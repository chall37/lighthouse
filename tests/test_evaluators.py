"""
Tests for evaluator implementations.
"""

from datetime import datetime

from lighthouse.core import ObservationResult
from lighthouse.evaluators import (
    PatternMatchEvaluator,
    SequentialGrowthEvaluator,
    StateChangeEvaluator,
    ThresholdEvaluator,
)


class TestPatternMatchEvaluator:
    """Tests for PatternMatchEvaluator."""

    def test_evaluate_match(self) -> None:
        """Test evaluation when pattern is matched."""
        evaluator = PatternMatchEvaluator({"severity": "high"})

        observation = ObservationResult(
            value=True,
            timestamp=datetime.now(),
            metadata={"matched_patterns": ["ERROR", "FATAL"]}
        )

        decision = evaluator.evaluate(observation, [])

        assert decision.should_alert is True
        assert decision.severity == "high"
        assert "ERROR" in decision.message

    def test_evaluate_no_match(self) -> None:
        """Test evaluation when pattern is not matched."""
        evaluator = PatternMatchEvaluator({"severity": "medium"})

        observation = ObservationResult(
            value=False,
            timestamp=datetime.now(),
            metadata={"matched_patterns": []}
        )

        decision = evaluator.evaluate(observation, [])

        assert decision.should_alert is False


class TestThresholdEvaluator:
    """Tests for ThresholdEvaluator."""

    def test_evaluate_greater_than(self) -> None:
        """Test evaluation with greater than operator."""
        evaluator = ThresholdEvaluator({
            "operator": "gt",
            "value": 10,
            "severity": "medium"
        })

        observation = ObservationResult(
            value=15,
            timestamp=datetime.now(),
            metadata={}
        )

        decision = evaluator.evaluate(observation, [])

        assert decision.should_alert is True
        assert "15 gt 10" in decision.message

    def test_evaluate_not_exceeded(self) -> None:
        """Test evaluation when threshold not exceeded."""
        evaluator = ThresholdEvaluator({
            "operator": "gt",
            "value": 10,
            "severity": "medium"
        })

        observation = ObservationResult(
            value=5,
            timestamp=datetime.now(),
            metadata={}
        )

        decision = evaluator.evaluate(observation, [])

        assert decision.should_alert is False

    def test_evaluate_less_than(self) -> None:
        """Test evaluation with less than operator."""
        evaluator = ThresholdEvaluator({
            "operator": "lt",
            "value": 10,
            "severity": "low"
        })

        observation = ObservationResult(
            value=5,
            timestamp=datetime.now(),
            metadata={}
        )

        decision = evaluator.evaluate(observation, [])

        assert decision.should_alert is True

    def test_evaluate_equals(self) -> None:
        """Test evaluation with equals operator."""
        evaluator = ThresholdEvaluator({
            "operator": "eq",
            "value": 42,
            "severity": "low"
        })

        observation = ObservationResult(
            value=42,
            timestamp=datetime.now(),
            metadata={}
        )

        decision = evaluator.evaluate(observation, [])

        assert decision.should_alert is True

    def test_evaluate_null_value(self) -> None:
        """Test evaluation with null value."""
        evaluator = ThresholdEvaluator({
            "operator": "gt",
            "value": 10
        })

        observation = ObservationResult(
            value=None,
            timestamp=datetime.now(),
            metadata={}
        )

        decision = evaluator.evaluate(observation, [])

        assert decision.should_alert is False


