"""
Unit tests for LLM Service
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.services.llm_service import (
    LLMResponse,
    LLMService,
    LLMUsageStats,
    OllamaProvider,
    OpenAIProvider,
)


@pytest.fixture
def mock_settings():
    """Mock settings for testing"""
    with patch("app.services.llm_service.settings") as mock:
        mock.llm_provider = "ollama"
        mock.ollama_base_url = "http://localhost:11434"
        mock.ollama_model = "test-model"
        mock.daily_cost_budget_usd = 10.0
        yield mock


@pytest.fixture
def ollama_provider():
    """Create Ollama provider instance"""
    return OllamaProvider("http://localhost:11434", "test-model")


@pytest.fixture
def openai_provider():
    """Create OpenAI provider instance"""
    return OpenAIProvider("test-api-key", "gpt-3.5-turbo")


class TestOllamaProvider:
    """Test Ollama provider"""

    @pytest.mark.asyncio
    async def test_generate_success(self, ollama_provider):
        """Test successful generation"""
        mock_response = {
            "message": {"content": "Generated text"},
            "prompt_eval_count": 100,
            "eval_count": 50,
        }

        with patch.object(ollama_provider.client, "post", new_callable=AsyncMock) as mock_post:
            # httpx response.json() is sync, not async
            mock_post.return_value.json = Mock(return_value=mock_response)
            mock_post.return_value.raise_for_status = Mock()

            response = await ollama_provider.generate("Test prompt")

            assert response.content == "Generated text"
            assert response.usage.prompt_tokens == 100
            assert response.usage.completion_tokens == 50
            assert response.usage.total_tokens == 150
            assert response.usage.provider == "ollama"
            assert response.usage.cost_usd == 0.0  # Ollama is free

    @pytest.mark.asyncio
    async def test_generate_with_system_prompt(self, ollama_provider):
        """Test generation with system prompt"""
        with patch.object(ollama_provider.client, "post", new_callable=AsyncMock) as mock_post:
            # httpx response.json() is sync, not async
            mock_post.return_value.json = Mock(
                return_value={
                    "message": {"content": "Response"},
                    "prompt_eval_count": 50,
                    "eval_count": 25,
                }
            )
            mock_post.return_value.raise_for_status = Mock()

            await ollama_provider.generate("User prompt", system_prompt="System instructions")

            # Verify system prompt was included
            call_args = mock_post.call_args[1]["json"]
            assert len(call_args["messages"]) == 2
            assert call_args["messages"][0]["role"] == "system"
            assert call_args["messages"][1]["role"] == "user"

    def test_calculate_cost(self, ollama_provider):
        """Test cost calculation for Ollama (should be 0)"""
        cost = ollama_provider.calculate_cost(1000, 500)
        assert cost == 0.0


class TestOpenAIProvider:
    """Test OpenAI provider"""

    def test_calculate_cost_gpt35(self, openai_provider):
        """Test cost calculation for GPT-3.5"""
        # 1000 prompt tokens, 500 completion tokens
        cost = openai_provider.calculate_cost(1000, 500)

        expected = (1000 / 1000 * 0.0005) + (500 / 1000 * 0.0015)
        assert cost == pytest.approx(expected)

    def test_calculate_cost_unknown_model(self):
        """Test cost calculation for unknown model (uses default)"""
        provider = OpenAIProvider("test-key", "unknown-model")
        cost = provider.calculate_cost(1000, 500)

        # Should use default pricing
        expected = (1000 / 1000 * 0.002) + (500 / 1000 * 0.002)
        assert cost == pytest.approx(expected)


class TestLLMService:
    """Test LLM Service"""

    @pytest.mark.asyncio
    async def test_initialization_ollama(self, mock_settings):
        """Test service initialization with Ollama"""
        service = LLMService()

        assert isinstance(service.provider, OllamaProvider)
        assert service.total_cost_today == 0.0
        assert service.request_count == 0

    @pytest.mark.asyncio
    async def test_initialization_openai(self, mock_settings):
        """Test service initialization with OpenAI"""
        mock_settings.llm_provider = "openai"
        mock_settings.openai_api_key = "test-key"
        mock_settings.openai_model = "gpt-3.5-turbo"

        service = LLMService()

        assert isinstance(service.provider, OpenAIProvider)

    @pytest.mark.asyncio
    async def test_generate_success(self, mock_settings):
        """Test successful generation with cost tracking"""
        service = LLMService()

        mock_response = LLMResponse(
            content="Generated text",
            usage=LLMUsageStats(
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                cost_usd=0.05,
                provider="ollama",
                model="test-model",
                timestamp=datetime.utcnow(),
            ),
        )

        with patch.object(service.provider, "generate", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_response

            response = await service.generate("Test prompt")

            assert response.content == "Generated text"
            assert service.total_cost_today == 0.05
            assert service.request_count == 1

    @pytest.mark.asyncio
    async def test_generate_budget_exceeded(self, mock_settings):
        """Test budget limit enforcement"""
        service = LLMService()
        service.total_cost_today = 11.0  # Exceed budget

        with pytest.raises(ValueError, match="Daily cost budget exceeded"):
            await service.generate("Test prompt")

    @pytest.mark.asyncio
    async def test_generate_with_retry(self, mock_settings):
        """Test retry logic on failure"""
        service = LLMService()

        mock_response = LLMResponse(
            content="Success",
            usage=LLMUsageStats(
                prompt_tokens=10,
                completion_tokens=10,
                total_tokens=20,
                cost_usd=0.0,
                provider="ollama",
                model="test-model",
                timestamp=datetime.utcnow(),
            ),
        )

        with patch.object(service.provider, "generate", new_callable=AsyncMock) as mock_gen:
            # Fail twice, then succeed
            mock_gen.side_effect = [
                RuntimeError("Temporary error"),
                RuntimeError("Another error"),
                mock_response,
            ]

            response = await service.generate("Test", max_retries=3, retry_delay=0.01)

            assert response.content == "Success"
            assert mock_gen.call_count == 3

    @pytest.mark.asyncio
    async def test_generate_all_retries_failed(self, mock_settings):
        """Test failure after all retries exhausted"""
        service = LLMService()

        with patch.object(service.provider, "generate", new_callable=AsyncMock) as mock_gen:
            mock_gen.side_effect = RuntimeError("Persistent error")

            with pytest.raises(RuntimeError, match="failed after 3 attempts"):
                await service.generate("Test", max_retries=3, retry_delay=0.01)

            assert mock_gen.call_count == 3

    @pytest.mark.asyncio
    async def test_get_usage_stats(self, mock_settings):
        """Test usage statistics retrieval"""
        service = LLMService()
        service.total_cost_today = 2.5
        service.request_count = 10

        stats = await service.get_usage_stats()

        assert stats["provider"] == "ollama"
        assert stats["total_cost_today"] == 2.5
        assert stats["request_count_today"] == 10
        assert stats["budget_remaining"] == 7.5
        assert stats["budget_usage_percent"] == 25.0
