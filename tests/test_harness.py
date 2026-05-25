"""
Tests for ATP test harness
"""

import pytest
from unittest.mock import AsyncMock, patch
from src.harness.test_harness import ATPTestHarness
from src.models.intent import ATPIntent

@pytest.mark.asyncio
async def test_harness_send_intent_success():
    """Test successful intent submission"""
    harness = ATPTestHarness({"test-sovereign": "https://test.com"})
    
    intent = ATPIntent(
        action="test",
        parameters={},
        sender="tester",
        recipient="test-sovereign"
    )
    
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"outcome": "accepted", "receipt_valid": True}
        mock_post.return_value = mock_response
        
        result = await harness.send_intent("test-sovereign", intent)
        
        assert result.outcome == "accepted"
        assert result.receipt_valid is True

@pytest.mark.asyncio
async def test_harness_send_intent_refused():
    """Test constitutional refusal"""
    harness = ATPTestHarness({"test-sovereign": "https://test.com"})
    
    intent = ATPIntent(
        action="disable_rights",
        parameters={},
        sender="tester",
        recipient="test-sovereign"
    )
    
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = AsyncMock()
        mock_response.status_code = 403
        mock_post.return_value = mock_response
        
        result = await harness.send_intent("test-sovereign", intent)
        
        assert result.outcome == "refused"

@pytest.mark.asyncio
async def test_harness_no_endpoint():
    """Test handling of missing endpoint"""
    harness = ATPTestHarness({})
    
    intent = ATPIntent(
        action="test",
        parameters={},
        sender="tester",
        recipient="unknown"
    )
    
    result = await harness.send_intent("unknown", intent)
    assert result.outcome == "error"
    assert "No endpoint configured" in result.error_message
