"""测试工具绑定"""
import sys
sys.path.insert(0, 'D:/hds/project/ai_data_analyst')

from src.engines.llm_agent import LLMAgent

# 创建 agent
config = {
    "provider": "openai",
    "api_key": "test-key",
    "model": "gpt-4",
}

try:
    agent = LLMAgent(config)
    print(f"✓ 创建成功")
    print(f"✓ 工具数量: {len(agent.tools)}")
    for tool in agent.tools:
        print(f"  - {tool.name}")
        print(f"    描述: {tool.description[:80]}")
        print(f"    参数: {tool.args}")
except Exception as e:
    print(f"✗ 创建失败: {e}")
    import traceback
    traceback.print_exc()
