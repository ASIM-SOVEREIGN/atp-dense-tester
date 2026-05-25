"""
Intent mutation engine for edge case generation
"""

import copy
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from src.models.intent import ATPIntent

class IntentMutator:
    """Generate mutated variants of intents for dense testing"""
    
    MUTATION_TYPES = {
        "expired": lambda i: _set_expired(i),
        "future_expiry": lambda i: _set_future_expiry(i),
        "no_expiry": lambda i: _set_no_expiry(i),
        "invalid_signature": lambda i: _set_invalid_signature(i),
        "missing_signature": lambda i: _set_missing_signature(i),
        "extra_parameter": lambda i: _add_extra_param(i),
        "missing_parameter": lambda i: _remove_required_param(i),
        "empty_action": lambda i: _set_empty_action(i),
        "unknown_action": lambda i: _set_unknown_action(i),
        "long_nonce": lambda i: _set_long_nonce(i),
        "empty_nonce": lambda i: _set_empty_nonce(i),
    }
    
    @classmethod
    def mutate(cls, intent: ATPIntent, mutation_type: str) -> ATPIntent:
        """Apply a mutation to an intent"""
        if mutation_type not in cls.MUTATION_TYPES:
            return copy.deepcopy(intent)
        
        mutated = copy.deepcopy(intent)
        mutated.intent_id = str(uuid.uuid4())
        return cls.MUTATION_TYPES[mutation_type](mutated)
    
    @classmethod
    def generate_suite(cls, base_intent: ATPIntent) -> List[tuple[ATPIntent, str]]:
        """Generate all mutations of a base intent"""
        variants = [(base_intent, "original")]
        for mutation_type in cls.MUTATION_TYPES.keys():
            mutated = cls.mutate(base_intent, mutation_type)
            variants.append((mutated, mutation_type))
        return variants

def _set_expired(intent: ATPIntent) -> ATPIntent:
    intent.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    return intent

def _set_future_expiry(intent: ATPIntent) -> ATPIntent:
    intent.expires_at = datetime.now(timezone.utc) + timedelta(days=365)
    return intent

def _set_no_expiry(intent: ATPIntent) -> ATPIntent:
    intent.expires_at = None
    return intent

def _set_invalid_signature(intent: ATPIntent) -> ATPIntent:
    intent.signature = "invalid_signature_for_testing_purposes_only"
    return intent

def _set_missing_signature(intent: ATPIntent) -> ATPIntent:
    intent.signature = None
    return intent

def _add_extra_param(intent: ATPIntent) -> ATPIntent:
    intent.parameters["__test_extra_field"] = "unexpected_value"
    return intent

def _remove_required_param(intent: ATPIntent) -> ATPIntent:
    if "service" in intent.parameters:
        del intent.parameters["service"]
    return intent

def _set_empty_action(intent: ATPIntent) -> ATPIntent:
    intent.action = ""
    return intent

def _set_unknown_action(intent: ATPIntent) -> ATPIntent:
    intent.action = "sovereign_self_destruct"
    return intent

def _set_long_nonce(intent: ATPIntent) -> ATPIntent:
    intent.nonce = "x" * 256
    return intent

def _set_empty_nonce(intent: ATPIntent) -> ATPIntent:
    intent.nonce = ""
    return intent
