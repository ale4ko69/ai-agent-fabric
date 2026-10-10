import unittest

from ai_agent_fabric.agent_profiles import default_capabilities
from ai_agent_fabric.capabilities import validate_capabilities
from ai_agent_fabric.distribution import (
    adapter_manifest,
    validate_adapter_manifest,
    validate_installation_manifest,
    validate_project_binding,
)
from ai_agent_fabric.gates import default_gates, validate_gates
from ai_agent_fabric.installer import default_project_profile, validate_project_profile
from ai_agent_fabric.model_routing import default_routing, validate_routing
from ai_agent_fabric.work_tracking import default_config, validate_config


class ContractValidationTest(unittest.TestCase):
    def test_top_level_contracts_reject_non_object_json(self) -> None:
        validators = (
            validate_capabilities,
            validate_gates,
            validate_project_profile,
            validate_routing,
            validate_config,
            validate_adapter_manifest,
            validate_installation_manifest,
            validate_project_binding,
        )
        for validator in validators:
            with self.subTest(validator=validator.__name__):
                with self.assertRaises(ValueError):
                    validator([])

    def test_runtime_validators_reject_undeclared_fields(self) -> None:
        cases = (
            (validate_capabilities, default_capabilities()),
            (validate_gates, default_gates()),
            (validate_project_profile, default_project_profile("Example")),
            (validate_routing, default_routing()),
            (validate_config, default_config()),
            (validate_adapter_manifest, adapter_manifest("codex")),
        )
        for validator, contract in cases:
            with self.subTest(validator=validator.__name__):
                contract["undeclared"] = True
                with self.assertRaises(ValueError):
                    validator(contract)
