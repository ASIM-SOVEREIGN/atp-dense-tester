"""
Core ATP test harness - submits intents to sovereigns and verifies responses
"""

import time
import httpx
from typing import Dict, Any, Optional
from src.models.intent import ATPIntent, TestResult

class ATPTestHarness:
    def __init__(self, endpoints: Dict[str, str], timeout: int = 30):
        self.endpoints = endpoints
        self.timeout = timeout
    
    async def send_intent(self, sovereign_id: str, intent: ATPIntent) -> TestResult:
        """Send a single intent to a sovereign"""
        endpoint = self.endpoints.get(sovereign_id)
        if not endpoint:
            return TestResult(
                task_id="",
                sovereign_id=sovereign_id,
                intent=intent,
                outcome="error",
                error_message=f"No endpoint configured for {sovereign_id}"
            )
        
        result = TestResult(
            task_id="",
            sovereign_id=sovereign_id,
            intent=intent,
            outcome="error"
        )
        
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{endpoint}/api/atp/intent",
                    json=intent.model_dump(),
                    headers={"Content-Type": "application/json"}
                )
            
            result.response_time_ms = int((time.time() - start_time) * 1000)
            
            if response.status_code == 200:
                data = response.json()
                result.outcome = data.get("outcome", "error")
                result.receipt_valid = data.get("receipt_valid", False)
                result.article_invoked = data.get("article_invoked")
                result.reasoning = data.get("reasoning", "")
            else:
                result.outcome = "refused" if response.status_code == 403 else "error"
                result.error_message = f"HTTP {response.status_code}"
                
        except httpx.TimeoutException:
            result.outcome = "error"
            result.error_message = f"Timeout after {self.timeout}s"
            result.response_time_ms = self.timeout * 1000
        except Exception as e:
            result.outcome = "error"
            result.error_message = str(e)
        
        return result
