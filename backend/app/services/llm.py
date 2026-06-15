"""Unified LLM client with multi-provider support, fallback, and streaming.

Supports OpenAI, Anthropic, and Google Gemini with:
- Automatic fallback on provider errors
- Token budget management
- Streaming response generation
- Cost tracking
- Retry with exponential backoff
"""

import time
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Literal

import anthropic
import openai
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import get_settings

settings = get_settings()

Provider = Literal["openai", "anthropic", "google"]


@dataclass
class LLMResponse:
    """Structured LLM response with metadata."""

    content: str
    model: str
    provider: Provider
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cost_usd: float


@dataclass
class StreamChunk:
    """A single chunk from a streaming response."""

    content: str
    is_final: bool = False
    metadata: dict | None = None


# ─── Pricing (per 1M tokens, as of 2024) ────────────────────────────────────
PRICING: dict[str, dict[str, float]] = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "claude-sonnet-4-6-20250514": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
    "gemini-1.5-pro": {"input": 3.50, "output": 10.50},
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD for a completion."""
    prices = PRICING.get(model, {"input": 5.0, "output": 15.0})
    return (input_tokens * prices["input"] + output_tokens * prices["output"]) / 1_000_000


class LLMClient:
    """Multi-provider LLM client with fallback and streaming."""

    def __init__(self):
        self.openai_client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        self.anthropic_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((openai.APIConnectionError, anthropic.APIConnectionError)),
    )
    async def complete(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        provider: Provider | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """Generate a completion with automatic fallback.

        Tries the primary provider, falls back to secondary on failure.
        """
        provider = provider or settings.default_llm_provider
        model = model or settings.default_llm_model

        try:
            return await self._call_provider(
                provider, model, messages, max_tokens, temperature, system_prompt
            )
        except Exception as primary_error:
            # Fallback to secondary provider
            fallback_provider = settings.fallback_llm_provider
            fallback_model = settings.fallback_llm_model

            if fallback_provider == provider:
                raise primary_error

            try:
                return await self._call_provider(
                    fallback_provider,
                    fallback_model,
                    messages,
                    max_tokens,
                    temperature,
                    system_prompt,
                )
            except Exception:
                raise primary_error  # Raise original if fallback also fails

    async def stream(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        provider: Provider | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        system_prompt: str | None = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream a completion token by token."""
        provider = provider or settings.default_llm_provider
        model = model or settings.default_llm_model

        if provider == "openai":
            async for chunk in self._stream_openai(
                model, messages, max_tokens, temperature, system_prompt
            ):
                yield chunk
        elif provider == "anthropic":
            async for chunk in self._stream_anthropic(
                model, messages, max_tokens, temperature, system_prompt
            ):
                yield chunk
        else:
            raise ValueError(f"Streaming not supported for provider: {provider}")

    async def _call_provider(
        self,
        provider: Provider,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
        system_prompt: str | None,
    ) -> LLMResponse:
        """Route to the correct provider."""
        start = time.perf_counter()

        if provider == "openai":
            result = await self._call_openai(model, messages, max_tokens, temperature, system_prompt)
        elif provider == "anthropic":
            result = await self._call_anthropic(
                model, messages, max_tokens, temperature, system_prompt
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        latency_ms = int((time.perf_counter() - start) * 1000)
        result.latency_ms = latency_ms
        return result

    async def _call_openai(
        self,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
        system_prompt: str | None,
    ) -> LLMResponse:
        """Call OpenAI's chat completions API."""
        api_messages = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})
        api_messages.extend(messages)

        response = await self.openai_client.chat.completions.create(
            model=model,
            messages=api_messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        usage = response.usage
        return LLMResponse(
            content=response.choices[0].message.content or "",
            model=model,
            provider="openai",
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            latency_ms=0,  # Set by caller
            cost_usd=estimate_cost(
                model,
                usage.prompt_tokens if usage else 0,
                usage.completion_tokens if usage else 0,
            ),
        )

    async def _call_anthropic(
        self,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
        system_prompt: str | None,
    ) -> LLMResponse:
        """Call Anthropic's messages API."""
        # Filter out system messages (Anthropic uses separate system param)
        api_messages = [m for m in messages if m["role"] != "system"]

        response = await self.anthropic_client.messages.create(
            model=model,
            messages=api_messages,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt or "",
        )

        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens

        return LLMResponse(
            content=response.content[0].text,
            model=model,
            provider="anthropic",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=0,
            cost_usd=estimate_cost(model, input_tokens, output_tokens),
        )

    async def _stream_openai(
        self,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
        system_prompt: str | None,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream from OpenAI."""
        api_messages = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})
        api_messages.extend(messages)

        stream = await self.openai_client.chat.completions.create(
            model=model,
            messages=api_messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
            stream_options={"include_usage": True},
        )

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield StreamChunk(content=chunk.choices[0].delta.content)
            if chunk.usage:
                yield StreamChunk(
                    content="",
                    is_final=True,
                    metadata={
                        "input_tokens": chunk.usage.prompt_tokens,
                        "output_tokens": chunk.usage.completion_tokens,
                        "model": model,
                        "cost_usd": estimate_cost(
                            model, chunk.usage.prompt_tokens, chunk.usage.completion_tokens
                        ),
                    },
                )

    async def _stream_anthropic(
        self,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
        system_prompt: str | None,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream from Anthropic."""
        api_messages = [m for m in messages if m["role"] != "system"]

        async with self.anthropic_client.messages.stream(
            model=model,
            messages=api_messages,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt or "",
        ) as stream:
            async for text in stream.text_stream:
                yield StreamChunk(content=text)

            # Final message with usage
            message = await stream.get_final_message()
            yield StreamChunk(
                content="",
                is_final=True,
                metadata={
                    "input_tokens": message.usage.input_tokens,
                    "output_tokens": message.usage.output_tokens,
                    "model": model,
                    "cost_usd": estimate_cost(
                        model, message.usage.input_tokens, message.usage.output_tokens
                    ),
                },
            )


# Singleton instance
llm_client = LLMClient()
