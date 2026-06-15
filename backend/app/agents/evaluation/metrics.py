"""RAG evaluation metrics — faithfulness, relevance, and accuracy.

Evaluation dimensions:
1. Faithfulness: Is the answer grounded in the retrieved context?
2. Relevance: Are the retrieved chunks relevant to the question?
3. Answer Correctness: Does the answer actually address the question?
4. Citation Accuracy: Do citations match the source content?
"""

import json
from dataclasses import dataclass

from app.services.llm import llm_client


@dataclass
class EvalResult:
    """Result of a single evaluation."""

    metric: str
    score: float  # 0-1
    explanation: str
    details: dict | None = None


@dataclass
class EvalSuite:
    """Complete evaluation of a RAG response."""

    faithfulness: EvalResult
    relevance: EvalResult
    correctness: EvalResult
    citation_accuracy: EvalResult

    @property
    def overall_score(self) -> float:
        """Weighted average of all metrics."""
        weights = {
            "faithfulness": 0.35,
            "relevance": 0.25,
            "correctness": 0.25,
            "citation_accuracy": 0.15,
        }
        return (
            self.faithfulness.score * weights["faithfulness"]
            + self.relevance.score * weights["relevance"]
            + self.correctness.score * weights["correctness"]
            + self.citation_accuracy.score * weights["citation_accuracy"]
        )


FAITHFULNESS_PROMPT = """Evaluate the faithfulness of this answer to the provided context.

Faithfulness means: every claim in the answer can be traced back to the context.

Context:
{context}

Answer:
{answer}

Score 0.0 to 1.0 where:
- 1.0 = Every claim is directly supported by the context
- 0.5 = Some claims are supported, some are inferred
- 0.0 = The answer contains fabricated information

Respond with JSON: {{"score": 0.0-1.0, "explanation": "...", "unsupported_claims": [...]}}"""

RELEVANCE_PROMPT = """Evaluate how relevant the retrieved context is to the question.

Question: {question}

Retrieved context:
{context}

Score 0.0 to 1.0 where:
- 1.0 = All retrieved chunks are directly relevant
- 0.5 = Some chunks are relevant, some are noise
- 0.0 = No chunks are relevant to the question

Respond with JSON: {{"score": 0.0-1.0, "explanation": "...", "relevant_count": N, "total_count": N}}"""

CORRECTNESS_PROMPT = """Evaluate if this answer correctly addresses the question.

Question: {question}

Answer: {answer}

Expected answer (if available): {expected}

Score 0.0 to 1.0 where:
- 1.0 = Completely and correctly answers the question
- 0.5 = Partially correct or incomplete
- 0.0 = Incorrect or doesn't address the question

Respond with JSON: {{"score": 0.0-1.0, "explanation": "...", "missing_aspects": [...]}}"""


async def evaluate_faithfulness(context: str, answer: str) -> EvalResult:
    """Evaluate if the answer is grounded in the context."""
    response = await llm_client.complete(
        messages=[
            {
                "role": "user",
                "content": FAITHFULNESS_PROMPT.format(context=context, answer=answer),
            }
        ],
        temperature=0.0,
        max_tokens=512,
    )

    try:
        result = json.loads(response.content)
        return EvalResult(
            metric="faithfulness",
            score=float(result["score"]),
            explanation=result["explanation"],
            details={"unsupported_claims": result.get("unsupported_claims", [])},
        )
    except (json.JSONDecodeError, KeyError):
        return EvalResult(metric="faithfulness", score=0.5, explanation="Evaluation parse error")


async def evaluate_relevance(question: str, context: str) -> EvalResult:
    """Evaluate if retrieved chunks are relevant to the question."""
    response = await llm_client.complete(
        messages=[
            {
                "role": "user",
                "content": RELEVANCE_PROMPT.format(question=question, context=context),
            }
        ],
        temperature=0.0,
        max_tokens=512,
    )

    try:
        result = json.loads(response.content)
        return EvalResult(
            metric="relevance",
            score=float(result["score"]),
            explanation=result["explanation"],
            details={
                "relevant_count": result.get("relevant_count"),
                "total_count": result.get("total_count"),
            },
        )
    except (json.JSONDecodeError, KeyError):
        return EvalResult(metric="relevance", score=0.5, explanation="Evaluation parse error")


async def evaluate_correctness(
    question: str, answer: str, expected: str = ""
) -> EvalResult:
    """Evaluate if the answer correctly addresses the question."""
    response = await llm_client.complete(
        messages=[
            {
                "role": "user",
                "content": CORRECTNESS_PROMPT.format(
                    question=question, answer=answer, expected=expected or "Not provided"
                ),
            }
        ],
        temperature=0.0,
        max_tokens=512,
    )

    try:
        result = json.loads(response.content)
        return EvalResult(
            metric="correctness",
            score=float(result["score"]),
            explanation=result["explanation"],
            details={"missing_aspects": result.get("missing_aspects", [])},
        )
    except (json.JSONDecodeError, KeyError):
        return EvalResult(metric="correctness", score=0.5, explanation="Evaluation parse error")


def evaluate_citation_accuracy(answer: str, sources: list[dict]) -> EvalResult:
    """Check if [Source N] citations in the answer match actual sources.

    This is a deterministic check — no LLM needed.
    """
    import re

    # Find all citations in the answer
    citations = re.findall(r"\[Source (\d+)\]", answer)
    cited_indices = set(int(c) for c in citations)

    # Check if cited indices are valid
    valid_indices = set(range(1, len(sources) + 1))
    invalid_citations = cited_indices - valid_indices

    if not citations:
        return EvalResult(
            metric="citation_accuracy",
            score=0.5,  # No citations — could be good or bad
            explanation="No citations found in answer",
            details={"citation_count": 0},
        )

    accuracy = 1.0 - (len(invalid_citations) / len(cited_indices)) if cited_indices else 0.0

    return EvalResult(
        metric="citation_accuracy",
        score=accuracy,
        explanation=f"{len(cited_indices)} citations, {len(invalid_citations)} invalid",
        details={
            "total_citations": len(citations),
            "unique_sources_cited": len(cited_indices),
            "invalid_citations": list(invalid_citations),
        },
    )


async def run_full_evaluation(
    question: str,
    answer: str,
    context: str,
    sources: list[dict],
    expected_answer: str = "",
) -> EvalSuite:
    """Run the complete evaluation suite on a RAG response."""
    faithfulness = await evaluate_faithfulness(context, answer)
    relevance = await evaluate_relevance(question, context)
    correctness = await evaluate_correctness(question, answer, expected_answer)
    citation_accuracy = evaluate_citation_accuracy(answer, sources)

    return EvalSuite(
        faithfulness=faithfulness,
        relevance=relevance,
        correctness=correctness,
        citation_accuracy=citation_accuracy,
    )
