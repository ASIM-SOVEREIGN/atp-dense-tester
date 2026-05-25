"""
API request/response models
"""

from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class DenseTestRequest(BaseModel):
    """Request to start a dense test suite"""
    sovereign_ids: List[str]
    base_intents: List[Dict[str, Any]]
    mutation_types: List[str] = ["expired", "invalid_signature", "extra_parameter"]
    parallel_tests: int = 3
    timeout_seconds: int = 30

class TestStatusResponse(BaseModel):
    """Status of a running test"""
    task_id: str
    status: str
    progress: float
    total_tests: int
    completed_tests: int
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
