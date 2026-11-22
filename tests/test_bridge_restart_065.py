"""Tests 0.6.5: automatischer Bridge-Neustart (GUI-Quelle, ohne PySide6 pruefbar)."""
import ast
import pathlib
import unittest

SRC = pathlib.Path(__file__).resolve().parents[1] / "r3e_coach" / "gui.py"


class BridgeRestartTests(unittest.TestCase):
    def setUp(self):
        text = SRC.read_text(encoding="utf-8")
        self.text = text
        tree = ast.parse(text)
        cls = next(n for n in ast.walk(tree)
                   if isinstance(n, ast.ClassDef) and n.name == "CoachGui")
        self.methods = {n.name: n for n in cls.body if isinstance(n, ast.FunctionDef)}

    def _src(self, name):
        return ast.get_source_segment(self.text, self.methods[name])

    def test_poll_bridge_restarts(self):
        src = self._src("_poll_bridge")
        self.assertIn("bridge_fast_fails", src)
        self.assertIn("restart_check", src)
        self.assertIn("bridge.start()", src)

    def test_stop_disables_autorestart(self):
        self.assertIn("_bridge_user_stopped", self._src("stop_bridge"))

    def test_persist_auto_restart_exists(self):
        self.assertIn("bridge_auto_restart", self._src("_persist_auto_restart"))

    def test_labels_and_checkbox_present(self):
        for key in ("auto_restart", "restarted", "restart_off", "QCheckBox"):
            self.assertIn(key, self.text)


if __name__ == "__main__":
    unittest.main()
