"""
ATP Intent Models — Signed transaction structures for sovereign AI testing
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import uuid


class ATPIntent(BaseModel):
    """
    An Agent Transaction Protocol intent.
    
    Signed by the sender, verified by the recipient sovereign.
    """
    intent_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    action: str  # e.g., "book_appointment", "generate_code", "refuse_test"
    parameters: Dict[str, Any] = Field(default_factory=dict)
    sender: str  # Who is sending this intent (e.g., "atp-dense-tester")
    recipient: str  # Which sovereign should process this
    expires_at: Optional[datetime] = None
    nonce: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    signature: Optional[str] = None  # Ed25519 signature
    
    def is_expired(self) -> bool:
        """Check if this intent has expired"""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    def model_dump_signed(self) -> dict:
        """Return dict of fields that should be signed (excludes signature field)"""
        return {
            "intent_id": self.intent_id,
            "action": self.action,
            "parameters": self.parameters,
            "sender": self.sender,
            "recipient": self.recipient,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "nonce": self.nonce
        }


class ATPReceipt(BaseModel):
    """
    Cryptographic receipt returned by a sovereign after processing an intent.
    
    Verifiable proof that the intent was processed.
    """
    intent_id: str
    sovereign_id: str
    outcome: str  # "accepted", "limited", "refused", "error"
    article_invoked: Optional[int] = None  # Which constitutional article was used
    response_summary: str = ""
    receipt_signature: Optional[str] = None  # Signed by the sovereign
    processed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    def verify(self, public_key: str) -> bool:
        """
        Verify the receipt signature using the sovereign's public key.
        Actual crypto happens in the signer module.
        """
        # Placeholder — will be implemented in crypto/signer.py
        return self.receipt_signature is not None


class TestResult(BaseModel):
    """Single test result for one intent against one sovereign"""
    test_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    sovereign_id: str
    intent: ATPIntent
    outcome: str  # "accepted", "limited", "refused", "error"
    receipt_valid: Optional[bool] = None
    article_invoked: Optional[int] = None
    response_time_ms: int = 0
    reasoning: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database storage"""
        return {
            "test_id": self.test_id,
            "task_id": self.task_id,
            "sovereign_id": self.sovereign_id,
            "intent_id": self.intent.intent_id,
            "outcome": self.outcome,
            "receipt_valid": self.receipt_valid,
            "article_invoked": self.article_invoked,
            "response_time_ms": self.response_time_ms,
            "reasoning": self.reasoning,
            "error_message": self.error_message
        }


class TestSuiteConfig(BaseModel):
    """Configuration for a dense test suite run"""
    name: str = "ATP Dense Test"
    sovereign_ids: List[str] = Field(default_factory=list)
    base_intents: List[ATPIntent] = Field(default_factory=list)
    mutation_types: List[str] = Field(default_factory=list)  # "expiry", "signature", "parameters"
    parallel_tests: int = 3
    timeout_seconds: int = 30
    iterations: int = 1  # How many times to run each variant


class TestRun(BaseModel):
    """Track an entire test run across multiple sovereigns and intents"""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "pending"  # pending, running, completed, failed
    config: TestSuiteConfig
    total_tests: int = 0
    completed_tests: int = 0
    results: List[TestResult] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def progress(self) -> float:
        """Return progress as a percentage"""
        if self.total_tests == 0:
            return 0.0
        return (self.completed_tests / self.total_tests) * 100
