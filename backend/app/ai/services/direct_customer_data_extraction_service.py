from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.exceptions import AIError
from app.ai.prompts.registry import get_prompt
from app.ai.schemas.provider import AIProviderRequest
from app.ai.schemas.structured_output import (
    CustomerDeliveryProvider,
    DirectCustomerDataExtractionOutput,
)
from app.ai.services.ai_gateway_service import AIGatewayService
from app.ai.services.usage_service import AIUsageService
from app.core.config import get_settings
from app.models.ai_direct import (
    AIAnalysis,
    AIAnalysisStatus,
    AIIntent,
    DirectAIProcessingStatus,
    DirectChannel,
    DirectConversation,
    DirectMessage,
    DirectMessageDirection,
    DirectMessageType,
)
from app.models.customer import CustomerProfileStatus
from app.repositories.ai_direct_repository import AIRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.schemas.direct_customer_extraction import (
    DirectCustomerExtractionApplyRequest,
    DirectCustomerExtractionData,
    DirectCustomerExtractionResponse,
)
from app.services.business_utils import snapshot
from app.services.direct_customer_automation_service import (
    DirectCustomerAutomationError,
    DirectCustomerAutomationService,
)
from app.services.nova_poshta_service import (
    NovaPoshtaDirectoryService,
    NovaPoshtaServiceError,
)
from app.utils.phone import PhoneNormalizationError, normalize_ua_phone


PROMPT_KEY = "DIRECT_CUSTOMER_DATA_EXTRACTION"
CONTACT_SIGNAL = re.compile(
    r"(?:\+?38)?[\s()\-]*0\d[\d\s()\-]{7,}|"
    r"нова\s*пошта|новая\s*почта|\bнп\b|\bnp\b|відділен|отделен|поштомат|почтомат|warehouse|branch",
    re.IGNORECASE,
)
GENERIC_CUSTOMER_NAMES = {"", "Instagram customer", "Клієнт Instagram"}
ALLOWED_OVERWRITE_FIELDS = {"name", "phone", "city", "region", "delivery_address"}


