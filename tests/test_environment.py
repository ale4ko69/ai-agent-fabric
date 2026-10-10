import unittest

from ai_agent_fabric.environment import Environment, command_is_allowed


class EnvironmentTest(unittest.TestCase):
    def test_command_family_is_environment_specific(self) -> None:
        windows = Environment("windows", "windows", "test", True, None)
        windows_with_bash = Environment("windows", "windows", "test", True, "C:/Git/bin/bash.exe")
        linux = Environment("linux", "linux", "test", True, "/usr/bin/bash")
        self.assertTrue(command_is_allowed("python", windows))
        self.assertFalse(command_is_allowed("bash", windows))
        self.assertTrue(command_is_allowed("bash", windows_with_bash))
        self.assertTrue(command_is_allowed("bash", linux))
        self.assertFalse(command_is_allowed("powershell", linux))
