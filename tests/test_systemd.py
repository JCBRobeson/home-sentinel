import pytest
from subprocess import CompletedProcess
from sentinel.core.collectors import failed_units


def test_failed_units_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:

    def fake_subprocess_run(args: list[str], capture_output: bool, text: bool):
        return CompletedProcess(
            args=[
                "systemctl",
                "list-units",
                "-t",
                "service",
                "--state=failed",
                "--no-legend",
                "--plain",
            ],
            returncode=0,
            stdout=(
                "sentinel-test-fail2.service loaded failed failed [systemd-run] /bin/false\n"
                "sentinel-test-fail.service  loaded failed failed [systemd-run] /bin/false\n"
            ),
            stderr="",
        )

    monkeypatch.setattr(failed_units.subprocess, "run", fake_subprocess_run)

    results = failed_units.collect()
    assert len(results) == 2

    result1, result2 = results

    assert result1.target == "sentinel-test-fail2.service"
    assert result1.metrics == {"failed": True}
    assert result1.details == {
        "service": "sentinel-test-fail2.service",
        "load": "loaded",
        "sub": "failed",
        "description": "[systemd-run] /bin/false",
    }

    assert result2.target == "sentinel-test-fail.service"
    assert result2.metrics == {"failed": True}
    assert result2.details == {
        "service": "sentinel-test-fail.service",
        "load": "loaded",
        "sub": "failed",
        "description": "[systemd-run] /bin/false",
    }


def test_failed_units_command_not_found(monkeypatch: pytest.MonkeyPatch) -> None:

    def fake_subprocess_run(args: list[str], capture_output: bool, text: bool):
        raise FileNotFoundError

    monkeypatch.setattr(failed_units.subprocess, "run", fake_subprocess_run)

    results = failed_units.collect()
    assert results == []


def test_failed_units_nonsuccess_code(monkeypatch: pytest.MonkeyPatch) -> None:

    def fake_subprocess_run(args: list[str], capture_output: bool, text: bool):
        return CompletedProcess(
            args=["dummy", "command"],
            returncode=1,
            stdout="",
            stderr="dummy command not found",
        )

    monkeypatch.setattr(failed_units.subprocess, "run", fake_subprocess_run)

    results = failed_units.collect()
    assert results == []


def test_failed_units_malformed_string(monkeypatch: pytest.MonkeyPatch) -> None:

    def fake_subprocess_run(args: list[str], capture_output: bool, text: bool):
        return CompletedProcess(
            args=[
                "systemctl",
                "list-units",
                "-t",
                "service",
                "--state=failed",
                "--no-legend",
                "--plain",
            ],
            returncode=0,
            stdout=(
                "sentinel-test-fail2.service loaded failed failed [systemd-run] /bin/false\n"
                "sentinel-test-fail.service  loaded failed"
            ),
            stderr="",
        )

    monkeypatch.setattr(failed_units.subprocess, "run", fake_subprocess_run)

    results = failed_units.collect()
    assert len(results) == 1
    assert results[0].target == "sentinel-test-fail2.service"
