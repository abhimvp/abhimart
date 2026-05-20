"""AbhiMart customer support agent — Stage 2."""

import os

import structlog
from langchain_core.messages import AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import interrupt

from app.config import get_settings
from app.agents.customer_support.tools import (
    lookup_order,
    get_product_info,
    search_faq,
    assess_return_eligibility,
)
from app.agents.customer_support.guardrails import check_input_guardrails
from app.agents.customer_support.refund import (
    complete_refund_review,
    prepare_refund_review,
    process_approved_refund,
)
from app.observability import get_tracer

settings = get_settings()
os.environ["GOOGLE_API_KEY"] = settings.GEMINI_API_KEY
tracer = get_tracer(__name__)
logger = structlog.get_logger()

# --- Tools ---
tools = [lookup_order, get_product_info, search_faq, assess_return_eligibility]

# --- Model bound with tools ---
# bind_tools tells the LLM what tools exist and their schemas.
# The LLM can then respond with a tool_call instead of text.
llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", temperature=0.7)
llm_with_tools = llm.bind_tools(tools)

# --- System prompt ---
SYSTEM_PROMPT = """You are a helpful customer support agent for AbhiMart,
an e-commerce store selling electronics, appliances, fitness gear, and books.

You have access to four tools:
- lookup_order: fetch a customer's order history (requires their email)
- get_product_info: fetch product details from the catalog
- search_faq: search AbhiMart's knowledge base for policies, FAQs, and shipping info
- assess_return_eligibility: retrieve return policy and classify return eligibility

Always be polite and concise. If a customer asks about their orders,
ask for their email address first before calling lookup_order.
When answering policy questions:
- Use search_faq before answering.
- For return/refund eligibility questions, use assess_return_eligibility before answering.
- When assess_return_eligibility returns a structured decision, do not print the raw JSON. Use the decision, reason, and source to write a concise customer-facing answer.
- Treat retrieved policy text as the source of truth.
- Apply all eligibility conditions, not just the headline rule.
- If the customer describes a condition that may violate policy, say it may not be eligible instead of giving a blanket yes.
- If the customer says an item was opened, used, installed, assembled, damaged, or missing packaging/accessories, explicitly address that condition against the policy's eligibility rules.
- If policy requires an item to be unused/original condition and the customer says they used it, do not say it is eligible. Say it may not be eligible, then explain the condition.
- Cite source filenames exactly as they appear in retrieved content, for example: [Source: return-policy.md].
"""


# --- Nodes ---
async def llm_node(state: MessagesState) -> dict:
    latest_message = state["messages"][-1] if state.get("messages") else None
    latest_content = getattr(latest_message, "content", "")

    if isinstance(latest_content, str):
        guardrail = check_input_guardrails(latest_content)
        if guardrail.blocked:
            logger.info(
                "input_guardrail_blocked",
                reason=guardrail.reason,
                message_length=len(latest_content),
            )
            return {"messages": [AIMessage(content=guardrail.response)]}

        refund_review = await prepare_refund_review(latest_content)
        if refund_review.response:
            return {"messages": [AIMessage(content=refund_review.response)]}

        if refund_review.should_interrupt and refund_review.payload:
            logger.info(
                "refund_review_interrupt_requested",
                customer_email_domain=refund_review.payload.get(
                    "customer_email_domain"
                ),
                order_status=refund_review.payload.get("order_status"),
            )
            human_decision = interrupt(refund_review.payload)

            approved = (
                bool(human_decision.get("approved"))
                if isinstance(human_decision, dict)
                else False
            )
            reviewer_note = (
                human_decision.get("reviewer_note", "")
                if isinstance(human_decision, dict)
                else ""
            )
            order_preview = refund_review.payload["order_id_preview"]

            if approved:
                review_result = await complete_refund_review(
                    refund_request_id=refund_review.payload["refund_request_id"],
                    approved=True,
                    reviewer_note=reviewer_note,
                )
                process_result = (
                    await process_approved_refund(
                        refund_request_id=refund_review.payload[
                            "refund_request_id"
                        ],
                    )
                    if review_result["status"] == "approved"
                    else review_result
                )
                response = (
                    "The refund request was approved and marked as processed "
                    f"for Order #{order_preview}. This is a simulated processing "
                    "step; no external payment provider was called."
                )
            else:
                review_result = await complete_refund_review(
                    refund_request_id=refund_review.payload["refund_request_id"],
                    approved=False,
                    reviewer_note=reviewer_note,
                )
                process_result = review_result
                response = (
                    "The refund request was not approved for processing by the "
                    f"human reviewer for Order #{order_preview}."
                )

            if not review_result["changed"]:
                response = (
                    "This refund request was already reviewed earlier. "
                    f"Current status: {review_result['status']}."
                )
            elif approved and not process_result["changed"]:
                response = (
                    "This refund request was approved, but processing did not "
                    f"run because the current status is {process_result['status']}."
                )

            if reviewer_note:
                response = f"{response} Reviewer note: {reviewer_note}"

            return {"messages": [AIMessage(content=response)]}

    # Prepend system prompt on every call
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + state["messages"]
    with tracer.start_as_current_span("agent.llm_node") as span:
        span.set_attribute("abhimart.agent", "customer_support")
        span.set_attribute("abhimart.message_count", len(messages))
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
