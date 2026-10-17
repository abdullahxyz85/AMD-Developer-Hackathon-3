"""Regression checks for the Windows frontend launcher; no live model calls."""
import unittest
from unittest.mock import Mock, patch, mock_open
from pathlib import Path
import main as launcher


class LauncherTests(unittest.TestCase):
    def test_windows_uses_resolved_npm_cmd_for_install_and_server(self):
        npm = r"C:\Program Files\nodejs\npm.cmd"
        with patch.object(launcher.os, "name", "nt"), \
             patch.object(launcher.shutil, "which", side_effect=lambda name: npm if name == "npm.cmd" else "node.exe"), \
             patch.object(Path, "exists", return_value=False), \
             patch("builtins.open", mock_open()), \
             patch.object(launcher.subprocess, "run") as install, \
             patch.object(launcher.subprocess, "Popen", return_value=Mock()) as spawn:
            launcher.start_frontend()
        self.assertEqual(install.call_args.args[0], [npm, "install"])
        self.assertEqual(spawn.call_args.args[0][0], npm)
        self.assertIn("--strictPort", spawn.call_args.args[0])
        self.assertEqual(spawn.call_args.kwargs["env"]["VITE_DEMO_FALLBACK"], "false")
        self.assertEqual(spawn.call_args.kwargs["env"]["VITE_API_URL"], "http://localhost:8002")

    def test_missing_node_skips_frontend(self):
        with patch.object(launcher.shutil, "which", return_value=None):
            self.assertIsNone(launcher.start_frontend())


if __name__ == "__main__":
    unittest.main()
