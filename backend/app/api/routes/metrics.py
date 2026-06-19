"""Metrics endpoint — expose LLM cost, latency, and quality metrics for the dashboard."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.auth import AdminUser
from app.agents.evaluation.drift_detector import drift_detector

router = APIRouter(prefix="/metrics", tags=["metrics"])


class MetricsSummary(BaseModel):
    drift_report: dict
    recent_failures: list[dict]


@router.get("/", response_model=MetricsSummary)
async def get_metrics(current_user: AdminUser):
    """Get current system metrics and drift analysis. Requires admin/tutor role."""
    report = drift_detector.analyze()

    return MetricsSummary(
        drift_report={
            "overall_health": report.overall_health,
            "timestamp": report.timestamp,
            "metrics": report.metrics,
            "alerts": report.alerts,
            "recommendations": report.recommendations,
        },
        recent_failures=drift_detector.get_recent_failures(10),
    )
