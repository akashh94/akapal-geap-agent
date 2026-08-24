import copy
import unittest

from app.a2ui.planning_envelope import (
    DEFAULT_PLANNING_A2UI,
    PlanningA2uiValidationError,
    build_planning_envelope,
    default_planning_envelope,
    validate_planning_envelope,
)


def _valid_kwargs():
    return {
        "glide_path_series": [{"age": 45, "equity_pct": 65, "bond_pct": 35}],
        "monte_carlo_series": {"p10": [], "p50": [], "p90": []},
        "monte_carlo_target": 1_000_000,
        "allocation_segments": [{"label": "U.S. Equities", "weight_pct": 45}],
        "success_rate": "84%",
        "target_age": 65,
        "current_savings": "$84,230.15",
        "target_portfolio": "$1,245,000",
    }


class TestDefaultPlanningEnvelope(unittest.TestCase):
    def test_default_envelope_is_valid(self):
        validate_planning_envelope(default_planning_envelope())  # should not raise

    def test_default_envelope_is_independent_copy(self):
        envelope = default_planning_envelope()
        envelope["root"]["children"]["charts"]["type"] = "mutated"
        self.assertEqual(
            DEFAULT_PLANNING_A2UI["root"]["children"]["charts"]["type"], "chart_tabs"
        )

    def test_default_envelope_matches_canonical_shape(self):
        envelope = default_planning_envelope()
        self.assertEqual(envelope["version"], "1.0")
        self.assertEqual(envelope["root"]["type"], "surface")
        charts = envelope["root"]["children"]["charts"]
        self.assertEqual(charts["type"], "chart_tabs")
        self.assertEqual(
            set(charts["children"]), {"glide_path", "monte_carlo", "allocation"}
        )
        planning = envelope["updateDataModel"]["planning"]
        self.assertEqual(
            set(planning),
            {"successRate", "targetAge", "currentSavings", "targetPortfolio"},
        )


class TestBuildPlanningEnvelope(unittest.TestCase):
    def test_build_produces_valid_envelope(self):
        envelope = build_planning_envelope(**_valid_kwargs())
        validate_planning_envelope(envelope)  # should not raise
        self.assertEqual(
            envelope["root"]["children"]["charts"]["children"]["glide_path"]["props"][
                "series"
            ],
            _valid_kwargs()["glide_path_series"],
        )
        self.assertEqual(envelope["updateDataModel"]["planning"]["targetAge"], 65)


class TestValidatePlanningEnvelope(unittest.TestCase):
    def test_none_payload_raises(self):
        with self.assertRaises(PlanningA2uiValidationError):
            validate_planning_envelope(None)

    def test_wrong_version_raises(self):
        envelope = default_planning_envelope()
        envelope["version"] = "0.9"
        with self.assertRaises(PlanningA2uiValidationError):
            validate_planning_envelope(envelope)

    def test_wrong_root_type_raises(self):
        envelope = default_planning_envelope()
        envelope["root"]["type"] = "not_a_surface"
        with self.assertRaises(PlanningA2uiValidationError):
            validate_planning_envelope(envelope)

    def test_missing_charts_raises(self):
        envelope = default_planning_envelope()
        del envelope["root"]["children"]["charts"]
        with self.assertRaises(PlanningA2uiValidationError):
            validate_planning_envelope(envelope)

    def test_wrong_charts_type_raises(self):
        envelope = default_planning_envelope()
        envelope["root"]["children"]["charts"]["type"] = "not_chart_tabs"
        with self.assertRaises(PlanningA2uiValidationError):
            validate_planning_envelope(envelope)

    def test_missing_required_chart_child_raises(self):
        for missing in ("glide_path", "monte_carlo", "allocation"):
            with self.subTest(missing=missing):
                envelope = default_planning_envelope()
                del envelope["root"]["children"]["charts"]["children"][missing]
                with self.assertRaises(PlanningA2uiValidationError):
                    validate_planning_envelope(envelope)

    def test_missing_planning_data_model_raises(self):
        envelope = default_planning_envelope()
        del envelope["updateDataModel"]["planning"]
        with self.assertRaises(PlanningA2uiValidationError):
            validate_planning_envelope(envelope)

    def test_missing_planning_key_raises(self):
        for key in ("successRate", "targetAge", "currentSavings", "targetPortfolio"):
            with self.subTest(key=key):
                envelope = default_planning_envelope()
                del envelope["updateDataModel"]["planning"][key]
                with self.assertRaises(PlanningA2uiValidationError):
                    validate_planning_envelope(envelope)

    def test_valid_default_envelope_deep_copy_passes(self):
        validate_planning_envelope(copy.deepcopy(DEFAULT_PLANNING_A2UI))


if __name__ == "__main__":
    unittest.main()
