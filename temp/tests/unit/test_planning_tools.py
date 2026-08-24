import unittest

from app.a2ui.planning_envelope import validate_planning_envelope
from app.tools.planning.retirement_tools import (
    get_glide_path_allocation,
    get_retirement_summary,
    render_retirement_dashboard,
    run_monte_carlo_projection,
)


class TestRetirementTools(unittest.TestCase):
    def test_get_retirement_summary_shape(self):
        summary = get_retirement_summary()
        for key in (
            "target_age",
            "target_year",
            "current_savings",
            "projected_value_at_target_age",
        ):
            self.assertIn(key, summary)
        self.assertIsInstance(summary["target_age"], int)
        self.assertGreater(summary["current_savings"], 0)

    def test_run_monte_carlo_projection_uses_requested_simulation_count(self):
        result = run_monte_carlo_projection(simulations=500)
        self.assertEqual(result["simulations"], 500)
        self.assertTrue(0 <= result["success_probability_pct"] <= 100)

    def test_get_glide_path_allocation_weights_sum_to_100(self):
        allocation = get_glide_path_allocation()
        self.assertEqual(sum(row["weight_pct"] for row in allocation), 100)

    def test_get_glide_path_allocation_returns_copies(self):
        """Callers mutating the result must not corrupt module state."""
        allocation = get_glide_path_allocation()
        allocation[0]["label"] = "mutated"
        self.assertNotEqual(get_glide_path_allocation()[0]["label"], "mutated")


class TestRenderRetirementDashboard(unittest.TestCase):
    def test_returns_valid_a2ui_chart_envelope(self):
        result = render_retirement_dashboard()
        self.assertIn("a2ui", result)
        envelope = result["a2ui"]
        self.assertIsNotNone(envelope)
        validate_planning_envelope(envelope)  # should not raise

        self.assertEqual(envelope["version"], "1.0")
        self.assertEqual(envelope["root"]["type"], "surface")
        charts = envelope["root"]["children"]["charts"]
        self.assertEqual(charts["type"], "chart_tabs")
        self.assertEqual(
            set(charts["children"]), {"glide_path", "monte_carlo", "allocation"}
        )

    def test_dashboard_figures_match_the_underlying_tools(self):
        summary = get_retirement_summary()
        projection = run_monte_carlo_projection()
        envelope = render_retirement_dashboard()["a2ui"]
        planning_data = envelope["updateDataModel"]["planning"]

        self.assertEqual(planning_data["targetAge"], summary["target_age"])
        self.assertIn(
            f"{summary['current_savings']:,.2f}", planning_data["currentSavings"]
        )
        self.assertIn(
            str(projection["success_probability_pct"]), planning_data["successRate"]
        )

    def test_chart_props_are_numeric_structured_not_prose(self):
        envelope = render_retirement_dashboard()["a2ui"]
        charts = envelope["root"]["children"]["charts"]["children"]

        self.assertIsInstance(charts["glide_path"]["props"]["series"], list)
        monte_carlo_series = charts["monte_carlo"]["props"]["series"]
        self.assertIsInstance(monte_carlo_series, dict)
        self.assertEqual(set(monte_carlo_series), {"p10", "p50", "p90"})
        for band in monte_carlo_series.values():
            self.assertIsInstance(band, list)
        self.assertIsInstance(charts["allocation"]["props"]["segments"], list)
        for segment in charts["allocation"]["props"]["segments"]:
            self.assertNotIsInstance(segment.get("weight_pct"), str)


if __name__ == "__main__":
    unittest.main()
