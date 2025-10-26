"""
PatternMatch evaluator for Lighthouse.
"""

from lighthouse.core import AlertDecision, Evaluator, ObservationResult
from lighthouse.registry import register_evaluator


@register_evaluator("pattern_match")
class PatternMatchEvaluator(Evaluator):
    """
    Alerts when a pattern is matched.

    Simple evaluator for log pattern matching - alerts whenever
    the observer finds a match.

    Config:
        severity: Alert severity level (default: "medium")
    """

    def evaluate(
        self,
        current: ObservationResult,
        _history: list[ObservationResult]
    ) -> AlertDecision:
        """Alert if current observation indicates a match."""
        severity = self.config.get("severity", "medium")

        if current.value is True:
            # Pattern was matched
            matched_patterns = current.metadata.get("matched_patterns", [])
            return AlertDecision(
                should_alert=True,
                severity=severity,
                message=f"Pattern matched: {', '.join(matched_patterns)}",
                context=current.metadata
            )
        # No match or error
        return AlertDecision(
            should_alert=False,
            severity=severity,
            message="No pattern match",
            context=current.metadata
        )


# Export for dynamic importing
__all__ = ["PatternMatchEvaluator"]