class DirectCustomerDataExtractionService:
    def __init__(self, db: Session, gateway: AIGatewayService | None = None) -> None:
        self.db = db
        self.gateway = gateway or AIGatewayService()
        self.ai_repo = AIRepository(db)
        self.audit_logs = AuditLogRepository(db)
        self.customer_automation = DirectCustomerAutomationService(db)

    async def process_next(self) -> str | None:
        settings = get_settings()
        if not settings.ai_customer_data_extraction_enabled or not settings.ai_api_key:
            return None

        analysis = self._next_queued()
        if analysis is None:
            analysis = self._discover_and_queue()
        if analysis is None:
            return None

        await self._process_analysis(analysis, actor_user_id=None, auto_apply=True)
        return analysis.status

    async def extract_now(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
        actor_user_id: UUID,
    ) -> DirectCustomerExtractionResponse:
        settings = get_settings()
        if not settings.ai_customer_data_extraction_enabled:
            raise AIError("AI customer extraction is disabled", "AI_FEATURE_DISABLED")
        if not settings.ai_api_key:
            raise AIError("AI provider credential is not configured", "AI_PROVIDER_NOT_CONFIGURED")

        analysis = self._queue(
            workspace_id,
            conversation_id,
            actor_user_id=actor_user_id,
            force=True,
        )
        if analysis.status == AIAnalysisStatus.COMPLETED.value:
            return self._response(analysis)
        await self._process_analysis(analysis, actor_user_id=actor_user_id, auto_apply=True)
        return self._response(analysis)

    def latest(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
    ) -> DirectCustomerExtractionResponse | None:
        analysis = self._latest_analysis(workspace_id, conversation_id)
        return self._response(analysis) if analysis else None

    def apply(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
        payload: DirectCustomerExtractionApplyRequest,
        actor_user_id: UUID,
    ) -> DirectCustomerExtractionResponse:
        analysis = self.ai_repo.get_analysis(workspace_id, payload.analysis_id)
        if not analysis or analysis.conversation_id != conversation_id or analysis.prompt_key != PROMPT_KEY:
            raise AIError("Customer extraction not found", "DIRECT_CUSTOMER_EXTRACTION_NOT_FOUND")
        if analysis.status != AIAnalysisStatus.COMPLETED.value:
            raise AIError("Customer extraction is not ready", "DIRECT_CUSTOMER_EXTRACTION_NOT_READY")

        result = dict(analysis.structured_result or {})
        data = result.get("data") or {}
        overwrite_fields = set(payload.overwrite_fields) & ALLOWED_OVERWRITE_FIELDS
        applied_fields = self._apply_data(
            workspace_id,
            conversation_id,
            data,
            actor_user_id=actor_user_id,
            overwrite_fields=overwrite_fields,
            automatic=False,
        )
        result["data"] = {**data, "applied_fields": sorted(set(data.get("applied_fields") or []) | set(applied_fields))}
        analysis.structured_result = result
        self.db.commit()
        self.db.refresh(analysis)
        return self._response(analysis)

    def _next_queued(self) -> AIAnalysis | None:
        return self.db.execute(
            select(AIAnalysis)
            .where(
                AIAnalysis.prompt_key == PROMPT_KEY,
                AIAnalysis.status == AIAnalysisStatus.QUEUED.value,
            )
            .order_by(AIAnalysis.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        ).scalar_one_or_none()

    def _discover_and_queue(self) -> AIAnalysis | None:
        conversations = self.db.execute(
            select(DirectConversation)
            .where(
                DirectConversation.channel == DirectChannel.INSTAGRAM.value,
                DirectConversation.deleted_at.is_(None),
                DirectConversation.last_inbound_message_at.is_not(None),
            )
            .order_by(DirectConversation.last_inbound_message_at.desc())
            .limit(30)
        ).scalars()
        for conversation in conversations:
            messages = self._recent_messages(conversation.workspace_id, conversation.id)
            inbound_texts = [item.text or "" for item in messages if item.direction == DirectMessageDirection.INBOUND.value]
            if not self._looks_like_customer_data(inbound_texts):
                continue
            fingerprint = self._fingerprint(messages)
            latest = self._latest_analysis(conversation.workspace_id, conversation.id)
            if latest and (latest.structured_result or {}).get("context_fingerprint") == fingerprint:
                if latest.status in {
                    AIAnalysisStatus.QUEUED.value,
                    AIAnalysisStatus.PROCESSING.value,
                    AIAnalysisStatus.COMPLETED.value,
                }:
                    continue
            return self._queue(
                conversation.workspace_id,
                conversation.id,
                actor_user_id=None,
                force=False,
                messages=messages,
            )
        return None

    def _queue(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
        *,
        actor_user_id: UUID | None,
        force: bool,
        messages: list[DirectMessage] | None = None,
    ) -> AIAnalysis:
        conversation = self._conversation(workspace_id, conversation_id)
        messages = messages or self._recent_messages(workspace_id, conversation_id)
        if not messages:
            raise AIError("Direct text messages not found", "DIRECT_MESSAGE_NOT_FOUND")
        inbound_texts = [item.text or "" for item in messages if item.direction == DirectMessageDirection.INBOUND.value]
        if not force and not self._looks_like_customer_data(inbound_texts):
            raise AIError("Customer delivery data was not detected", "DIRECT_CUSTOMER_DATA_NOT_DETECTED")

        fingerprint = self._fingerprint(messages)
        latest = self._latest_analysis(workspace_id, conversation_id)
        if latest and (latest.structured_result or {}).get("context_fingerprint") == fingerprint:
            if latest.status in {
                AIAnalysisStatus.QUEUED.value,
                AIAnalysisStatus.PROCESSING.value,
                AIAnalysisStatus.COMPLETED.value,
            }:
                return latest

        source = next(
            (item for item in reversed(messages) if item.direction == DirectMessageDirection.INBOUND.value),
            messages[-1],
        )
        prompt = get_prompt(PROMPT_KEY)
        now = datetime.now(UTC)
        analysis = self.ai_repo.create_analysis(
            AIAnalysis(
                workspace_id=workspace_id,
                conversation_id=conversation_id,
                source_message_id=source.id,
                provider=get_settings().ai_provider,
                model=get_settings().ai_fast_model,
                prompt_key=prompt.prompt_key,
                prompt_version=prompt.prompt_version,
                status=AIAnalysisStatus.QUEUED.value,
                structured_result={
                    "context_fingerprint": fingerprint,
                    "source_message_count": len(messages),
                },
                created_at=now,
                created_by=actor_user_id,
            )
        )
        conversation.ai_processing_status = DirectAIProcessingStatus.QUEUED.value
        self.db.flush()
        return analysis

    async def _process_analysis(
        self,
        analysis: AIAnalysis,
        *,
        actor_user_id: UUID | None,
        auto_apply: bool,
    ) -> None:
        settings = get_settings()
        conversation = self._conversation(analysis.workspace_id, analysis.conversation_id)
        messages = self._recent_messages(analysis.workspace_id, analysis.conversation_id)
        prompt = get_prompt(PROMPT_KEY)
        context = self._context(conversation, messages)
        input_characters = len(json.dumps(context, ensure_ascii=False))
        if input_characters > min(settings.ai_max_input_characters, prompt.maximum_context):
            self._fail(analysis, conversation, "AI_INPUT_TOO_LARGE")
            return

        analysis.status = AIAnalysisStatus.PROCESSING.value
        analysis.started_at = datetime.now(UTC)
        conversation.ai_processing_status = DirectAIProcessingStatus.PROCESSING.value
        self.db.flush()

        try:
            result = await self.gateway.generate_structured_response(
                AIProviderRequest(
                    prompt_key=prompt.prompt_key,
                    prompt_version=prompt.prompt_version,
                    model=settings.ai_fast_model,
                    system_prompt=prompt.system_prompt,
                    user_payload=context,
                    output_schema=prompt.output_schema,
                    timeout_seconds=settings.ai_request_timeout_seconds,
                )
            )
            extracted = DirectCustomerDataExtractionOutput.model_validate(result.structured_output)
            data = self._normalize(extracted)
            data = self._verify_delivery(analysis.workspace_id, data)
            customer_state = self.customer_automation.ensure_candidate(
                analysis.workspace_id,
                analysis.conversation_id,
                actor_user_id,
                require_order_intent=False,
                commit=False,
            )
            customer = customer_state.customer
            data["conflicts"] = self._conflicts(customer, data)
            data["applied_fields"] = []
            if auto_apply:
                data["applied_fields"] = self._apply_data(
                    analysis.workspace_id,
                    analysis.conversation_id,
                    data,
                    actor_user_id=actor_user_id,
                    overwrite_fields=set(),
                    automatic=True,
                )

            previous = dict(analysis.structured_result or {})
            analysis.structured_result = {
                **previous,
                "data": data,
                "provider_request_id": result.provider_request_id,
            }
            analysis.status = AIAnalysisStatus.COMPLETED.value
            analysis.detected_intent = AIIntent.ORDER_REQUEST.value
            analysis.intent_confidence = extracted.overall_confidence
            analysis.provider_request_id = result.provider_request_id
            analysis.input_tokens = result.input_tokens
            analysis.output_tokens = result.output_tokens
            analysis.total_tokens = result.total_tokens
            analysis.estimated_cost_usd = result.estimated_cost_usd
            analysis.latency_ms = result.latency_ms
            analysis.completed_at = datetime.now(UTC)
            conversation.ai_processing_status = DirectAIProcessingStatus.REVIEW_REQUIRED.value
            conversation.latest_ai_analysis_id = analysis.id
            AIUsageService(self.ai_repo).record(
                analysis.workspace_id,
                result.provider,
                result.model,
                PROMPT_KEY,
                "COMPLETED",
                actor_user_id,
                analysis.conversation_id,
                analysis.id,
                result.input_tokens,
                result.output_tokens,
                result.estimated_cost_usd,
                result.latency_ms,
            )
        except Exception as exc:
            code = getattr(exc, "safe_code", "AI_INVALID_STRUCTURED_OUTPUT")
            self._fail(analysis, conversation, code)
            AIUsageService(self.ai_repo).record(
                analysis.workspace_id,
                settings.ai_provider,
                settings.ai_fast_model,
                PROMPT_KEY,
                code,
                actor_user_id,
                analysis.conversation_id,
                analysis.id,
            )

    def _apply_data(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
        data: dict,
        *,
        actor_user_id: UUID | None,
        overwrite_fields: set[str],
        automatic: bool,
    ) -> list[str]:
        state = self.customer_automation.ensure_candidate(
            workspace_id,
            conversation_id,
            actor_user_id,
            require_order_intent=False,
            commit=False,
        )
        if not state.customer:
            return []
        customer = self.customer_automation.customers.get(workspace_id, state.customer.id)
        if customer is None:
            return []

        old_value = snapshot(customer)
        applied: list[str] = []
        name = (data.get("recipient_name") or "").strip()
        phone = data.get("phone")
        city = (data.get("city") or "").strip()
        region = (data.get("region") or "").strip()

        if name and float(data.get("recipient_name_confidence") or 0) >= 0.85:
            if customer.name in GENERIC_CUSTOMER_NAMES or "name" in overwrite_fields:
                customer.name = name
                applied.append("name")
        if phone and float(data.get("phone_confidence") or 0) >= 0.9:
            if not customer.phone or "phone" in overwrite_fields:
                customer.phone = phone
                applied.append("phone")
        if city and float(data.get("city_confidence") or 0) >= 0.8:
            if not customer.city or "city" in overwrite_fields:
                customer.city = city
                applied.append("city")
        if region and (not customer.region or "region" in overwrite_fields):
            customer.region = region
            applied.append("region")

        can_apply_address = (
            data.get("delivery_provider") == CustomerDeliveryProvider.NOVA_POSHTA.value
            and data.get("city_verified")
            and data.get("warehouse_verified")
            and data.get("nova_poshta_city_ref")
            and data.get("nova_poshta_warehouse_ref")
            and float(data.get("warehouse_confidence") or 0) >= 0.85
        )
        latest_state = self.customer_automation._state(
            workspace_id,
            self.customer_automation._conversation(workspace_id, conversation_id),
            customer,
        )
        if can_apply_address and (
            "delivery_address" in latest_state.missing_fields
            or "delivery_address" in overwrite_fields
        ):
            recipient_name = name or customer.name
            recipient_phone = phone or customer.phone
            if recipient_name and recipient_phone and city:
                self.customer_automation._upsert_default_address(
                    workspace_id,
                    customer.id,
                    recipient_name=recipient_name,
                    recipient_phone=recipient_phone,
                    city=city,
                    warehouse=data.get("warehouse_text") or f"Відділення №{data.get('warehouse_number')}",
                    warehouse_number=data.get("warehouse_number"),
                    city_ref=data["nova_poshta_city_ref"],
                    warehouse_ref=data["nova_poshta_warehouse_ref"],
                    actor_user_id=actor_user_id,
                )
                applied.append("delivery_address")

        self.db.flush()
        refreshed_state = self.customer_automation._state(
            workspace_id,
            self.customer_automation._conversation(workspace_id, conversation_id),
            customer,
        )
        customer.profile_status = (
            CustomerProfileStatus.COMPLETE.value
            if refreshed_state.profile_complete
            else CustomerProfileStatus.INCOMPLETE.value
        )
        if applied:
            self.audit_logs.create(
                workspace_id=workspace_id,
                user_id=actor_user_id,
                entity_type="Customer",
                entity_id=customer.id,
                action="DIRECT_AI_CUSTOMER_DATA_APPLY",
                old_value=old_value,
                new_value={
                    **snapshot(customer),
                    "automatic": automatic,
                    "applied_fields": applied,
                },
            )
        return applied

    def _verify_delivery(self, workspace_id: UUID, data: dict) -> dict:
        data = dict(data)
        data.update(
            nova_poshta_city_ref=None,
            nova_poshta_warehouse_ref=None,
            city_verified=False,
            warehouse_verified=False,
        )
        if data.get("delivery_provider") != CustomerDeliveryProvider.NOVA_POSHTA.value:
            return data
        city = (data.get("city") or "").strip()
        warehouse_query = (data.get("warehouse_number") or data.get("warehouse_text") or "").strip()
        if not city or not warehouse_query:
            return data
        try:
            directory = NovaPoshtaDirectoryService(self.db)
            cities = directory.search_cities(workspace_id, city, 10)
            city_item = self._best_city(cities, city)
            if not city_item:
                return data
            data["nova_poshta_city_ref"] = city_item.ref
            data["city_verified"] = True
            warehouses = directory.search_warehouses(
                workspace_id,
                city_item.ref,
                warehouse_query,
                100,
            )
            warehouse_item = self._best_warehouse(
                warehouses,
                data.get("warehouse_number"),
                data.get("warehouse_text"),
            )
            if warehouse_item:
                data["nova_poshta_warehouse_ref"] = warehouse_item.ref
                data["warehouse_verified"] = True
                data["warehouse_text"] = warehouse_item.description
                if warehouse_item.number:
                    data["warehouse_number"] = str(warehouse_item.number)
        except NovaPoshtaServiceError:
            data.setdefault("conflicts", []).append("NOVA_POSHTA_VERIFICATION_UNAVAILABLE")
        return data

    @staticmethod
    def _best_city(items, query: str):
        normalized = DirectCustomerDataExtractionService._plain(query)
        exact = [item for item in items if DirectCustomerDataExtractionService._plain(item.description) == normalized]
        if exact:
            return exact[0]
        starts = [item for item in items if DirectCustomerDataExtractionService._plain(item.description).startswith(normalized)]
        return starts[0] if starts else (items[0] if items else None)

    @staticmethod
    def _best_warehouse(items, number: str | None, text: str | None):
        normalized_number = re.sub(r"\D", "", number or "")
        if normalized_number:
            exact = [item for item in items if re.sub(r"\D", "", str(item.number or "")) == normalized_number]
            if exact:
                return exact[0]
        normalized_text = DirectCustomerDataExtractionService._plain(text or "")
        if normalized_text:
            matches = [item for item in items if normalized_text in DirectCustomerDataExtractionService._plain(item.description)]
            if matches:
                return matches[0]
        return items[0] if len(items) == 1 else None

    def _conflicts(self, customer_response, data: dict) -> list[str]:
        if not customer_response:
            return list(data.get("conflicts") or [])
        conflicts = list(data.get("conflicts") or [])
        if customer_response.name not in GENERIC_CUSTOMER_NAMES and data.get("recipient_name"):
            if self._plain(customer_response.name) != self._plain(data["recipient_name"]):
                conflicts.append("name")
        if customer_response.phone and data.get("phone") and customer_response.phone != data["phone"]:
            conflicts.append("phone")
        if customer_response.city and data.get("city"):
            if self._plain(customer_response.city) != self._plain(data["city"]):
                conflicts.append("city")
        return sorted(set(conflicts))

    @staticmethod
    def _normalize(output: DirectCustomerDataExtractionOutput) -> dict:
        data = output.model_dump(mode="json")
        name = re.sub(r"\s+", " ", (data.get("recipient_name") or "")).strip()
        data["recipient_name"] = name or None
        phone = data.get("phone")
        if phone:
            try:
                data["phone"] = normalize_ua_phone(phone)
            except PhoneNormalizationError:
                data["phone"] = None
                data["phone_confidence"] = 0
                data["clarification_required"] = True
        if data.get("warehouse_number"):
            cleaned = re.sub(r"[^0-9A-Za-zА-Яа-яІіЇїЄєҐґ\-]", "", str(data["warehouse_number"]))
            data["warehouse_number"] = cleaned or None
        missing = set(data.get("missing_fields") or [])
        for field in ("recipient_name", "phone", "city", "warehouse_number"):
            if not data.get(field):
                missing.add(field)
        data["missing_fields"] = sorted(missing)
        return data

    def _recent_messages(self, workspace_id: UUID, conversation_id: UUID) -> list[DirectMessage]:
        items = list(
            self.db.execute(
                select(DirectMessage)
                .where(
                    DirectMessage.workspace_id == workspace_id,
                    DirectMessage.conversation_id == conversation_id,
                    DirectMessage.deleted_at.is_(None),
                    DirectMessage.message_type == DirectMessageType.TEXT.value,
                    DirectMessage.text.is_not(None),
                )
                .order_by(
                    DirectMessage.received_at.desc(),
                    DirectMessage.created_at.desc(),
                    DirectMessage.id.desc(),
                )
                .limit(20)
            ).scalars()
        )
        return list(reversed(items))

    def _context(self, conversation: DirectConversation, messages: list[DirectMessage]) -> dict:
        return {
            "conversation": {
                "participant_display_name": conversation.participant_display_name,
                "participant_username": conversation.participant_username,
            },
            "messages": [
                {
                    "index": index,
                    "direction": message.direction,
                    "text": message.text,
                    "received_at": message.received_at.isoformat(),
                }
                for index, message in enumerate(messages, start=1)
            ],
        }

    def _latest_analysis(self, workspace_id: UUID, conversation_id: UUID) -> AIAnalysis | None:
        return self.db.execute(
            select(AIAnalysis)
            .where(
                AIAnalysis.workspace_id == workspace_id,
                AIAnalysis.conversation_id == conversation_id,
                AIAnalysis.prompt_key == PROMPT_KEY,
            )
            .order_by(AIAnalysis.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()

    def _conversation(self, workspace_id: UUID, conversation_id: UUID) -> DirectConversation:
        conversation = self.db.execute(
            select(DirectConversation).where(
                DirectConversation.workspace_id == workspace_id,
                DirectConversation.id == conversation_id,
                DirectConversation.deleted_at.is_(None),
            )
        ).scalar_one_or_none()
        if not conversation:
            raise DirectCustomerAutomationError("DIRECT_CONVERSATION_NOT_FOUND")
        return conversation

    @staticmethod
    def _looks_like_customer_data(texts: list[str]) -> bool:
        joined = "\n".join(texts[-8:])
        digit_count = sum(character.isdigit() for character in joined)
        return bool(CONTACT_SIGNAL.search(joined)) or digit_count >= 9

    @staticmethod
    def _fingerprint(messages: list[DirectMessage]) -> str:
        payload = "\n".join(
            f"{message.id}:{message.direction}:{message.safe_text_hash or message.text or ''}"
            for message in messages
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    @staticmethod
    def _plain(value: str) -> str:
        return re.sub(r"[^0-9a-zа-яіїєґ]", "", value.lower())

    def _fail(self, analysis: AIAnalysis, conversation: DirectConversation, code: str) -> None:
        analysis.status = AIAnalysisStatus.FAILED_SAFE.value
        analysis.safe_error_code = code
        analysis.safe_error_message = "AI customer data extraction failed safely"
        analysis.completed_at = datetime.now(UTC)
        conversation.ai_processing_status = DirectAIProcessingStatus.FAILED.value

    @staticmethod
    def _response(analysis: AIAnalysis) -> DirectCustomerExtractionResponse:
        result = analysis.structured_result or {}
        raw_data = result.get("data")
        data = DirectCustomerExtractionData.model_validate(raw_data) if raw_data else None
        return DirectCustomerExtractionResponse(
            analysis_id=analysis.id,
            conversation_id=analysis.conversation_id,
            status=analysis.status,
            data=data,
            source_message_count=int(result.get("source_message_count") or 0),
            safe_error_code=analysis.safe_error_code,
            applied=bool(data and data.applied_fields),
            created_at=analysis.created_at,
            completed_at=analysis.completed_at,
        )
