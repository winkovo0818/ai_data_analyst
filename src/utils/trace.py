"""请求追踪工具"""

import uuid
from datetime import datetime
from typing import Dict, List, Any
from pydantic import BaseModel


class StepLog(BaseModel):
    """单步执行日志"""
    tool: str
    args: Dict[str, Any]
    result: Any = None
    error: str | None = None
    latency_ms: float = 0
    timestamp: datetime


class TraceContext:
    """追踪上下文"""

    def __init__(self):
        self.trace_id: str = str(uuid.uuid4())
        self.steps: List[StepLog] = []
        self.start_time = datetime.now()
        self.llm_tokens: int = 0
        self.llm_cost_usd: float = 0.0

    def add_step(self, step: StepLog):
        """添加执行步骤"""
        self.steps.append(step)

    def to_dict(self) -> Dict[str, Any]:
        """转为字典"""
        return {
            "trace_id": self.trace_id,
            "steps": [
                {
                    "tool": s.tool,
                    "latency_ms": s.latency_ms,
                    "error": s.error,
                    "timestamp": s.timestamp.isoformat()
                }
                for s in self.steps
            ],
            "total_steps": len(self.steps),
            "llm_tokens": self.llm_tokens,
            "llm_cost_usd": round(self.llm_cost_usd, 4),
            "duration_ms": (datetime.now() - self.start_time).total_seconds() * 1000
        }
