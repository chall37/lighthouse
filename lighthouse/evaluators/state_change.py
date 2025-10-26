"""
StateChange evaluator for Lighthouse.
"""

from lighthouse.core import AlertDecision, Evaluator, ObservationResult
from lighthouse.registry import register_evaluator


@register_evaluator("state_change")
class StateChangeEvaluator(Evaluator):
    """
    Alerts when a boolean state changes.

    Useful for service monitoring - alert when service goes down,
    optionally alert when it comes back up.

    Config:
        alert_on: "both", "true_to_false", "false_to_true"
        severity: Alert severity level (default: "medium")
    """

    def evaluate(
        self,
        current: ObservationResult,
        history: list[ObservationResult]
    ) -> AlertDecision:
        """Alert on state changes."""
        alert_on = self.config.get("alert_on", "both")
        severity = self.config.get("severity", "medium")

        if current.value is None:
            return AlertDecision(
                should_alert=False,
                severity=severity,
                message="No current state",
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
                    "current_state": current.value,
                    "previous_state": None
                }
            )

        # Get most recent previous value
        previous = history[-1]
        if previous.value is None:
            return AlertDecision(
                should_alert=False,
                severity=severity,
                message="No previous state to compare",
                context=current.metadata
            )

        # Check for state change
        changed = current.value != previous.value

        if not changed:
            return AlertDecision(
                should_alert=False,
                severity=severity,
                message=f"No state change (still {current.value})",
                context=current.metadata
            )

        # Determine if we should alert based on alert_on config
        transitioned_to_failure = (
            alert_on == "true_to_false" and previous.value is True and current.value is False
        )
        transitioned_to_success = (
            alert_on == "false_to_true" and previous.value is False and current.value is True
        )
        should_alert = alert_on == "both" or transitioned_to_failure or transitioned_to_success

        if should_alert:
            return AlertDecision(
                should_alert=True,
                severity=severity,
                message=f"State changed: {previous.value} → {current.value}",
                context={
                    **current.metadata,
                    "current_state": current.value,
                    "previous_state": previous.value
                }
            )
        return AlertDecision(
            should_alert=False,
            severity=severity,
            message=f"State changed but not alerting: {previous.value} → {current.value}",
            context=current.metadata
        )


# Export for dynamic importing
__all__ = ["StateChangeEvaluator"]
