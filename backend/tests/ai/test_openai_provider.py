import json

import httpx
import pytest

from app.ai.exceptions import AIError
from app.ai.providers.openai_provider import OpenAIProvider
from app.ai.schemas.provider import AIProviderRequest


def _request() -> AIProviderRequest:
    return AIProviderRequest(
        prompt_key="DIRECT_CUSTOMER_DATA_EXTRACTION",
        prompt_version="v1",
        model="gpt-4.1-mini",
        system_prompt="Return structured data only.",
        user_payload={"messages": [{"direction": "INBOUND", "text": "0987379999 Київ НП-273"}]},
        output_schema={
            "type": "object",
            "properties": {
                "phone": {"anyOf": [{"type": "string"}, {"type": "null"}], "default": None},
                "city": {"anyOf": [{"type": "string"}, {"type": "null"}], "default": None},
            },
        },
        timeout_seconds=5,
    )


@pytest.mark.asyncio
async def test_openai_provider_uses_responses_structured_outputs_without_storage() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.read().decode()))
        return httpx.Response(
            200,
            json={
                "id": "resp_test",
                "model": "gpt-4.1-mini",
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": json.dumps({"phone": "+380987379999", "city": "Київ"}),
                            }
                        ],
                    }
                ],
                "usage": {"input_tokens": 50, "output_tokens": 20, "total_tokens": 70},
            },
        )

    provider = OpenAIProvider(
        "test-key",
        transport=httpx.MockTransport(handler),
        max_retries=0,
    )
    result = await provider.generate_structured_response(_request())

    assert result.structured_output == {"phone": "+380987379999", "city": "Київ"}
    assert result.total_tokens == 70
    assert captured["store"] is False
    assert captured["text"]["format"]["type"] == "json_schema"
    assert captured["text"]["format"]["strict"] is True
    schema = captured["text"]["format"]["schema"]
    assert schema["additionalProperties"] is False
    assert schema["required"] == ["phone", "city"]
    assert "default" not in json.dumps(schema)


@pytest.mark.asyncio
async def test_openai_provider_maps_rate_limit_to_safe_error() -> None:
    provider = OpenAIProvider(
        "test-key",
        transport=httpx.MockTransport(lambda _request: httpx.Response(429, json={"error": {"message": "limited"}})),
        max_retries=0,
    )

    with pytest.raises(AIError) as error:
        await provider.generate_structured_response(_request())

    assert error.value.safe_code == "AI_RATE_LIMITED"


@pytest.mark.asyncio
async def test_openai_provider_maps_insufficient_quota_separately() -> None:
    provider = OpenAIProvider(
        "test-key",
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                429,
                json={
                    "error": {
                        "message": "You exceeded your current quota.",
                        "type": "insufficient_quota",
                        "code": "insufficient_quota",
                    }
                },
            )
        ),
        max_retries=1,
    )

    with pytest.raises(AIError) as error:
        await provider.generate_structured_response(_request())

    assert error.value.safe_code == "AI_BILLING_QUOTA_EXCEEDED"


@pytest.mark.asyncio
async def test_openai_provider_requires_credential() -> None:
    provider = OpenAIProvider(None, max_retries=0)

    with pytest.raises(AIError) as error:
        await provider.generate_structured_response(_request())

    assert error.value.safe_code == "AI_PROVIDER_NOT_CONFIGURED"
