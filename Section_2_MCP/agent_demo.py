"""Host 2: a LangChain agent (create_agent) that answers a research question with the server's tools.

    python agent_demo.py                                   # the default research question
    python agent_demo.py "What is known about gut microbiome changes in Parkinson's disease?"

The model provider is explicit (LLM_PROVIDER, default openllm). Nothing switches provider on errors.
"""

import asyncio
import os
import sys

from langchain.agents import create_agent
from langchain.mcp import MCPAdapter

from litreview import config
from litreview.evidence import ids_in_text, ids_in_tool_messages, unsupported_citations
from litreview.policy import APPROVED_TOOLS, make_policy_middleware
from litreview.texts import AGENT_SYSTEM_PROMPT
from litreview.workshop import final_text, make_llm, print_trace


async def main(url: str, question: str) -> None:
    async with MCPAdapter(url) as adapter:
        offered = await adapter.list_tools()
    tools = [tool for tool in offered if tool.name in APPROVED_TOOLS]
    denied: list = []
    agent = create_agent(
        model=make_llm(),
        tools=tools,
        system_prompt=AGENT_SYSTEM_PROMPT,
        middleware=[make_policy_middleware(denied)],
    )
    run = await agent.ainvoke(
        {"messages": [{"role": "user", "content": question}]},
        config={"recursion_limit": 16},
    )
    print_trace(run)
    unsupported = unsupported_citations(ids_in_text(final_text(run)), ids_in_tool_messages(run["messages"]))
    print("\nUnsupported citations:", unsupported or "none")
    print("Denied tool calls:", denied or "none")


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]).strip() or config.DEFAULT_QUESTION
    asyncio.run(main(os.environ.get("MCP_URL", "http://127.0.0.1:8000/mcp"), question))
