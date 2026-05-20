"""Structured policy-decision helpers for customer support.

The main agent can answer policy questions directly, but some policy workflows
need a more explicit intermediate decision. Return eligibility is one of them:
the model should classify the case before writing a customer-facing answer.
"""

from typing import Literal
from time import perf_counter

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from app.config import get_settings
from app.observability import get_tracer
from app.observability_metrics import record_policy_decision

tracer = get_tracer(__name__)
logger = structlog.get_logger()

PolicyDecision = Literal["eligible", "likely_not_eligible", "need_more_info"]
PolicyConfidence = Literal["low", "medium", "high"]


class PolicyEligibilityDecision(BaseModel):
    """Structured decision for return/refund eligibility questions."""

    decision: PolicyDecision = Field(
        description=(
            "Eligibility classification. Use eligible only when the policy "
            "clearly allows the request. Use likely_not_eligible when the "
            "customer described a condition that likely violates policy. Use "
            "need_more_info when the answer depends on missing details."
        )
    )
    reason: str = Field(description="Short explanation grounded in the policy text.")
    source: str = Field(
        description="Source filename used for the decision, such as return-policy.md."
    )
    confidence: PolicyConfidence = Field(
        description="Confidence in the decision based on the available facts."
    )


POLICY_DECISION_PROMPT = """You classify AbhiMart policy eligibility.

Use only the provided policy text and customer question.
Do not invent policy.

Decision labels:
- eligible: the policy clearly allows the request.
- likely_not_eligible: the customer described a condition that likely violates policy.
- need_more_info: the policy depends on missing details.

Important rules:
- If the policy requires original condition or unused condition and the customer says the item was used, choose likely_not_eligible.
- If the policy requires original packaging/accessories and the customer did not say whether they have them, choose need_more_info unless another stated condition already makes the request likely_not_eligible.
- If the source filename is available, return it exactly.
"""


def _build_policy_decision_llm():
    settings = get_settings()
    llm = ChatGoogleGenerativeAI(
        model="gemini-3.1-flash-lite",
        temperature=0,
        api_key=settings.GEMINI_API_KEY,
    )
    return llm.with_structured_output(PolicyEligibilityDecision)


async def classify_return_eligibility(
    *,
    customer_question: str,
    policy_text: str,
    source: str,
) -> PolicyEligibilityDecision:
    """Classify return eligibility from customer question and policy text."""
    structured_llm = _build_policy_decision_llm()

    with tracer.start_as_current_span("policy.classify_return_eligibility") as span:
        start = perf_counter()
        span.set_attribute("abhimart.policy_source", source)
        span.set_attribute("abhimart.question_length", len(customer_question))
        span.set_attribute("abhimart.policy_text_length", len(policy_text))
        logger.info(
            "policy_classification_started",
            policy_source=source,
            question_length=len(customer_question),
            policy_text_length=len(policy_text),
        )
        response = await structured_llm.ainvoke(
            [
                SystemMessage(content=POLICY_DECISION_PROMPT),
                HumanMessage(
                    content=(
                        f"Customer question:\n{customer_question}\n\n"
                        f"Source filename:\n{source}\n\n"
                        f"Policy text:\n{policy_text}"
                    )
                ),
            ]
        )
        span.set_attribute("abhimart.policy_decision", response.decision)
        span.set_attribute("abhimart.policy_confidence", response.confidence)
        record_policy_decision(response.decision)
        logger.info(
            "policy_classification_completed",
            policy_source=source,
            policy_decision=response.decision,
            policy_confidence=response.confidence,
            duration_ms=round((perf_counter() - start) * 1000, 2),
        )

    return response
