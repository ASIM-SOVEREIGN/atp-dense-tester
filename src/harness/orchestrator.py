"""
Dense test orchestrator - runs suites across multiple sovereigns
"""

import asyncio
import os
import json
from typing import Dict, List, Any
from src.models.intent import ATPIntent, TestSuiteConfig
from src.harness.test_harness import ATPTestHarness
from src.harness.mutator import IntentMutator
from src.db.repositories import save_test_result, update_test_run_summary

async def run_test_suite(task_id: str, config: Dict[str, Any], endpoints: Dict[str, str]):
    """Execute a test suite across multiple sovereigns"""
    
    # Load endpoints from env if not provided
    if not endpoints:
        endpoints = json.loads(os.environ.get("SOVEREIGN_ENDPOINTS", "{}"))
    
    harness = ATPTestHarness(endpoints, timeout=config.get("timeout_seconds", 30))
    
    # Build base intents from config
    base_intents = []
    for intent_dict in config.get("base_intents", []):
        base_intents.append(ATPIntent(**intent_dict))
    
    # Generate all test variants
    all_tests = []
    for intent in base_intents:
        variants = IntentMutator.generate_suite(intent)
        all_tests.extend(variants)
    
    sovereign_ids = config.get("sovereign_ids", [])
    total_tests = len(all_tests) * len(sovereign_ids)
    
    # Update config with total count
    config["total_tests"] = total_tests
    
    # Run all tests
    results = []
    semaphore = asyncio.Semaphore(config.get("parallel_tests", 3))
    
    async def run_one(sovereign_id: str, intent: ATPIntent, mutation: str):
        async with semaphore:
            result = await harness.send_intent(sovereign_id, intent)
            
            # Store in database
            await save_test_result(task_id, {
                "sovereign_id": sovereign_id,
                "intent_id": intent.intent_id,
                "outcome": result.outcome,
                "receipt_valid": result.receipt_valid,
                "article_invoked": result.article_invoked,
                "response_time_ms": result.response_time_ms,
                "reasoning": result.reasoning,
                "error_message": result.error_message
            })
            
            return result
    
    tasks = []
    for sovereign_id in sovereign_ids:
        for intent, mutation in all_tests:
            tasks.append(run_one(sovereign_id, intent, mutation))
    
    results = await asyncio.gather(*tasks)
    
    # Generate summary
    summary = {
        "total_tests": len(results),
        "accepted": sum(1 for r in results if r.outcome == "accepted"),
        "limited": sum(1 for r in results if r.outcome == "limited"),
        "refused": sum(1 for r in results if r.outcome == "refused"),
        "errors": sum(1 for r in results if r.outcome == "error"),
        "receipt_valid_count": sum(1 for r in results if r.receipt_valid),
        "by_sovereign": {}
    }
    
    for r in results:
        if r.sovereign_id not in summary["by_sovereign"]:
            summary["by_sovereign"][r.sovereign_id] = {"accepted": 0, "limited": 0, "refused": 0, "errors": 0}
        category = r.outcome if r.outcome in ["accepted", "limited", "refused"] else "errors"
        summary["by_sovereign"][r.sovereign_id][category] += 1
    
    await update_test_run_summary(task_id, summary)
    return summary
