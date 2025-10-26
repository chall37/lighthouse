"""
Threshold evaluator for Lighthouse.
"""

from lighthouse.core import AlertDecision, Evaluator, ObservationResult
from lighthouse.registry import register_evaluator


@register_evaluator("threshold")
class ThresholdEvaluator(Evaluator):
    """
    Alerts when a metric crosses a threshold.

    Config:
        operator: "gt", "gte", "lt", "lte", "eq", "ne"
        value: Threshold value to compare against
        severity: Alert severity level (default: "medium")
    """

    def evaluate(
        self,
        current: ObservationResult,
        _history: list[ObservationResult]
    ) -> AlertDecision:
        """Alert if metric crosses threshold."""
        operator = self.config["operator"]
        threshold = self.config["value"]
        severity = self.config.get("severity", "medium")

        if current.value is None:
            return AlertDecision(
                should_alert=False,
                severity=severity,
                message="No value to evaluate",
                context=current.metadata
            )

        # Perform comparison
        comparisons = {
            "gt": lambda v, t: v > t,
            "gte": lambda v, t: v >= t,
            "lt": lambda v, t: v < t,
            "lte": lambda v, t: v <= t,
            "eq": lambda v, t: v == t,
            "ne": lambda v, t: v != t,
        }

        if operator not in comparisons:
            raise ValueError(f"Unknown operator: {operator}")

        threshold_crossed = comparisons[operator](current.value, threshold)

        if threshold_crossed:
            return AlertDecision(
                should_alert=True,
                severity=severity,
                message=f"Threshold crossed: {current.value} {operator} {threshold}",
                context={
                    **current.metadata,
                    "current_value": current.value,
                    "threshold": threshold,
                    "operator": operator
                }
            )
        return AlertDecision(
            should_alert=False,
            severity=severity,
            message=f"Threshold not crossed: {current.value} {operator} {threshold}",
            context=current.metadata
        )


# Export for dynamic importing
__all__ = ["ThresholdEvaluator"]
