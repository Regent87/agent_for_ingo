# app/agent.py
import os
import re
import asyncio
from collections.abc import AsyncIterable
from typing import Any, Literal

from langchain_core.messages import AIMessage, ToolMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_community.tools import DuckDuckGoSearchResults
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode, tools_condition
from pydantic import BaseModel

memory = MemorySaver()

# === Инструменты ===
@tool
def calculator(expression: str) -> str:
    """Evaluates a mathematical expression and returns the result as a string.

    Args:
        expression: A string containing a valid arithmetic expression
                    (e.g., "155 / 29", "(10 + 5) * 2").
                    Supported operators: +, -, *, /, //, %, **, and parentheses.
    """
    expr = expression.strip()
    if not re.fullmatch(r'[\d+\-*/().\s%]+', expr):
        return "Error: Invalid characters in expression."
    try:
        result = eval(expr, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"Error: {e}"

search_web = DuckDuckGoSearchResults(
    name="search_web",
    #description="Search the web for real-world facts (e.g., speeds, distances, dimensions)."
    num_results = 10
)

tools = [calculator, search_web]

# === Системное сообщение ===
SYSTEM_INSTRUCTION = (
    "You are a precise assistant that answers questions by using tools when needed. "
    "1. If you lack factual data (e.g., speeds, distances, sizes), use the 'search_web' tool to retrieve it. "
    "2. Once you have all necessary numbers, use the 'calculator' tool to compute the result. "
    "3. Your final output MUST include: "
    "   - The final answer, "
    "   - The key values and facts used (e.g., 'leopard speed: 29 m/s', 'bridge length: 155 m'), "
    "   - The calculation performed (e.g., '155 / 29 = 5.34'). "
    "Do NOT include apologies, extra commentary, or unrelated text. "
    "All calculations must use meters and seconds; convert units if necessary."
)

class MathAgent:
    """Math & Search Agent compatible with A2A protocol."""

    def __init__(self):
        PROXY_URLS = os.getenv("PROXY_URLS")
        self.model = ChatOpenAI(
            model="gpt-4o",
            openai_api_base=PROXY_URLS,
            temperature=0,
        )
        self.tools = tools
        self.llm_with_tools = self.model.bind_tools(self.tools, parallel_tool_calls=False)

        def assistant(state: MessagesState):
            return {"messages": [self.llm_with_tools.invoke([SystemMessage(content=SYSTEM_INSTRUCTION)] + state["messages"])]}

        builder = StateGraph(MessagesState)
        builder.add_node("assistant", assistant)
        builder.add_node("tools", ToolNode(self.tools))
        builder.add_edge(START, "assistant")
        builder.add_conditional_edges("assistant", tools_condition)
        builder.add_edge("tools", "assistant")
        self.graph = builder.compile(checkpointer=memory)

    async def stream(self, query: str, context_id: str) -> AsyncIterable[dict[str, Any]]:
        inputs = {"messages": [HumanMessage(content=query)]}
        config = {"configurable": {"thread_id": context_id}}

        # 🔥 ВСЕГДА отправляем первое событие для streaming
        yield {
            "is_task_complete": False,
            "require_user_input": False,
            "content": "Processing your request...",
        }

        # Запускаем синхронный граф в отдельном потоке
        def _run_graph():
            return list(self.graph.stream(inputs, config, stream_mode="values"))

        loop = asyncio.get_event_loop()
        steps = await loop.run_in_executor(None, _run_graph)

        for step in steps:
            message = step["messages"][-1]
            if isinstance(message, AIMessage) and hasattr(message, "tool_calls") and message.tool_calls:
                yield {
                    "is_task_complete": False,
                    "require_user_input": False,
                    "content": "Gathering information...",
                }
            elif isinstance(message, ToolMessage):
                yield {
                    "is_task_complete": False,
                    "require_user_input": False,
                    "content": "Performing calculation...",
                }

        # Финальный ответ
        final_state = self.graph.get_state(config)
        final_message = final_state.values["messages"][-1]
        content = (
            final_message.content.strip()
            if isinstance(final_message, AIMessage) and final_message.content
            else "No answer generated."
        )

        yield {
            "is_task_complete": True,
            "require_user_input": False,
            "content": content,
        }

    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]