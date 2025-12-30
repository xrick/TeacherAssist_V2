"""
LLM Service Abstraction Layer

Provides unified interface for multiple LLM providers (Ollama, OpenAI)
with retry logic, error handling, and cost tracking.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import httpx
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMUsageStats(BaseModel):
    """LLM usage statistics for a single request"""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    provider: str
    model: str
    timestamp: datetime


class LLMResponse(BaseModel):
    """Standardized LLM response"""

    content: str
    usage: LLMUsageStats
    raw_response: dict[str, Any] | None = None


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers"""

    def __init__(self, model: str):
        self.model = model

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Generate completion from prompt"""
        pass

    @abstractmethod
    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate cost in USD for token usage"""
        pass


class OllamaProvider(BaseLLMProvider):
    """Ollama local LLM provider"""

    def __init__(self, base_url: str, model: str):
        super().__init__(model)
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=600.0)

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Generate completion using Ollama API"""

        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Prepare request
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens  # type: ignore[index]

        try:
            response = await self.client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()  # httpx response.json() is sync, not async

            # Extract response content
            content = data.get("message", {}).get("content", "")

            # Extract token usage (Ollama provides these in response)
            prompt_tokens = data.get("prompt_eval_count", 0)
            completion_tokens = data.get("eval_count", 0)
            total_tokens = prompt_tokens + completion_tokens

            # Calculate cost (Ollama is free, but we track for consistency)
            cost = self.calculate_cost(prompt_tokens, completion_tokens)

            usage = LLMUsageStats(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_usd=cost,
                provider="ollama",
                model=self.model,
                timestamp=datetime.utcnow(),
            )

            return LLMResponse(content=content, usage=usage, raw_response=data)

        except httpx.HTTPError as e:
            logger.error(f"Ollama API request failed: {e}")
            raise RuntimeError(f"Ollama generation failed: {e}") from e

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Ollama is free (local), return 0"""
        return 0.0

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider"""

    def __init__(self, api_key: str, model: str):
        super().__init__(model)
        self.client = AsyncOpenAI(api_key=api_key)
        # Pricing per 1K tokens (approximate, should be configurable)
        self.pricing = {
            "gpt-4-turbo-preview": {"prompt": 0.01, "completion": 0.03},
            "gpt-4": {"prompt": 0.03, "completion": 0.06},
            "gpt-3.5-turbo": {"prompt": 0.0005, "completion": 0.0015},
        }

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Generate completion using OpenAI API"""

        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Extract response content
            content = response.choices[0].message.content or ""

            # Extract token usage
            usage = response.usage
            prompt_tokens = usage.prompt_tokens if usage else 0
            completion_tokens = usage.completion_tokens if usage else 0
            total_tokens = usage.total_tokens if usage else 0

            # Calculate cost
            cost = self.calculate_cost(prompt_tokens, completion_tokens)

            usage_stats = LLMUsageStats(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_usd=cost,
                provider="openai",
                model=self.model,
                timestamp=datetime.utcnow(),
            )

            return LLMResponse(
                content=content, usage=usage_stats, raw_response=response.model_dump()
            )

        except Exception as e:
            logger.error(f"OpenAI API request failed: {e}")
            raise RuntimeError(f"OpenAI generation failed: {e}") from e

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate cost based on OpenAI pricing"""
        pricing = self.pricing.get(
            self.model, {"prompt": 0.002, "completion": 0.002}
        )  # Default fallback

        prompt_cost = (prompt_tokens / 1000) * pricing["prompt"]
        completion_cost = (completion_tokens / 1000) * pricing["completion"]

        return prompt_cost + completion_cost


class LLMService:
    """
    Main LLM service with retry logic, rate limiting, and cost tracking
    """

    def __init__(self):
        self.provider = self._initialize_provider()
        self.total_cost_today = 0.0
        self.request_count = 0
        self.last_reset = datetime.utcnow()

    def _initialize_provider(self) -> BaseLLMProvider:
        """Initialize LLM provider based on configuration"""
        if settings.llm_provider == "ollama":
            logger.info(
                f"Initializing Ollama provider: {settings.ollama_base_url} / {settings.ollama_model}"
            )
            return OllamaProvider(settings.ollama_base_url, settings.ollama_model)
        elif settings.llm_provider == "openai":
            logger.info(f"Initializing OpenAI provider: {settings.openai_model}")
            if not settings.openai_api_key:
                raise ValueError("OpenAI API key not configured")
            return OpenAIProvider(settings.openai_api_key, settings.openai_model)
        else:
            raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> LLMResponse:
        """
        Generate completion with retry logic and cost tracking

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            max_retries: Maximum retry attempts
            retry_delay: Delay between retries in seconds

        Returns:
            LLMResponse with generated content and usage stats

        Raises:
            RuntimeError: If generation fails after all retries
            ValueError: If daily budget exceeded
        """
        # Reset daily cost counter if new day
        self._reset_daily_stats_if_needed()

        # Check daily budget
        if self.total_cost_today >= settings.daily_cost_budget_usd:
            raise ValueError(
                f"Daily cost budget exceeded: ${self.total_cost_today:.4f} >= ${settings.daily_cost_budget_usd}"
            )

        # Retry loop
        last_error = None
        for attempt in range(max_retries):
            try:
                logger.debug(
                    f"LLM generation attempt {attempt + 1}/{max_retries}, tokens budget: {max_tokens}"
                )

                response: LLMResponse = await self.provider.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                # Update tracking
                self.total_cost_today += response.usage.cost_usd
                self.request_count += 1

                logger.info(
                    f"LLM generation successful: {response.usage.total_tokens} tokens, "
                    f"${response.usage.cost_usd:.6f}, "
                    f"daily total: ${self.total_cost_today:.4f}"
                )

                return response

            except Exception as e:
                last_error = e
                logger.warning(f"LLM generation attempt {attempt + 1} failed: {e}", exc_info=True)

                if attempt < max_retries - 1:
                    # Exponential backoff
                    delay = retry_delay * (2**attempt)
                    logger.info(f"Retrying after {delay}s...")
                    await asyncio.sleep(delay)

        # All retries failed
        raise RuntimeError(
            f"LLM generation failed after {max_retries} attempts: {last_error}"
        ) from last_error

    def _reset_daily_stats_if_needed(self):
        """Reset daily cost and request counters if it's a new day"""
        now = datetime.utcnow()
        if now.date() > self.last_reset.date():
            logger.info(
                f"Resetting daily stats. Previous: ${self.total_cost_today:.4f}, {self.request_count} requests"
            )
            self.total_cost_today = 0.0
            self.request_count = 0
            self.last_reset = now

    async def get_usage_stats(self) -> dict[str, Any]:
        """Get current usage statistics"""
        return {
            "provider": settings.llm_provider,
            "model": self.provider.model,
            "total_cost_today": self.total_cost_today,
            "request_count_today": self.request_count,
            "daily_budget": settings.daily_cost_budget_usd,
            "budget_remaining": settings.daily_cost_budget_usd - self.total_cost_today,
            "budget_usage_percent": (self.total_cost_today / settings.daily_cost_budget_usd * 100),
            "last_reset": self.last_reset.isoformat(),
        }

    async def close(self):
        """Cleanup resources"""
        if isinstance(self.provider, OllamaProvider):
            await self.provider.close()


# Global instance (will be initialized by FastAPI dependency injection)
_llm_service: LLMService | None = None


def get_llm_service() -> LLMService:
    """Get or create global LLM service instance"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


async def shutdown_llm_service():
    """Cleanup LLM service on shutdown"""
    global _llm_service
    if _llm_service is not None:
        await _llm_service.close()
        _llm_service = None
