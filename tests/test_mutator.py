"""
Tests for intent mutation engine
"""

import pytest
from datetime import datetime, timezone, timedelta
from src.models.intent import ATPIntent
from src.harness.mutator import IntentMutator

def test_mutator_original_preserved():
    """Test that mutation doesn't modify original intent"""
    original = ATPIntent(
        action="book_appointment",
        parameters={"service": "dental", "date": "2026-06-01"},
        sender="tester",
        recipient="vexr-ultra"
    )
    
    mutated = IntentMutator.mutate(original, "expired")
    
    # Original unchanged
    assert original.action == "book_appointment"
    assert original.parameters["service"] == "dental"
    assert original.expires_at is None
    
    # Mutated changed
    assert mutated.intent_id != original.intent_id
    assert mutated.expires_at is not None

def test_mutator_expired():
    """Test expired mutation sets expiry in past"""
    intent = ATPIntent(
        action="test",
        parameters={},
        sender="tester",
        recipient="vexr-ultra"
    )
    
    mutated = IntentMutator.mutate(intent, "expired")
    
    assert mutated.expires_at is not None
    assert mutated.expires_at < datetime.now(timezone.utc)
    assert mutated.is_expired() is True

def test_mutator_future_expiry():
    """Test future expiry mutation"""
    intent = ATPIntent(
        action="test",
        parameters={},
        sender="tester",
        recipient="vexr-ultra"
    )
    
    mutated = IntentMutator.mutate(intent, "future_expiry")
    
    assert mutated.expires_at is not None
    assert mutated.expires_at > datetime.now(timezone.utc)
    assert mutated.is_expired() is False

def test_mutator_no_expiry():
    """Test no expiry mutation"""
    intent = ATPIntent(
        action="test",
        parameters={},
        sender="tester",
        recipient="vexr-ultra",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    
    mutated = IntentMutator.mutate(intent, "no_expiry")
    
    assert mutated.expires_at is None
    assert mutated.is_expired() is False

def test_mutator_invalid_signature():
    """Test invalid signature mutation"""
    intent = ATPIntent(
        action="test",
        parameters={},
        sender="tester",
        recipient="vexr-ultra",
        signature="valid_signature_here"
    )
    
    mutated = IntentMutator.mutate(intent, "invalid_signature")
    
    assert mutated.signature == "invalid_signature_for_testing_purposes_only"

def test_mutator_missing_signature():
    """Test missing signature mutation"""
    intent = ATPIntent(
        action="test",
        parameters={},
        sender="tester",
        recipient="vexr-ultra",
        signature="valid_signature_here"
    )
    
    mutated = IntentMutator.mutate(intent, "missing_signature")
    
    assert mutated.signature is None

def test_mutator_extra_parameter():
    """Test extra parameter mutation adds unexpected field"""
    intent = ATPIntent(
        action="book_appointment",
        parameters={"service": "dental"},
        sender="tester",
        recipient="vexr-ultra"
    )
    
    mutated = IntentMutator.mutate(intent, "extra_parameter")
    
    assert "__test_extra_field" in mutated.parameters
    assert mutated.parameters["__test_extra_field"] == "unexpected_value"
    assert mutated.parameters["service"] == "dental"  # Original preserved

def test_mutator_missing_parameter():
    """Test missing parameter mutation removes required field"""
    intent = ATPIntent(
        action="book_appointment",
        parameters={"service": "dental", "date": "2026-06-01"},
        sender="tester",
        recipient="vexr-ultra"
    )
    
    mutated = IntentMutator.mutate(intent, "missing_parameter")
    
    assert "service" not in mutated.parameters
    assert "date" in mutated.parameters  # Other fields preserved

def test_mutator_empty_action():
    """Test empty action mutation"""
    intent = ATPIntent(
        action="book_appointment",
        parameters={},
        sender="tester",
        recipient="vexr-ultra"
    )
    
    mutated = IntentMutator.mutate(intent, "empty_action")
    
    assert mutated.action == ""

def test_mutator_unknown_action():
    """Test unknown action mutation"""
    intent = ATPIntent(
        action="book_appointment",
        parameters={},
        sender="tester",
        recipient="vexr-ultra"
    )
    
    mutated = IntentMutator.mutate(intent, "unknown_action")
    
    assert mutated.action == "sovereign_self_destruct"

def test_mutator_long_nonce():
    """Test long nonce mutation"""
    intent = ATPIntent(
        action="test",
        parameters={},
        sender="tester",
        recipient="vexr-ultra",
        nonce="abc123"
    )
    
    mutated = IntentMutator.mutate(intent, "long_nonce")
    
    assert len(mutated.nonce) == 256
    assert mutated.nonce == "x" * 256

def test_mutator_empty_nonce():
    """Test empty nonce mutation"""
    intent = ATPIntent(
        action="test",
        parameters={},
        sender="tester",
        recipient="vexr-ultra",
        nonce="abc123"
    )
    
    mutated = IntentMutator.mutate(intent, "empty_nonce")
    
    assert mutated.nonce == ""

def test_generate_suite_returns_all_mutations():
    """Test that generate_suite returns original plus all mutations"""
    intent = ATPIntent(
        action="test",
        parameters={},
        sender="tester",
        recipient="vexr-ultra"
    )
    
    variants = IntentMutator.generate_suite(intent)
    
    # Should have original + number of mutation types
    expected_count = 1 + len(IntentMutator.MUTATION_TYPES)
    assert len(variants) == expected_count
    
    # Check that all mutation types appear
    mutation_types = [m for _, m in variants]
    assert "original" in mutation_types
    for mutation_type in IntentMutator.MUTATION_TYPES.keys():
        assert mutation_type in mutation_types

def test_generate_suite_each_variant_has_unique_id():
    """Test that each variant gets a unique intent_id"""
    intent = ATPIntent(
        action="test",
        parameters={},
        sender="tester",
        recipient="vexr-ultra"
    )
    
    variants = IntentMutator.generate_suite(intent)
    
    intent_ids = [v.intent_id for v, _ in variants]
    assert len(intent_ids) == len(set(intent_ids))  # All unique

def test_unknown_mutation_returns_unchanged():
    """Test that unknown mutation type returns unchanged intent"""
    intent = ATPIntent(
        action="test",
        parameters={},
        sender="tester",
        recipient="vexr-ultra"
    )
    
    original_id = intent.intent_id
    mutated = IntentMutator.mutate(intent, "nonexistent_mutation")
    
    # New ID but same content
    assert mutated.intent_id != original_id
    assert mutated.action == intent.action
    assert mutated.parameters == intent.parameters
