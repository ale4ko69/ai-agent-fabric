import unittest

from ai_agent_fabric.bootstrap import bash_install_plan
from ai_agent_fabric.environment import Environment


class BootstrapTest(unittest.TestCase):
    def test_bash_plan_reports_ready_when_bash_exists(self) -> None:
        plan = bash_install_plan(Environment("windows", "windows", "test", True, "C:/Git/bin/bash.exe"))
        self.assertTrue(plan.available)
        self.assertIsNone(plan.command)
