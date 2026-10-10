import unittest

from ai_agent_fabric.model_routing import default_routing, validate_routing


class ModelRoutingTest(unittest.TestCase):
    def test_default_routing_is_valid(self) -> None:
        routing = default_routing()
        validate_routing(routing)
        self.assertEqual(routing["role_tiers"]["opponent"]["cost_policy"], "minimize")

    def test_default_must_be_allowed(self) -> None:
        routing = default_routing()
        routing["role_tiers"]["dev"] = {"capability_floor": "deep", "cost_policy": "balanced", "allowed": ["standard"]}
        with self.assertRaisesRegex(ValueError, "invalid tier policy"):
            validate_routing(routing)