class TestSequentialGrowthEvaluator:
    """Tests for SequentialGrowthEvaluator."""

    def test_evaluate_first_observation_no_alert(self) -> None:
        """Test that first observation doesn't alert (establishing baseline)."""
        evaluator = SequentialGrowthEvaluator({"severity": "medium"})

        observation = ObservationResult(
            value=10,
            timestamp=datetime.now(),
            metadata={}
        )

        decision = evaluator.evaluate(observation, [])

        assert decision.should_alert is False
        assert "baseline" in decision.message.lower()

    def test_evaluate_value_zero_no_alert(self) -> None:
        """Test that value of 0 never alerts (problem resolved)."""
        evaluator = SequentialGrowthEvaluator({"severity": "medium"})

        observation = ObservationResult(
            value=0,
            timestamp=datetime.now(),
            metadata={}
        )

        decision = evaluator.evaluate(observation, [])

        assert decision.should_alert is False
        assert "no issues" in decision.message.lower()

    def test_evaluate_growth_alerts(self) -> None:
        """Test that growth triggers alert."""
        evaluator = SequentialGrowthEvaluator({"severity": "medium"})

        previous = ObservationResult(
            value=10,
            timestamp=datetime.now(),
            metadata={}
        )

        current = ObservationResult(
            value=15,
            timestamp=datetime.now(),
            metadata={}
        )

        decision = evaluator.evaluate(current, [previous])

        assert decision.should_alert is True
        assert decision.severity == "medium"
        assert "15 errors" in decision.message
        assert "was 10" in decision.message

    def test_evaluate_same_value_alerts(self) -> None:
        """Test that same value (stagnation) triggers alert."""
        evaluator = SequentialGrowthEvaluator({"severity": "medium"})

        previous = ObservationResult(
            value=10,
            timestamp=datetime.now(),
            metadata={}
        )

        current = ObservationResult(
            value=10,
            timestamp=datetime.now(),
            metadata={}
        )

        decision = evaluator.evaluate(current, [previous])

        assert decision.should_alert is True
        assert "10 errors" in decision.message
        assert "not improving" in decision.message

    def test_evaluate_decrease_no_alert(self) -> None:
        """Test that decrease doesn't alert (improving)."""
        evaluator = SequentialGrowthEvaluator({"severity": "medium"})

        previous = ObservationResult(
            value=15,
            timestamp=datetime.now(),
            metadata={}
        )

        current = ObservationResult(
            value=10,
            timestamp=datetime.now(),
            metadata={}
        )

        decision = evaluator.evaluate(current, [previous])

        assert decision.should_alert is False
        assert "improving" in decision.message.lower()


class TestStateChangeEvaluator:
    """Tests for StateChangeEvaluator."""

    def test_evaluate_first_observation_no_alert(self) -> None:
        """Test that first observation doesn't alert (establishing baseline)."""
        evaluator = StateChangeEvaluator({
            "alert_on": "both",
            "severity": "high"
        })

        observation = ObservationResult(
            value=True,
            timestamp=datetime.now(),
            metadata={}
        )

        decision = evaluator.evaluate(observation, [])

        assert decision.should_alert is False
        assert "baseline" in decision.message.lower()

    def test_evaluate_no_change_no_alert(self) -> None:
        """Test that no state change doesn't alert."""
        evaluator = StateChangeEvaluator({
            "alert_on": "both",
            "severity": "high"
        })

        previous = ObservationResult(
            value=True,
            timestamp=datetime.now(),
            metadata={}
        )

        current = ObservationResult(
            value=True,
            timestamp=datetime.now(),
            metadata={}
        )

        decision = evaluator.evaluate(current, [previous])

        assert decision.should_alert is False

    def test_evaluate_change_both_alerts(self) -> None:
        """Test that state change alerts when alert_on is 'both'."""
        evaluator = StateChangeEvaluator({
            "alert_on": "both",
            "severity": "high"
        })

        previous = ObservationResult(
            value=True,
            timestamp=datetime.now(),
            metadata={}
        )

        current = ObservationResult(
            value=False,
            timestamp=datetime.now(),
            metadata={}
        )

        decision = evaluator.evaluate(current, [previous])

        assert decision.should_alert is True
        assert "True → False" in decision.message

    def test_evaluate_true_to_false_alerts(self) -> None:
        """Test alert on true→false transition."""
        evaluator = StateChangeEvaluator({
            "alert_on": "true_to_false",
            "severity": "critical"
        })

        previous = ObservationResult(
            value=True,
            timestamp=datetime.now(),
            metadata={}
        )

        current = ObservationResult(
            value=False,
            timestamp=datetime.now(),
            metadata={}
        )

        decision = evaluator.evaluate(current, [previous])

        assert decision.should_alert is True
        assert decision.severity == "critical"

    def test_evaluate_false_to_true_no_alert_when_configured(self) -> None:
        """Test no alert on false→true when configured for true→false only."""
        evaluator = StateChangeEvaluator({
            "alert_on": "true_to_false",
            "severity": "high"
        })

        previous = ObservationResult(
            value=False,
            timestamp=datetime.now(),
            metadata={}
        )

        current = ObservationResult(
            value=True,
            timestamp=datetime.now(),
            metadata={}
        )

        decision = evaluator.evaluate(current, [previous])

        assert decision.should_alert is False

    def test_evaluate_false_to_true_alerts(self) -> None:
        """Test alert on false→true transition."""
        evaluator = StateChangeEvaluator({
            "alert_on": "false_to_true",
            "severity": "low"
        })

        previous = ObservationResult(
            value=False,
            timestamp=datetime.now(),
            metadata={}
        )

        current = ObservationResult(
            value=True,
            timestamp=datetime.now(),
            metadata={}
        )

        decision = evaluator.evaluate(current, [previous])

        assert decision.should_alert is True
