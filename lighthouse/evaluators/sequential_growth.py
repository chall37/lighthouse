"""
SequentialGrowth evaluator for Lighthouse.
"""

from lighthouse.core import AlertDecision, Evaluator, ObservationResult
from lighthouse.registry import register_evaluator


@register_evaluator("sequential_growth")
class SequentialGrowthEvaluator(Evaluator):
    """
    Alerts when a metric fails to decrease over time.

    This is useful for monitoring error counts - if the count stays the same
    or increases between runs, it means the problem is persisting or worsening.

    Config:
        severity: Alert severity level (default: "medium")

    Logic:
        Alert if: current >= previous AND current > 0
        Don't alert if: current < previous OR current == 0
    """

    def evaluate(
        self,
        current: ObservationResult,
        history: list[ObservationResult]
    ) -> AlertDecision:
        """Alert if metric shows sequential growth or stagnation."""
        severity = self.config.get("severity", "medium")

        if current.value is None:
            return AlertDecision(
                should_alert=False,
                severity=severity,
                message="No current value",
                context=current.metadata
            )

        # If current value is 0, never alert (problem resolved)
        if current.value == 0:
            return AlertDecision(
                should_alert=False,
                severity=severity,
                message="Value is 0 (no issues)",
                context=current.metadata
            )

        # If no history, don't alert (establishing baseline)
        if not history:
            return AlertDecision(
                should_alert=False,
                severity=severity,
                message=f"Establishing baseline: {current.value}",
                context={
                    **current.metadata,
                    "current_value": current.value,
                    "previous_value": None
                }
            )

        # Get most recent previous value
        previous = history[-1]
        if previous.value is None:
            return AlertDecision(
                should_alert=False,
                severity=severity,
                message="No previous value to compare",
                context=current.metadata
            )

        # Alert if current >= previous AND current > 0
        if current.value >= previous.value:
            return AlertDecision(
                should_alert=True,
                severity=severity,
                message=(
                    f"Persistent issue: {current.value} errors "
                    f"(was {previous.value}, not improving)"
                ),
                context={
                    **current.metadata,
                    "current_value": current.value,
                    "previous_value": previous.value,
                    "change": current.value - previous.value
                }
            )
        # Value decreased - improving!
        return AlertDecision(
            should_alert=False,
            severity=severity,
            message=f"Improving: {current.value} (was {previous.value})",
            context={
                **current.metadata,
                "current_value": current.value,
                "previous_value": previous.value,
                "change": current.value - previous.value
            }
        )


# Export for dynamic importing
__all__ = ["SequentialGrowthEvaluator"]
