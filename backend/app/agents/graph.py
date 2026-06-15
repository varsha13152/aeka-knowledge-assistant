"""LangGraph multi-agent orchestration graph.

The AEKA agent system uses a state machine architecture:

    ┌─────────┐     ┌──────────┐     ┌───────────┐     ┌───────────┐
    │  Router  │────▶│ Research  │────▶│ Validator  │────▶│   Output  │
    └─────────┘     └──────────┘     └───────────┘     └───────────┘
         │                                  │
         │ (direct answer)                  │ (low confidence)
         ▼                                  ▼
    ┌─────────┐                      ┌───────────┐
    │  Output  │                      │ Escalation │
    └─────────┘                      └───────────┘

Nodes:
- Router: Classifies intent and routes to the appropriate specialist
- Research: Performs RAG retrieval and synthesizes an answer
- Validator: Checks for hallucinations against source chunks
- Escalation: Routes low-confidence answers to HITL queue
"""

from __future__ import annotations

from typing import Annotated, TypedDict

from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from app.agents.escalator import escalation_node
from app.agents.guardrails import input_guardrail_node, output_guardrail_node
from app.agents.researcher import research_node
from app.agents.router import router_node
from app.agents.validator import validator_node


# ─── State Definition ───────────────────────────────────────────────────────


class AgentState(TypedDict):
    """State shared across all agent nodes in the graph."""

    # Input
    query: str
    session_id: str
    messages: Annotated[list, add_messages]

    # Routing
    intent: str  # "question" | "summary" | "direct" | "unsafe"
    routed_to: str

    # Research
    context_chunks: list[dict]  # Retrieved document chunks
    raw_answer: str
    sources: list[dict]

    # Validation
    confidence_score: float  # 0-1
    hallucination_flags: list[dict]
    is_valid: bool

    # Output
    final_answer: str
    requires_review: bool
    review_reason: str

    # Metadata
    agent_steps: list[dict]  # For frontend visualization
    total_tokens: int
    total_cost: float


# ─── Routing Logic ──────────────────────────────────────────────────────────


def route_after_guardrail(state: AgentState) -> str:
    """Route based on guardrail check."""
    if state.get("intent") == "unsafe":
        return "output"
    return "router"


def route_after_router(state: AgentState) -> str:
    """Route based on intent classification."""
    intent = state.get("intent", "question")
    if intent == "direct":
        return "output"
    return "research"


def route_after_validator(state: AgentState) -> str:
    """Route based on validation results."""
    if state.get("requires_review", False):
        return "escalation"
    return "output_guardrail"


# ─── Graph Construction ─────────────────────────────────────────────────────


def build_agent_graph() -> StateGraph:
    """Construct the multi-agent LangGraph state machine.

    Returns a compiled graph ready for invocation.
    """
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("input_guardrail", input_guardrail_node)
    graph.add_node("router", router_node)
    graph.add_node("research", research_node)
    graph.add_node("validator", validator_node)
    graph.add_node("escalation", escalation_node)
    graph.add_node("output_guardrail", output_guardrail_node)
    graph.add_node("output", output_node)

    # Define edges
    graph.set_entry_point("input_guardrail")

    graph.add_conditional_edges("input_guardrail", route_after_guardrail)
    graph.add_conditional_edges("router", route_after_router)
    graph.add_edge("research", "validator")
    graph.add_conditional_edges("validator", route_after_validator)
    graph.add_edge("escalation", "output")
    graph.add_edge("output_guardrail", "output")
    graph.add_edge("output", END)

    return graph.compile()


def output_node(state: AgentState) -> dict:
    """Final output node — packages the response."""
    # If unsafe, provide a safe response
    if state.get("intent") == "unsafe":
        return {
            "final_answer": "I'm unable to help with that request. Please ask something else.",
            "agent_steps": state.get("agent_steps", [])
            + [{"node": "output", "action": "blocked_unsafe_query"}],
        }

    # Use validated answer or raw answer
    answer = state.get("final_answer") or state.get("raw_answer", "I couldn't find an answer.")

    return {
        "final_answer": answer,
        "agent_steps": state.get("agent_steps", [])
        + [{"node": "output", "action": "delivered_response"}],
    }


# Compiled graph singleton
agent_graph = build_agent_graph()
