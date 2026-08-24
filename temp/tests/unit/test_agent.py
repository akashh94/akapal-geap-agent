import unittest

from google.genai import types

from app.agents.customer_support import customer_support
from app.agents.general_assistant import general_assistant
from app.agents.market_research import market_research
from app.agents.market_research_super_agent import market_research_super_agent
from app.agents.mortgage_agent import mortgage_agent
from app.agents.planning_agent import planning_agent
from app.agents.portfolio_analyst import portfolio_analyst
from app.agents.supervisor import root_agent
from app.agents.trade_assistant import trade_assistant


class TestGeapAgent(unittest.TestCase):
    def test_root_agent_initialization(self):
        """Verify the root agent is correctly initialized with expected sub-agents."""
        self.assertEqual(root_agent.name, "supervisor")

        sub_agent_names = [a.name for a in root_agent.sub_agents]
        expected_names = [
            "portfolio_analyst",
            "trade_assistant",
            "market_research",
            "market_research_super_agent",
            "customer_support",
            "mortgage_agent",
            "planning_agent",
            "general_assistant",
        ]
        for name in expected_names:
            self.assertIn(name, sub_agent_names)

    def test_root_agent_instruction(self):
        """Verify root agent has supervisor instructions."""
        self.assertIn("supervisor", root_agent.instruction.lower())
        self.assertIn("route", root_agent.instruction.lower())

    def test_trade_assistant_has_rebalance_widget_signal_tool(self):
        """Verify trade_assistant can signal the rebalance widget to the client."""
        tool_names = [t.name for t in trade_assistant.tools]
        self.assertIn("show_rebalance_widget", tool_names)

    def test_planning_agent_has_render_dashboard_tool(self):
        """Verify planning_agent can signal the A2UI retirement dashboard."""
        tool_names = [t.name for t in planning_agent.tools]
        self.assertIn("render_retirement_dashboard", tool_names)

    def test_planning_agent_uses_the_default_model_absent_an_override(self):
        """planning_agent should resolve to DEFAULT_MODEL absent any env override."""
        from app.config.models import DEFAULT_MODEL

        self.assertEqual(planning_agent.model.model, DEFAULT_MODEL)

    def test_supervisor_uses_minimal_thinking_and_a_small_token_cap(self):
        """Routing is a trivial classification -- should get the tightest cap of any agent."""
        config = root_agent.generate_content_config
        self.assertIsNotNone(config)
        self.assertEqual(
            config.thinking_config.thinking_level, types.ThinkingLevel.MINIMAL
        )
        self.assertEqual(config.max_output_tokens, 150)

    def test_all_specialist_agents_use_minimal_thinking(self):
        """Every hop should run at minimal thinking depth for this demo -- no agent left unconfigured."""
        specialists = [
            portfolio_analyst,
            trade_assistant,
            market_research,
            market_research_super_agent,
            customer_support,
            mortgage_agent,
            planning_agent,
            general_assistant,
        ]
        for agent in specialists:
            config = agent.generate_content_config
            self.assertIsNotNone(config, f"{agent.name} has no generate_content_config")
            self.assertEqual(
                config.thinking_config.thinking_level,
                types.ThinkingLevel.MINIMAL,
                f"{agent.name} is not set to minimal thinking",
            )
            self.assertEqual(
                config.max_output_tokens,
                1024,
                f"{agent.name} has an unexpected token cap",
            )


if __name__ == "__main__":
    unittest.main()
