import re
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.ai.schemas.structured_output import DirectMessageAnalysisOutput, ProductMention
from app.ai.services.product_matching_service import CatalogMatch, ProductMatchingService, normalize_product_text
from app.ai.services.direct_catalog_hints import suggest_from_catalog
from app.ai.services.direct_commercial_intent_service import classify_commercial_conversation, classify_commercial_message
from app.repositories.ai_direct_repository import AIRepository, DirectConversationRepository, DirectMessageRepository
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.product_repository import ProductRepository, ProductVariantRepository
from app.schemas.direct_order_proposal import DirectOrderProposal, OrderProposalCandidate, OrderProposalEvidence, OrderProposalLine


class ProposalConversationNotFound(ValueError):
    pass


class DirectOrderProposalService:
    """Saved data only: construction and GET never initialize AI settings/gateways."""
    def __init__(self, db: Session) -> None:
        self.conversations = DirectConversationRepository(db)
        self.messages = DirectMessageRepository(db)
        self.analyses = AIRepository(db)
        self.variants = ProductVariantRepository(db)
        self.inventory = InventoryRepository(db)
        self.matcher = ProductMatchingService(ProductRepository(db), self.variants)

    def get(self, workspace_id: UUID, conversation_id: UUID) -> DirectOrderProposal:
        if self.conversations.get(workspace_id, conversation_id) is None:
            raise ProposalConversationNotFound()
        analysis = self.analyses.latest_generic_analysis(workspace_id, conversation_id)
        inbound = self.messages.proposal_inbound(workspace_id, conversation_id)
        catalog = self.variants.proposal_catalog(workspace_id)
        truncated = len(catalog) > 500
        # Never match a partial catalog, including exact SKUs duplicated after limit.
        catalog = [] if truncated else catalog
        stock = {item.product_variant_id: item for item in self.inventory.list_by_variants(
            workspace_id, [variant.id for variant, _product in catalog]
        )}
        proposal = DirectOrderProposal(
            conversation_id=conversation_id, analysis_state="MISSING",
            catalog_truncated=truncated, context_truncated=len(inbound) > 50,
        )
        bounded = []
        remaining = 20000
        commercial_signal = classify_commercial_conversation(inbound[:50])
        proposal.commercial_stage = commercial_signal.stage.value
        proposal.commercial_reason = commercial_signal.reason
        for message in inbound[:50]:
            text = message.text or ""
            if remaining <= 0:
                proposal.context_truncated = True
                break
            sample = text[:min(4000, remaining)]
            clipped = len(sample) != len(text)
            proposal.context_truncated |= clipped
            remaining -= len(sample)
            # A bounded prefix is not a genuine token boundary. Discard its
            # incomplete terminal token rather than inventing evidence for
            # SKU-1 when the actual message continues with SKU-1-RED.
            if clipped and sample and not sample[-1].isspace() and not text[len(sample)].isspace():
                terminal = re.search(r"\S+$", sample)
                sample = sample[:terminal.start()] if terminal else sample
            bounded.append((message, sample))
        if analysis:
            proposal.analysis_id = analysis.id
            proposal.analysis_created_at = analysis.created_at
            # Context anchor only, not a per-mention citation. Do not leak a
            # corrupt/foreign source ID or guess the anchor outside this window.
            if analysis.source_message_id in {message.id for message, _ in bounded}:
                proposal.analysis_context_message_id = analysis.source_message_id
            if analysis.status != "COMPLETED":
                proposal.analysis_state = "PENDING" if analysis.status in {"QUEUED", "PROCESSING"} else "FAILED"
            else:
                try:
                    saved = analysis.structured_result
                    if not isinstance(saved, dict) or not isinstance(saved.get("extracted_entities"), dict) or not isinstance(saved["extracted_entities"].get("product_mentions"), list):
                        raise ValueError("MISSING_SAVED_PRODUCT_MENTIONS")
                    structured = DirectMessageAnalysisOutput.model_validate(saved)
                except (ValidationError, TypeError, ValueError):
                    proposal.analysis_state = "MALFORMED"
                else:
                    stale = self.messages.proposal_context_changed(workspace_id, conversation_id, analysis.created_at)
                    proposal.analysis_state = "STALE" if stale else "COMPLETED"
                    seen = set()
                    for mention in structured.extracted_entities.product_mentions:
                        identity = tuple(normalize_product_text(value) for value in (mention.text, mention.sku, mention.color, mention.size))
                        if identity in seen:
                            continue
                        seen.add(identity)
                        match = CatalogMatch("NOT_FOUND", "CATALOG_LIMIT") if truncated else self.matcher.match_mention(mention, catalog)
                        proposal.lines.append(self._line(
                            f"analysis:{analysis.id}:{len(seen)}", mention, match, stock, "ANALYSIS_CONTEXT", [],
                        ))
        # SKU permits arbitrary characters in the actual schema. Use whole,
        # whitespace-delimited literal identifiers rather than unsafe word-boundary
        # matching (SKU-1 inside SKU-1-RED/XSKU-1/SKU-10 must never be evidence).
        seen_skus = set()
        for variant, _product in catalog:
            sku = normalize_product_text(variant.sku)
            if not sku or sku in seen_skus:
                continue
            seen_skus.add(sku)
            pattern = re.compile(r"(?<!\S)" + r"\s+".join(re.escape(part) for part in variant.sku.strip().split()) + r"(?!\S)", re.IGNORECASE)
            evidence = None
            for message, text in bounded:
                if classify_commercial_message(text).reason == "NEGATED":
                    continue
                found = pattern.search(text)
                if found:
                    start = max(0, found.start() - 40)
                    evidence = OrderProposalEvidence(message_id=message.id, snippet=text[start:start + 160])
                    break
            if evidence is None:
                continue
            mention = ProductMention(text=variant.sku[:240], sku=variant.sku, quantity=1)
            proposal.lines.append(self._line(
                f"inbound:{variant.id}", mention, self.matcher.match_mention(mention, catalog), stock, "INBOUND_SKU", [evidence],
            ))
            if sum(line.source == "INBOUND_SKU" for line in proposal.lines) >= 20:
                proposal.context_truncated = True
                break
        # Only fully visible, active, workspace-scoped catalogs can support a
        # product hint. Keep AI-derived suggestions and exact SKUs authoritative;
        # never replace either with a broad category guess.
        if not truncated:
            sku_evidence = {
                evidence.message_id
                for line in proposal.lines if line.source == "INBOUND_SKU"
                for evidence in line.evidence
            }
            used_hint_keys: set[tuple[str, str]] = set()
            for message, text in bounded:
                if message.id in sku_evidence or classify_commercial_message(text).reason == "NEGATED":
                    continue
                for hint in suggest_from_catalog(text, catalog):
                    identity = (hint.matched_by, hint.identity)
                    if identity in used_hint_keys:
                        continue
                    used_hint_keys.add(identity)
                    candidates = hint.rows
                    product_mention = ProductMention(text=hint.phrase[:240], quantity=1)
                    match = CatalogMatch(
                        "AMBIGUOUS" if len(candidates) > 1 else "MATCHED",
                        "MULTIPLE_VARIANTS" if len(candidates) > 1 else "UNIQUE_EXACT_MATCH",
                        hint.matched_by,
                        candidates,
                    )
                    line = self._line(
                        f"product:{message.id}:{len(used_hint_keys)}",
                        product_mention, match, stock, "INBOUND_PRODUCT",
                        [OrderProposalEvidence(message_id=message.id, snippet=hint.phrase[:160])],
                    )
                    # Always require operator review even if exactly one
                    # catalog variant exists. Mention != agreement to buy.
                    line.requires_review = True
                    proposal.lines.append(line)
                    if len(proposal.lines) >= 40:
                        proposal.context_truncated = True
                        return proposal
        return proposal

    @staticmethod
    def _line(identity, mention, match, stock, source, evidence) -> OrderProposalLine:
        candidates = []
        for variant, product in match.rows[:10]:
            inventory = stock.get(variant.id)
            candidates.append(OrderProposalCandidate(
                product_id=product.id, variant_id=variant.id, product_name=product.name,
                sku=variant.sku, color=variant.color, size=variant.size, price=variant.price,
                available_quantity=inventory.stock_quantity - inventory.reserved_quantity if inventory else None,
            ))
        return OrderProposalLine(
            id=identity, mention_text=mention.text, quantity=mention.quantity or 1,
            source=source, evidence=evidence, requires_review=source == "ANALYSIS_CONTEXT",
            match_status=match.status, matched_by=match.matched_by, reason=match.reason,
            candidates_truncated=len(match.rows) > 10, candidates=candidates,
        )
