"""OpenTelemetry instrumentation for AEKA backend.

Sets up:
- Distributed tracing (FastAPI auto-instrumentation)
- Custom LLM metrics (tokens, cost, latency per provider/model)
- Request correlation IDs
- Structured log integration
"""

import uuid
from contextvars import ContextVar

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.metrics import Counter, Histogram
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.core.config import get_settings

settings = get_settings()

# ─── Correlation ID ─────────────────────────────────────────────────────────

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


def generate_request_id() -> str:
    """Generate a unique request correlation ID."""
    return str(uuid.uuid4())[:8]


# ─── Tracing Setup ──────────────────────────────────────────────────────────


def setup_tracing() -> TracerProvider:
    """Configure OpenTelemetry tracing with OTLP export."""
    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "service.version": "0.1.0",
            "deployment.environment": settings.app_env,
        }
    )

    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    return provider


# ─── Metrics Setup ───────────────────────────────────────────────────────────


def setup_metrics() -> MeterProvider:
    """Configure OpenTelemetry metrics with OTLP export."""
    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "deployment.environment": settings.app_env,
        }
    )

    exporter = OTLPMetricExporter(endpoint=settings.otel_exporter_otlp_endpoint, insecure=True)
    reader = PeriodicExportingMetricReader(exporter, export_interval_millis=10000)
    provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(provider)

    return provider


# ─── LLM-Specific Metrics ───────────────────────────────────────────────────

meter = metrics.get_meter("aeka.llm")

# Token usage counter
llm_tokens_counter: Counter = meter.create_counter(
    name="aeka.llm.tokens",
    description="Total LLM tokens consumed",
    unit="tokens",
)

# Cost counter
llm_cost_counter: Counter = meter.create_counter(
    name="aeka.llm.cost",
    description="Total LLM cost in USD",
    unit="usd",
)

# Latency histogram
llm_latency_histogram: Histogram = meter.create_histogram(
    name="aeka.llm.latency",
    description="LLM response latency in milliseconds",
    unit="ms",
)

# Retrieval metrics
retrieval_latency_histogram: Histogram = meter.create_histogram(
    name="aeka.retrieval.latency",
    description="Retrieval search latency in milliseconds",
    unit="ms",
)

retrieval_results_histogram: Histogram = meter.create_histogram(
    name="aeka.retrieval.results",
    description="Number of chunks retrieved per query",
    unit="chunks",
)

# Agent metrics
agent_step_counter: Counter = meter.create_counter(
    name="aeka.agent.steps",
    description="Agent graph node executions",
    unit="steps",
)

# HITL metrics
hitl_queue_counter: Counter = meter.create_counter(
    name="aeka.hitl.escalations",
    description="Answers escalated to human review",
    unit="items",
)


def record_llm_call(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: int,
    cost_usd: float,
) -> None:
    """Record metrics for an LLM API call."""
    labels = {"provider": provider, "model": model}

    llm_tokens_counter.add(input_tokens, {**labels, "direction": "input"})
    llm_tokens_counter.add(output_tokens, {**labels, "direction": "output"})
    llm_cost_counter.add(cost_usd, labels)
    llm_latency_histogram.record(latency_ms, labels)


def record_retrieval(latency_ms: float, result_count: int, search_type: str = "hybrid") -> None:
    """Record metrics for a retrieval operation."""
    retrieval_latency_histogram.record(latency_ms, {"search_type": search_type})
    retrieval_results_histogram.record(result_count, {"search_type": search_type})


def record_agent_step(node: str, action: str) -> None:
    """Record metrics for an agent graph step."""
    agent_step_counter.add(1, {"node": node, "action": action})


# ─── FastAPI Integration ─────────────────────────────────────────────────────


def instrument_app(app) -> None:
    """Instrument a FastAPI application with OpenTelemetry."""
    setup_tracing()
    setup_metrics()
    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls="/health,/docs,/redoc,/openapi.json",
    )
