import json
import sys

import pytest

from r3e_coach.bridge import (BridgeError, BridgeProcess, find_config, load_config,
                              resolve_args, resolve_exe, run_bridge)
from r3e_coach.cli import main


def test_load_config(tmp_path):
    f = tmp_path / "cfg.json"
    f.write_text(json.dumps({"bridge_exe": "C:/tools/bridge.exe", "bridge_args": ["--port", "5566"]}),
                 encoding="utf-8")
    cfg = load_config(str(f))
    assert cfg["bridge_exe"] == "C:/tools/bridge.exe"


def test_load_config_invalid(tmp_path):
    f = tmp_path / "cfg.json"
    f.write_text("{kein json", encoding="utf-8")
    with pytest.raises(BridgeError):
        load_config(str(f))


def test_resolve_exe_missing_raises():
    with pytest.raises(BridgeError):
        resolve_exe(None, {})
    with pytest.raises(BridgeError):
        resolve_exe("/definitiv/nicht/vorhanden.exe", {})


def test_resolve_exe_from_config(tmp_path):
    exe = tmp_path / "bridge.sh"
    exe.write_text("#!/bin/sh\n", encoding="utf-8")
    assert resolve_exe(None, {"bridge_exe": str(exe)}) == str(exe)


def test_resolve_args_strips_separator():
    assert resolve_args(["--", "--port", "1"], {}) == ["--port", "1"]
    assert resolve_args(None, {"bridge_args": ["--x"]}) == ["--x"]
    assert resolve_args(["--y"], {"bridge_args": ["--x"]}) == ["--y"]


def test_bridge_process_start_stop():
    bp = BridgeProcess(sys.executable, ["-c", "import time; time.sleep(60)"])
    bp.start()
    assert bp.is_running()
    bp.stop()
    assert not bp.is_running()
    assert bp.proc.returncode is not None


def test_run_bridge_quick_exit(capsys):
    rc = run_bridge(sys.executable, ["-c", "print('ok')"], lang="de")
    assert rc == 0
    out = capsys.readouterr().out
    assert "Bridge gestartet" in out
    assert "Exit-Code 0" in out


def test_cli_bridge_with_standin(tmp_path, capsys):
    rc = main(["bridge", "--exe", sys.executable, "--args", "-c", "print(1)", "--lang", "de"])
    assert rc == 0
    assert "Bridge gestartet" in capsys.readouterr().out


def test_cli_bridge_missing_exe_returns_2(capsys):
    rc = main(["bridge", "--exe", "/nicht/vorhanden.exe"])
    assert rc == 2
    assert "nicht gefunden" in capsys.readouterr().err


def test_cli_bridge_uses_config(tmp_path, monkeypatch, capsys):
    cfg = tmp_path / ".r3e-coach.json"
    cfg.write_text(json.dumps({"bridge_exe": sys.executable, "bridge_args": ["-c", "print(1)"]}),
                   encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert find_config(None) == ".r3e-coach.json"
    rc = main(["bridge", "--lang", "de"])
    assert rc == 0
    assert "Bridge gestartet" in capsys.readouterr().out


def test_cli_analyze_still_works_without_subcommand(tmp_path, capsys):
    f = tmp_path / "log.csv"
    f.write_text("Time,Speed\n0,100\n1,120\n", encoding="utf-8")
    rc = main([str(f)])
    assert rc == 0
    assert "R3E Setup-Coach" in capsys.readouterr().out
