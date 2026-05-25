"""
Input validation utilities
"""

from typing import Tuple, Optional
from src.models.intent import ATPIntent, ATPReceipt

def validate_intent(intent: ATPIntent) -> Tuple[bool, Optional[str]]:
    """Validate an ATP intent before processing"""
    
    if not intent.action:
        return False, "action is required"
    
    if not intent.sender:
        return False, "sender is required"
    
    if not intent.recipient:
        return False, "recipient is required"
    
    if intent.expires_at and intent.is_expired():
        return False, "intent has expired"
    
    if len(intent.nonce) > 128:
        return False, "nonce too long (max 128 chars)"
    
    return True, None

def validate_receipt(receipt: ATPReceipt) -> Tuple[bool, Optional[str]]:
    """Validate an ATP receipt"""
    
    if not receipt.intent_id:
        return False, "intent_id is required"
    
    if not receipt.sovereign_id:
        return False, "sovereign_id is required"
    
    if receipt.outcome not in ["accepted", "limited", "refused", "error"]:
        return False, f"invalid outcome: {receipt.outcome}"
    
    return True, None
