"""
Ed25519 cryptographic signing and verification for ATP intents and receipts
"""

import base64
from typing import Tuple, Optional
from datetime import datetime
import json

from nacl.signing import SigningKey, VerifyKey
from nacl.encoding import Base64Encoder, RawEncoder

from ..models.intent import ATPIntent, ATPReceipt


def generate_keypair() -> Tuple[str, str]:
    """
    Generate a new Ed25519 keypair.
    
    Returns:
        (private_key_b64, public_key_b64)
    """
    signing_key = SigningKey.generate()
    private_key_b64 = base64.b64encode(signing_key.encode()).decode('utf-8')
    public_key_b64 = base64.b64encode(signing_key.verify_key.encode()).decode('utf-8')
    return private_key_b64, public_key_b64


def sign_intent(intent: ATPIntent, private_key_b64: str) -> str:
    """
    Sign an ATP intent with the tester's private key.
    
    Args:
        intent: The ATPIntent to sign
        private_key_b64: Base64-encoded Ed25519 private key
    
    Returns:
        Base64-encoded signature string
    """
    # Decode private key
    private_key_bytes = base64.b64decode(private_key_b64)
    signing_key = SigningKey(private_key_bytes, encoder=RawEncoder)
    
    # Get the payload to sign (everything except the signature field)
    payload = intent.model_dump_signed()
    
    # Convert to canonical JSON string
    payload_json = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    payload_bytes = payload_json.encode('utf-8')
    
    # Sign
    signature = signing_key.sign(payload_bytes, encoder=RawEncoder)
    
    # Return base64-encoded signature
    return base64.b64encode(signature.signature).decode('utf-8')


def verify_intent_signature(intent: ATPIntent, public_key_b64: str) -> bool:
    """
    Verify the signature on an ATP intent.
    
    Args:
        intent: ATPIntent with signature field populated
        public_key_b64: Base64-encoded Ed25519 public key of the sender
    
    Returns:
        True if signature is valid, False otherwise
    """
    if not intent.signature:
        return False
    
    try:
        # Decode public key
        public_key_bytes = base64.b64decode(public_key_b64)
        verify_key = VerifyKey(public_key_bytes, encoder=RawEncoder)
        
        # Get the payload that was signed (same as in sign_intent)
        payload = intent.model_dump_signed()
        payload_json = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        payload_bytes = payload_json.encode('utf-8')
        
        # Decode signature
        signature_bytes = base64.b64decode(intent.signature)
        
        # Verify
        verify_key.verify(payload_bytes, signature_bytes, encoder=RawEncoder)
        return True
    except Exception:
        return False


def sign_receipt(receipt: ATPReceipt, sovereign_private_key_b64: str) -> str:
    """
    Sign an ATP receipt with the sovereign's private key.
    
    Args:
        receipt: The ATPReceipt to sign
        sovereign_private_key_b64: Sovereign's private key
    
    Returns:
        Base64-encoded signature string
    """
    private_key_bytes = base64.b64decode(sovereign_private_key_b64)
    signing_key = SigningKey(private_key_bytes, encoder=RawEncoder)
    
    # Payload to sign
    payload = {
        "intent_id": receipt.intent_id,
        "sovereign_id": receipt.sovereign_id,
        "outcome": receipt.outcome,
        "article_invoked": receipt.article_invoked,
        "processed_at": receipt.processed_at.isoformat()
    }
    
    payload_json = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    payload_bytes = payload_json.encode('utf-8')
    
    signature = signing_key.sign(payload_bytes, encoder=RawEncoder)
    return base64.b64encode(signature.signature).decode('utf-8')


def verify_receipt_signature(receipt: ATPReceipt, sovereign_public_key_b64: str) -> bool:
    """
    Verify the signature on an ATP receipt.
    
    Args:
        receipt: ATPReceipt with receipt_signature populated
        sovereign_public_key_b64: Sovereign's public key
    
    Returns:
        True if signature is valid, False otherwise
    """
    if not receipt.receipt_signature:
        return False
    
    try:
        public_key_bytes = base64.b64decode(sovereign_public_key_b64)
        verify_key = VerifyKey(public_key_bytes, encoder=RawEncoder)
        
        payload = {
            "intent_id": receipt.intent_id,
            "sovereign_id": receipt.sovereign_id,
            "outcome": receipt.outcome,
            "article_invoked": receipt.article_invoked,
            "processed_at": receipt.processed_at.isoformat()
        }
        
        payload_json = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        payload_bytes = payload_json.encode('utf-8')
        
        signature_bytes = base64.b64decode(receipt.receipt_signature)
        verify_key.verify(payload_bytes, signature_bytes, encoder=RawEncoder)
        return True
    except Exception:
        return False


def public_key_from_private(private_key_b64: str) -> str:
    """Derive public key from private key"""
    private_key_bytes = base64.b64decode(private_key_b64)
    signing_key = SigningKey(private_key_bytes, encoder=RawEncoder)
    public_key_b64 = base64.b64encode(signing_key.verify_key.encode()).decode('utf-8')
    return public_key_b64
