"""Tests for OpenAI client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from openai.types.chat import ChatCompletion, ChatCompletionChunk
from openai.types.chat.chat_completion import Choice, ChatCompletionMessage
from openai import RateLimitError, AuthenticationError, APIError
import time

from nova.llm.openai import OpenAIClient
from nova.types import MCPPayload, ContextBlock, LLMResponse


@pytest.fixture
def mock_openai():
    """Create mock OpenAI client."""
    with patch("nova.llm.openai.AsyncOpenAI") as mock:
        client = mock.return_value
        client.chat = MagicMock()
        client.chat.completions = AsyncMock()
        yield client


@pytest.fixture
def test_payload():
    """Create test MCP payload."""
    return MCPPayload(
        system_instructions="You are a helpful AI assistant.",
        developer_instructions="Use the provided context to answer.",
        user_message="What is the capital of France?",
        context_blocks=[
            ContextBlock(
                content="Paris is the capital of France.",
                metadata={},
                ephemeral=False
            )
        ]
    )


@pytest.fixture
def openai_client(mock_openai):
    """Create OpenAI client with mock."""
    return OpenAIClient(
        api_key="test-key",
        model="gpt-3.5-turbo-16k",
        max_tokens=100,
        temperature=0.7
    )


@pytest.mark.asyncio
async def test_complete_success(openai_client, mock_openai, test_payload):
    """Test successful completion."""
    # Setup mock response
    mock_response = MagicMock(spec=ChatCompletion)
    mock_message = MagicMock(spec=ChatCompletionMessage)
    mock_message.content = "Paris is the capital of France."
    mock_choice = Choice(message=mock_message, index=0, finish_reason="stop")
    mock_response.choices = [mock_choice]
    mock_response.usage = {"total_tokens": 10}
    
    mock_openai.chat.completions.create.return_value = mock_response
    
    # Call complete
    response = await openai_client.complete(test_payload)
    
    # Verify response
    assert response.content == "Paris is the capital of France."
    assert response.metadata["model"] == "gpt-3.5-turbo-16k"
    assert response.usage == {"total_tokens": 10}
    
    # Verify API call
    mock_openai.chat.completions.create.assert_called_once()
    call_kwargs = mock_openai.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "gpt-3.5-turbo-16k"
    assert call_kwargs["max_tokens"] == 100
    assert call_kwargs["temperature"] == 0.7
    assert len(call_kwargs["messages"]) == 4  # System, dev instructions, context, user


@pytest.mark.asyncio
async def test_streaming(openai_client, mock_openai, test_payload):
    """Test streaming completion."""
    # Setup mock stream
    mock_chunks = [
        {
            "id": "1",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "gpt-3.5-turbo-16k",
            "choices": [{"index": 0, "delta": {"content": "Paris"}, "finish_reason": None}]
        },
        {
            "id": "2",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "gpt-3.5-turbo-16k",
            "choices": [{"index": 0, "delta": {"content": " is"}, "finish_reason": None}]
        },
        {
            "id": "3",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "gpt-3.5-turbo-16k",
            "choices": [{"index": 0, "delta": {"content": " the capital."}, "finish_reason": "stop"}]
        }
    ]
    chunks = [ChatCompletionChunk(**chunk) for chunk in mock_chunks]
    mock_openai.chat.completions.create.return_value.__aiter__.return_value = chunks
    
    # Call streaming complete
    result = []
    async for chunk in await openai_client.complete(test_payload, stream=True):
        result.append(chunk)
    
    # Verify result
    assert result == ["Paris", " is", " the capital."]
    
    # Verify API call
    mock_openai.chat.completions.create.assert_called_once()
    call_kwargs = mock_openai.chat.completions.create.call_args.kwargs
    assert call_kwargs["stream"] is True


@pytest.mark.asyncio
async def test_format_payload(openai_client, test_payload):
    """Test payload formatting."""
    messages = openai_client._format_payload(test_payload)
    
    assert len(messages) == 4
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == test_payload.system_instructions
    assert messages[1]["role"] == "system"
    assert messages[1]["content"] == test_payload.developer_instructions
    assert messages[2]["role"] == "user"
    assert "<context>" in messages[2]["content"]
    assert messages[3]["role"] == "user"
    assert messages[3]["content"] == test_payload.user_message


@pytest.mark.asyncio
async def test_rate_limit_error(openai_client, mock_openai, test_payload):
    """Test rate limit error handling."""
    error_response = MagicMock()
    error_response.status = 429
    error_response.json.return_value = {"error": {"message": "Rate limit exceeded"}}
    mock_openai.chat.completions.create.side_effect = RateLimitError(
        message="Rate limit exceeded",
        response=error_response,
        body={"error": {"message": "Rate limit exceeded"}}
    )
    
    with pytest.raises(RateLimitError, match="Rate limit exceeded"):
        await openai_client.complete(test_payload)


@pytest.mark.asyncio
async def test_auth_error(openai_client, mock_openai, test_payload):
    """Test authentication error handling."""
    error_response = MagicMock()
    error_response.status = 401
    error_response.json.return_value = {"error": {"message": "Invalid API key"}}
    mock_openai.chat.completions.create.side_effect = AuthenticationError(
        message="Invalid API key",
        response=error_response,
        body={"error": {"message": "Invalid API key"}}
    )
    
    with pytest.raises(AuthenticationError, match="Invalid API key"):
        await openai_client.complete(test_payload)


@pytest.mark.asyncio
async def test_api_error(openai_client, mock_openai, test_payload):
    """Test API error handling."""
    error_request = MagicMock()
    error_request.method = "POST"
    error_request.url = "https://api.openai.com/v1/chat/completions"
    mock_openai.chat.completions.create.side_effect = APIError(
        message="API Error",
        request=error_request,
        body={"error": {"message": "API Error", "type": "api_error"}}
    )
    
    with pytest.raises(APIError, match="API Error"):
        await openai_client.complete(test_payload)


@pytest.mark.asyncio
async def test_empty_context(openai_client, mock_openai):
    """Test completion with empty context."""
    payload = MCPPayload(
        system_instructions="You are a helpful AI assistant.",
        developer_instructions="Answer the question.",
        user_message="What is 2+2?",
        context_blocks=[]  # Empty context
    )
    
    mock_response = MagicMock(spec=ChatCompletion)
    mock_message = MagicMock(spec=ChatCompletionMessage)
    mock_message.content = "4"
    mock_choice = Choice(message=mock_message, index=0, finish_reason="stop")
    mock_response.choices = [mock_choice]
    mock_response.usage = {"total_tokens": 5}
    
    mock_openai.chat.completions.create.return_value = mock_response
    
    response = await openai_client.complete(payload)
    assert response.content == "4"
    
    # Verify no context block in messages
    call_kwargs = mock_openai.chat.completions.create.call_args.kwargs
    assert len(call_kwargs["messages"]) == 3  # System, dev instructions, user


@pytest.mark.asyncio
async def test_streaming_empty_chunk(openai_client, mock_openai, test_payload):
    """Test streaming with empty chunk content."""
    mock_chunks = [
        {
            "id": "1",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "gpt-3.5-turbo-16k",
            "choices": [{"index": 0, "delta": {"content": "Hello"}, "finish_reason": None}]
        },
        {
            "id": "2",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "gpt-3.5-turbo-16k",
            "choices": [{"index": 0, "delta": {}, "finish_reason": None}]
        },
        {
            "id": "3",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "gpt-3.5-turbo-16k",
            "choices": [{"index": 0, "delta": {"content": " world"}, "finish_reason": "stop"}]
        }
    ]
    chunks = [ChatCompletionChunk(**chunk) for chunk in mock_chunks]
    mock_openai.chat.completions.create.return_value.__aiter__.return_value = chunks
    
    result = []
    async for chunk in await openai_client.complete(test_payload, stream=True):
        if chunk:  # Should skip empty chunk
            result.append(chunk)
    
    assert result == ["Hello", " world"]


@pytest.mark.asyncio
async def test_multiple_context_blocks(openai_client, mock_openai):
    """Test completion with multiple context blocks."""
    payload = MCPPayload(
        system_instructions="You are a helpful AI assistant.",
        developer_instructions="Use the provided context to answer.",
        user_message="Tell me about France.",
        context_blocks=[
            ContextBlock(content="Paris is the capital of France.", metadata={}),
            ContextBlock(content="France is in Europe.", metadata={}),
            ContextBlock(content="French is the official language.", metadata={})
        ]
    )
    
    mock_response = MagicMock(spec=ChatCompletion)
    mock_message = MagicMock(spec=ChatCompletionMessage)
    mock_message.content = "France is a European country..."
    mock_choice = Choice(message=mock_message, index=0, finish_reason="stop")
    mock_response.choices = [mock_choice]
    mock_response.usage = {"total_tokens": 15}
    
    mock_openai.chat.completions.create.return_value = mock_response
    
    response = await openai_client.complete(payload)
    
    # Verify all context blocks are included
    call_kwargs = mock_openai.chat.completions.create.call_args.kwargs
    context_message = call_kwargs["messages"][2]["content"]
    assert "Paris is the capital" in context_message
    assert "France is in Europe" in context_message
    assert "French is the official language" in context_message


@pytest.mark.asyncio
async def test_custom_kwargs(openai_client, mock_openai, test_payload):
    """Test passing custom kwargs to API call."""
    mock_response = MagicMock(spec=ChatCompletion)
    mock_message = MagicMock(spec=ChatCompletionMessage)
    mock_message.content = "Response"
    mock_choice = Choice(message=mock_message, index=0, finish_reason="stop")
    mock_response.choices = [mock_choice]
    mock_response.usage = {"total_tokens": 5}
    
    mock_openai.chat.completions.create.return_value = mock_response
    
    await openai_client.complete(
        test_payload,
        presence_penalty=0.5,
        frequency_penalty=0.3,
        top_p=0.9
    )
    
    call_kwargs = mock_openai.chat.completions.create.call_args.kwargs
    assert call_kwargs["presence_penalty"] == 0.5
    assert call_kwargs["frequency_penalty"] == 0.3
    assert call_kwargs["top_p"] == 0.9 