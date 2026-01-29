"""速率限制器"""

import time
from collections import defaultdict
from typing import Dict
from src.utils.logger import log


class RateLimiter:
    """简单的速率限制器"""

    def __init__(self, max_requests: int = 100, time_window: int = 60):
        """
        初始化速率限制器

        Args:
            max_requests: 时间窗口内最大请求数
            time_window: 时间窗口（秒）
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: Dict[str, list] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        """
        检查是否允许请求

        Args:
            key: 限流键（如用户ID、IP）

        Returns:
            是否允许
        """
        now = time.time()

        # 清理过期记录
        self.requests[key] = [
            ts for ts in self.requests[key]
            if now - ts < self.time_window
        ]

        # 检查是否超限
        if len(self.requests[key]) >= self.max_requests:
            log.warning(f"速率限制触发: {key}")
            return False

        # 记录本次请求
        self.requests[key].append(now)
        return True

    def get_remaining(self, key: str) -> int:
        """获取剩余请求数"""
        now = time.time()
        self.requests[key] = [
            ts for ts in self.requests[key]
            if now - ts < self.time_window
        ]
        return max(0, self.max_requests - len(self.requests[key]))


# 全局限流器
_rate_limiter = RateLimiter(max_requests=100, time_window=60)


def get_rate_limiter() -> RateLimiter:
    """获取全局限流器"""
    return _rate_limiter
