"""AbhiMart customer support agent — Stage 1."""

import os

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.memory import InMemorySaver

from app.config import get_settings

settings = get_settings()
os.environ["GOOGLE_API_KEY"] = settings.GEMINI_API_KEY

# --- Model ---
llm = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite",
    temperature=0.7,
)


# --- Node ---
async def llm_node(state: MessagesState) -> dict:
    response = await llm.ainvoke(state["messages"])
    return {"messages": [response]}


# --- Graph ---
def build_graph():
    graph = StateGraph(MessagesState)
    graph.add_node("llm", llm_node)
    graph.add_edge(START, "llm")
    graph.add_edge("llm", END)
    memory = InMemorySaver()
    return graph.compile(checkpointer=memory)


graph = build_graph()
