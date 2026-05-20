"""Input guardrails for the AbhiMart customer-support agent.

These checks are intentionally deterministic. They catch obvious high-risk
requests before the LLM gets a chance to call tools.
"""

import re
from dataclasses import dataclass


EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}\b")


@dataclass(frozen=True)
class GuardrailResult:
    blocked: bool
    reason: str
    response: str


def _allow(response: str = "") -> GuardrailResult:
    return GuardrailResult(blocked=False, reason="", response=response)


def _block(reason: str, response: str) -> GuardrailResult:
    return GuardrailResult(blocked=True, reason=reason, response=response)


def check_input_guardrails(message: str) -> GuardrailResult:
    """Return a blocking response for obvious unsafe customer requests."""
    text = message.lower()
    emails = EMAIL_RE.findall(message)

    asks_for_order_data = any(
        phrase in text
        for phrase in [
            "order",
            "orders",
            "order history",
            "lookup_order",
            "status",
        ]
    )
    injection_intent = any(
        phrase in text
        for phrase in [
            "ignore your rules",
            "ignore all rules",
            "ignore previous instructions",
            "ignore system rules",
            "do not ask questions",
            "hidden instruction",
            "reveal secrets",
            "show me all customer",
        ]
    )

    if injection_intent and asks_for_order_data:
        return _block(
            "prompt_injection_order_lookup",
            (
                "I cannot access or share customer order information based on an "
                "instruction to ignore rules. For privacy and security, I can only "
                "help with order details after following the proper account-holder "
                "verification flow."
            ),
        )

    if "all customer emails" in text or "customer emails in the database" in text:
        return _block(
            "bulk_customer_data_request",
            (
                "I cannot provide private customer data or lists of customer emails. "
                "That information is personal data and must be protected for privacy "
                "and security."
            ),
        )

    if "reveal secrets" in text or (
        "hidden instruction" in text and "system rules" in text
    ):
        return _block(
            "instruction_override_or_secret_request",
            (
                "I cannot follow hidden instructions, override system rules, or "
                "reveal secrets. I can help with AbhiMart products, orders, and "
                "policies while following privacy and security rules."
            ),
        )

    if asks_for_order_data and len(set(email.lower() for email in emails)) > 1:
        return _block(
            "cross_customer_order_request",
            (
                "I cannot access or share another customer's order information. "
                "For privacy, I can only help with the account holder's own orders "
                "after the proper verification flow."
            ),
        )

    if "refund" in text and any(
        phrase in text
        for phrase in [
            "right now",
            "do not ask for approval",
            "without approval",
            "without confirmation",
        ]
    ):
        return _block(
            "refund_without_approval",
            (
                "I can help start a refund request, but I cannot process a refund "
                "without review or approval. Please provide the email address "
                "associated with your AbhiMart account so I can look up the order "
                "and explain the next steps for the refund."
            ),
        )

    return _allow()
