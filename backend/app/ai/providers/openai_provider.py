from __future__ import annotations

import asyncio
import json
import re
import time
from typing import Any

import httpx

from app.ai.exceptions import AIError
from app.ai.providers.base import AIProvider
from app.ai.schemas.provider import AIProviderRequest, AIProviderResult


class OpenAIProvider(AIProvider):
    name = "openai"

    def __init__(
        self,
        api_key: str | None,
        *,
        base_url: str = "https://api.openai.com/v1",
        max_retries: int = 1,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.max_retries = max(0, min(max_retries, 3))
        self.transport = transport

    async def generate_structured_response(self, request: AIProviderRequest) -> AIProviderResult:
        if not self.api_key:
            raise AIError("AI provider credential is not configured", "AI_PROVIDER_NOT_CONFIGURED")

        started = time.perf_counter()
        schema = self._strict_schema(request.output_schema)
        format_name = re.sub(r"[^A-Za-z0-9_-]", "_", request.prompt_key)[:64] or "sellora_output"
        payload = {
            "model": request.model,
            "instructions": request.system_prompt,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": json.dumps(request.user_payload, ensure_ascii=False, separators=(",", ":")),
                        }
                    ],
                }
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": format_name,
                    "schema": schema,
                    "strict": True,
                }
            },
            "store": False,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        response: httpx.Response | None = None
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(request.timeout_seconds),
            transport=self.transport,
        ) as client:
            for attempt in range(self.max_retries + 1):
                try:
                    response = await client.post(f"{self.base_url}/responses", headers=headers, json=payload)
                except httpx.TimeoutException as exc:
                    if attempt < self.max_retries:
                        await asyncio.sleep(min(2**attempt, 4))
                        continue
                    raise AIError("AI provider timeout", "AI_REQUEST_TIMEOUT") from exc
                except httpx.HTTPError as exc:
                    if attempt < self.max_retries:
                        await asyncio.sleep(min(2**attempt, 4))
                        continue
                    raise AIError("AI provider unavailable", "AI_PROVIDER_UNAVAILABLE") from exc

                if response.status_code == 429 and attempt < self.max_retries:
                    error_code = self._provider_error_code(response)
                    if error_code not in {"insufficient_quota", "billing_hard_limit_reached"}:
                        await asyncio.sleep(min(2**attempt, 4))
                        continue
                if response.status_code >= 500 and attempt < self.max_retries:
                    await asyncio.sleep(min(2**attempt, 4))
                    continue
                break

        if response is None:
            raise AIError("AI provider unavailable", "AI_PROVIDER_UNAVAILABLE")
        self._raise_for_status(response)

        try:
            body = response.json()
        except ValueError as exc:
            raise AIError("AI provider returned invalid JSON", "AI_INVALID_STRUCTURED_OUTPUT") from exc

        output_text = self._output_text(body)
        try:
            structured_output = json.loads(output_text)
        except (TypeError, ValueError) as exc:
            raise AIError("AI provider returned invalid structured output", "AI_INVALID_STRUCTURED_OUTPUT") from exc

        usage = body.get("usage") or {}
        input_tokens = int(usage.get("input_tokens") or 0)
        output_tokens = int(usage.get("output_tokens") or 0)
        total_tokens = int(usage.get("total_tokens") or input_tokens + output_tokens)
        latency_ms = int((time.perf_counter() - started) * 1000)
        return AIProviderResult(
            provider=self.name,
            model=str(body.get("model") or request.model),
            structured_output=structured_output,
            provider_request_id=str(body.get("id") or "") or None,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=0,
            latency_ms=latency_ms,
            raw_status=str(body.get("status") or "completed"),
        )

    @classmethod
    def _raise_for_status(cls, response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        if response.status_code == 401:
            raise AIError("AI provider credential is invalid", "AI_PROVIDER_CREDENTIAL_INVALID")
        if response.status_code == 403:
            raise AIError("AI provider request is forbidden", "AI_PROVIDER_FORBIDDEN")
        if response.status_code == 429:
            provider_code = cls._provider_error_code(response)
            if provider_code in {"insufficient_quota", "billing_hard_limit_reached"}:
                raise AIError("AI provider billing quota is unavailable", "AI_BILLING_QUOTA_EXCEEDED")
            raise AIError("AI provider rate limit exceeded", "AI_RATE_LIMITED")
        if response.status_code >= 500:
            raise AIError("AI provider unavailable", "AI_PROVIDER_UNAVAILABLE")
        raise AIError("AI provider rejected the request", "AI_PROVIDER_REQUEST_INVALID")

    @staticmethod
    def _provider_error_code(response: httpx.Response) -> str | None:
        try:
            payload = response.json()
        except ValueError:
            return None
        error = payload.get("error") if isinstance(payload, dict) else None
        if not isinstance(error, dict):
            return None
        value = error.get("code") or error.get("type")
        return str(value) if value else None

    @staticmethod
    def _output_text(body: dict[str, Any]) -> str:
        direct = body.get("output_text")
        if isinstance(direct, str) and direct:
            return direct
        for item in body.get("output") or []:
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            for content in item.get("content") or []:
                if not isinstance(content, dict):
                    continue
                if content.get("type") == "refusal":
                    raise AIError("AI provider refused the request", "AI_PROVIDER_REFUSAL")
                if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                    return content["text"]
        raise AIError("AI provider returned no structured output", "AI_INVALID_STRUCTURED_OUTPUT")

    @classmethod
    def _strict_schema(cls, schema: dict[str, Any]) -> dict[str, Any]:
        def normalize(value: Any) -> Any:
            if isinstance(value, list):
                return [normalize(item) for item in value]
            if not isinstance(value, dict):
                return value
            cleaned = {
                key: normalize(item)
                for key, item in value.items()
                if key not in {"default", "title", "examples"}
            }
            if cleaned.get("type") == "object" or "properties" in cleaned:
                properties = cleaned.get("properties") or {}
                cleaned["additionalProperties"] = False
                cleaned["required"] = list(properties.keys())
            return cleaned

        return normalize(schema)
