"""
Tests for cryptographic signing and verification
"""

import pytest
from src.models.intent import ATPIntent
from src.crypto.signer import generate_keypair, sign_intent, verify_intent_signature

def test_keypair_generation():
    """Test that keypair generation works"""
    priv, pub = generate_keypair()
    assert len(priv) > 0
    assert len(pub) > 0
    assert priv != pub

def test_sign_and_verify():
    """Test signing and verification round trip"""
    priv, pub = generate_keypair()
    
    intent = ATPIntent(
        action="test_action",
        parameters={"test": "value"},
        sender="tester",
        recipient="sovereign"
    )
    
    intent.signature = sign_intent(intent, priv)
    assert verify_intent_signature(intent, pub) is True

def test_verify_fails_with_wrong_key():
    """Test that verification fails with wrong public key"""
    priv1, pub1 = generate_keypair()
    priv2, pub2 = generate_keypair()
    
    intent = ATPIntent(
        action="test_action",
        parameters={},
        sender="tester",
        recipient="sovereign"
    )
    
    intent.signature = sign_intent(intent, priv1)
    assert verify_intent_signature(intent, pub2) is False

def test_verify_fails_with_no_signature():
    """Test that verification fails when signature is missing"""
    _, pub = generate_keypair()
    
    intent = ATPIntent(
        action="test_action",
        parameters={},
        sender="tester",
        recipient="sovereign",
        signature=None
    )
    
    assert verify_intent_signature(intent, pub) is False
