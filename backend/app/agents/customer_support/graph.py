"""AbhiMart customer support agent — Stage 2."""

import os

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition

from app.config import get_settings
from app.agents.customer_support.tools import lookup_order, get_product_info

settings = get_settings()
os.environ["GOOGLE_API_KEY"] = settings.GEMINI_API_KEY

# --- Tools ---
tools = [lookup_order, get_product_info]

# --- Model bound with tools ---
# bind_tools tells the LLM what tools exist and their schemas.
# The LLM can then respond with a tool_call instead of text.
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0.7)
llm_with_tools = llm.bind_tools(tools)

# --- System prompt ---
SYSTEM_PROMPT = """You are a helpful customer support agent for AbhiMart, 
an e-commerce store selling electronics, appliances, fitness gear, and books.

You have access to two tools:
- lookup_order: fetch a customer's order history (requires their email)
- get_product_info: fetch product details from the catalog

Always be polite and concise. If a customer asks about their orders, 
ask for their email address first before calling lookup_order."""


# --- Nodes ---
async def llm_node(state: MessagesState) -> dict:
    # Prepend system prompt on every call
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + state["messages"]
    response = await llm_with_tools.ainvoke(messages)
    return {"messages": [response]}


# --- Graph factory ---
def build_graph(checkpointer):
    graph = StateGraph(MessagesState)

    graph.add_node("llm", llm_node)
    graph.add_node("tools", ToolNode(tools))

    graph.add_edge(START, "llm")

    # tools_condition checks the last message:
    # - if it contains tool_calls → route to "tools"
    # - if it's a plain text response → route to END
    graph.add_conditional_edges("llm", tools_condition)

    # After tools execute → always go back to LLM
    # so the LLM can see the tool result and respond
    graph.add_edge("tools", "llm")

    return graph.compile(checkpointer=checkpointer)
