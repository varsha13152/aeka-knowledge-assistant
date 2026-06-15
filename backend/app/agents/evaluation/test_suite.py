"""Automated evaluation test suite for RAG quality.

Runs a labeled evaluation dataset through the RAG pipeline and reports
aggregate quality metrics. Use for:
- Regression testing after model/prompt changes
- A/B testing prompt variants
- Benchmarking chunking strategy performance
"""

import json
import time
from dataclasses import dataclass
from pathlib import Path

from app.agents.evaluation.drift_detector import drift_detector
from app.agents.evaluation.metrics import EvalSuite, run_full_evaluation
from app.db.session import async_session_factory
from app.services.llm import llm_client
from app.services.retrieval import build_context_window, hybrid_search


@dataclass
class EvalCase:
    """A single evaluation test case."""

    id: str
    query: str
    expected_answer: str  # Ground truth or reference answer
    required_sources: list[str]  # Document IDs that should be retrieved
    category: str  # For category-level reporting


@dataclass
class EvalRunResult:
    """Results from running the full evaluation suite."""

    total_cases: int
    avg_faithfulness: float
    avg_relevance: float
    avg_correctness: float
    avg_citation_accuracy: float
    overall_score: float
    latency_p50_ms: int
    latency_p95_ms: int
    total_cost_usd: float
    failures: list[dict]
    category_breakdown: dict[str, dict]
    duration_seconds: float


def load_eval_dataset(path: str = "tests/eval_dataset.json") -> list[EvalCase]:
    """Load evaluation dataset from JSON file.

    Expected format:
    [
        {
            "id": "eval-001",
            "query": "What is the refund policy?",
            "expected_answer": "Refunds are available within 30 days...",
            "required_sources": ["doc-uuid-1"],
            "category": "policy"
        }
    ]
    """
    dataset_path = Path(path)
    if not dataset_path.exists():
        return _generate_sample_dataset()

    with open(dataset_path) as f:
        data = json.load(f)

    return [EvalCase(**case) for case in data]


async def run_eval_suite(
    dataset: list[EvalCase] | None = None,
    prompt_variant: str | None = None,
) -> EvalRunResult:
    """Run the evaluation suite against the RAG pipeline.

    Args:
        dataset: Evaluation cases to run (loads default if None)
        prompt_variant: Optional prompt variant for A/B testing

    Returns:
        Aggregate metrics and per-case results
    """
    if dataset is None:
        dataset = load_eval_dataset()

    start_time = time.time()
    results: list[EvalSuite] = []
    latencies: list[int] = []
    total_cost = 0.0
    failures: list[dict] = []
    category_scores: dict[str, list[float]] = {}

    for case in dataset:
        case_start = time.perf_counter()

        try:
            # Run retrieval
            async with async_session_factory() as db:
                search_results = await hybrid_search(db=db, query=case.query, top_k=8)

            context, chunks = build_context_window(search_results, max_tokens=4096)

            # Generate answer
            response = await llm_client.complete(
                messages=[{"role": "user", "content": case.query}],
                system_prompt=_get_system_prompt(context, prompt_variant),
                max_tokens=1024,
            )

            # Evaluate
            eval_result = await run_full_evaluation(
                question=case.query,
                answer=response.content,
                context=context,
                sources=[{"chunk_id": str(c.chunk_id)} for c in chunks],
                expected_answer=case.expected_answer,
            )

            results.append(eval_result)
            total_cost += response.cost_usd

            # Track latency
            latency_ms = int((time.perf_counter() - case_start) * 1000)
            latencies.append(latency_ms)

            # Track by category
            if case.category not in category_scores:
                category_scores[case.category] = []
            category_scores[case.category].append(eval_result.overall_score)

            # Record in drift detector
            drift_detector.record(
                query=case.query,
                metrics={
                    "faithfulness": eval_result.faithfulness.score,
                    "relevance": eval_result.relevance.score,
                    "correctness": eval_result.correctness.score,
                },
            )

            # Track failures
            if eval_result.overall_score < 0.6:
                failures.append({
                    "case_id": case.id,
                    "query": case.query,
                    "score": eval_result.overall_score,
                    "faithfulness": eval_result.faithfulness.score,
                    "explanation": eval_result.faithfulness.explanation,
                })

        except Exception as e:
            failures.append({
                "case_id": case.id,
                "query": case.query,
                "error": str(e),
            })

    # Compute aggregates
    if not results:
        return EvalRunResult(
            total_cases=len(dataset),
            avg_faithfulness=0.0,
            avg_relevance=0.0,
            avg_correctness=0.0,
            avg_citation_accuracy=0.0,
            overall_score=0.0,
            latency_p50_ms=0,
            latency_p95_ms=0,
            total_cost_usd=total_cost,
            failures=failures,
            category_breakdown={},
            duration_seconds=time.time() - start_time,
        )

    latencies.sort()
    p50_idx = len(latencies) // 2
    p95_idx = int(len(latencies) * 0.95)

    category_breakdown = {
        cat: {"avg_score": sum(scores) / len(scores), "count": len(scores)}
        for cat, scores in category_scores.items()
    }

    return EvalRunResult(
        total_cases=len(dataset),
        avg_faithfulness=sum(r.faithfulness.score for r in results) / len(results),
        avg_relevance=sum(r.relevance.score for r in results) / len(results),
        avg_correctness=sum(r.correctness.score for r in results) / len(results),
        avg_citation_accuracy=sum(r.citation_accuracy.score for r in results) / len(results),
        overall_score=sum(r.overall_score for r in results) / len(results),
        latency_p50_ms=latencies[p50_idx] if latencies else 0,
        latency_p95_ms=latencies[p95_idx] if latencies else 0,
        total_cost_usd=total_cost,
        failures=failures,
        category_breakdown=category_breakdown,
        duration_seconds=time.time() - start_time,
    )


def _get_system_prompt(context: str, variant: str | None = None) -> str:
    """Get system prompt, optionally using an A/B test variant."""
    base_prompt = (
        "You are AEKA, an enterprise knowledge assistant. Answer based on the context.\n"
        "Rules: Cite sources using [Source N]. Only use information from the context.\n\n"
        f"Context:\n{context}"
    )

    if variant == "detailed":
        return (
            "You are AEKA, a thorough enterprise knowledge assistant.\n"
            "Rules:\n"
            "1. Answer ONLY from the provided context\n"
            "2. Cite every fact with [Source N]\n"
            "3. If information is missing, say so explicitly\n"
            "4. Structure complex answers with bullet points\n"
            "5. End with a confidence note if uncertain\n\n"
            f"Context:\n{context}"
        )

    if variant == "concise":
        return (
            "You are AEKA. Answer briefly from the context. Cite with [Source N].\n\n"
            f"Context:\n{context}"
        )

    return base_prompt


def _generate_sample_dataset() -> list[EvalCase]:
    """Generate a sample eval dataset for testing."""
    return [
        EvalCase(
            id="sample-001",
            query="What are the main features of the system?",
            expected_answer="The system includes document management, RAG search, and multi-agent orchestration.",
            required_sources=[],
            category="general",
        ),
        EvalCase(
            id="sample-002",
            query="How does the authentication work?",
            expected_answer="Authentication uses JWT tokens with refresh token rotation.",
            required_sources=[],
            category="technical",
        ),
        EvalCase(
            id="sample-003",
            query="What is the refund policy?",
            expected_answer="Refunds are available within 30 days of purchase.",
            required_sources=[],
            category="policy",
        ),
    ]
