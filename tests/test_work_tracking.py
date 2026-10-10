import unittest

from ai_agent_fabric.work_tracking import default_config, validate_config


class WorkTrackingTest(unittest.TestCase):
    def test_default_configuration_is_valid(self) -> None:
        validate_config(default_config())

    def test_configuration_rejects_secret_like_values(self) -> None:
        config = default_config()
        config["content"] = {"api_key": "not-allowed"}
        with self.assertRaisesRegex(ValueError, "must not contain secrets"):
            validate_config(config)

    def test_project_owned_adapter_is_valid(self) -> None:
        config = default_config()
        config.update({"provider": "project-adapter", "adapter": {"id": "project-owned"}, "enabled": True})
        validate_config(config)
