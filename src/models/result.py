"""
Test result models
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class TestResultSummary(BaseModel):
    """Summary of a test run"""
    task_id: str
    total_tests: int
    accepted: int
    limited: int
    refused: int
    errors: int
    receipt_valid_count: int
    by_sovereign: Dict[str, Dict[str, int]]
    started_at: datetime
    completed_at: Optional[datetime] = None

class DetailedTestResult(BaseModel):
    """Detailed individual test result"""
    test_id: str
    task_id: str
    sovereign_id: str
    intent_id: str
    outcome: str
    receipt_valid: Optional[bool]
    article_invoked: Optional[int]
    response_time_ms: int
    reasoning: Optional[str]
    error_message: Optional[str]
    created_at: datetime
