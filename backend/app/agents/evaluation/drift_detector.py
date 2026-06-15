"""Drift detection — monitors output quality over time.

Tracks evaluation metrics over sliding windows to detect:
- Quality degradation (model drift)
- Systematic hallucination patterns
- Topic-specific accuracy issues
"""

import json
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MetricWindow:
    """Sliding window of metric values."""

    values: deque = field(default_factory=lambda: deque(maxlen=100))

    @property
    def mean(self) -> float:
        return sum(self.values) / len(self.values) if self.values else 0.0

    @property
    def trend(self) -> str:
        """Detect if metrics are trending up, down, or stable."""
        if len(self.values) < 10:
            return "insufficient_data"

        recent = list(self.values)[-10:]
        older = list(self.values)[-20:-10] if len(self.values) >= 20 else list(self.values)[:10]

        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)

        diff = recent_avg - older_avg
        if diff < -0.1:
            return "degrading"
        elif diff > 0.1:
            return "improving"
        return "stable"


@dataclass
class DriftReport:
    """Summary of drift analysis."""

    timestamp: str
    overall_health: str  # "healthy" | "warning" | "critical"
    metrics: dict[str, dict]
    alerts: list[str]
    recommendations: list[str]


class DriftDetector:
    """Monitor RAG system quality over time.

    Maintains sliding windows of evaluation metrics and raises
    alerts when quality degrades below thresholds.
    """

    def __init__(self):
        self.windows: dict[str, MetricWindow] = {
            "faithfulness": MetricWindow(),
            "relevance": MetricWindow(),
            "correctness": MetricWindow(),
            "citation_accuracy": MetricWindow(),
            "confidence": MetricWindow(),
        }
        self.alert_thresholds = {
            "faithfulness": 0.7,
            "relevance": 0.6,
            "correctness": 0.6,
            "confidence": 0.65,
        }
        self.query_log: deque = deque(maxlen=500)

    def record(
        self,
        query: str,
        metrics: dict[str, float],
        metadata: dict | None = None,
    ) -> None:
        """Record evaluation results for drift tracking."""
        for metric_name, value in metrics.items():
            if metric_name in self.windows:
                self.windows[metric_name].values.append(value)

        self.query_log.append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "query": query[:200],
                "metrics": metrics,
                "metadata": metadata,
            }
        )

    def analyze(self) -> DriftReport:
        """Analyze current drift status and generate report."""
        alerts = []
        recommendations = []
        metric_summaries = {}

        for metric_name, window in self.windows.items():
            trend = window.trend
            mean = window.mean
            threshold = self.alert_thresholds.get(metric_name, 0.5)

            metric_summaries[metric_name] = {
                "mean": round(mean, 3),
                "trend": trend,
                "sample_count": len(window.values),
                "below_threshold": mean < threshold,
            }

            if mean < threshold:
                alerts.append(
                    f"⚠️ {metric_name} mean ({mean:.2f}) is below threshold ({threshold})"
                )

            if trend == "degrading":
                alerts.append(f"📉 {metric_name} is showing a degrading trend")
                recommendations.append(
                    f"Investigate {metric_name} degradation — consider re-indexing "
                    "documents or adjusting chunking strategy"
                )

        # Determine overall health
        if any("below threshold" in a for a in alerts):
            health = "critical"
        elif any("degrading" in a for a in alerts):
            health = "warning"
        else:
            health = "healthy"

        return DriftReport(
            timestamp=datetime.utcnow().isoformat(),
            overall_health=health,
            metrics=metric_summaries,
            alerts=alerts,
            recommendations=recommendations,
        )

    def get_recent_failures(self, n: int = 10) -> list[dict]:
        """Get recent queries that scored poorly."""
        recent = list(self.query_log)
        failures = [
            entry
            for entry in recent
            if any(
                entry["metrics"].get(m, 1.0) < self.alert_thresholds.get(m, 0.5)
                for m in self.alert_thresholds
            )
        ]
        return failures[-n:]


# Singleton instance
drift_detector = DriftDetector()
