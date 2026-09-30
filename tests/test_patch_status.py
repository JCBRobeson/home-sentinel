# pyright: reportPrivateUsage=false
import pytest
from subprocess import CompletedProcess
from sentinel.core.collectors import patch_status
from sentinel.core.collectors.patch_status import (
    _parse_check_update,
    _parse_updateinfo,
    _build_nevra,
    _collect_package_updates,
    AdvisoryInfo,
    PackageUpdate,
)


def test_parse_check_update() -> None:

    test_str = "This is more than three parts, and you know it.\nyggdrasil-worker-package-manager.x86_64 0.2.3-7.el10_2.8 rhel-10-for-x86_64-appstream-rpms\nsudo.x86_64 1.9.17-10.p2.el10_2.6 rhel-10-for-x86_64-baseos-rpms\nless"
    test_result = _parse_check_update(test_str)

    assert test_result == [
        PackageUpdate(
            name_arch="yggdrasil-worker-package-manager.x86_64",
            version="0.2.3-7.el10_2.8",
            repo="rhel-10-for-x86_64-appstream-rpms",
        ),
        PackageUpdate(
            name_arch="sudo.x86_64",
            version="1.9.17-10.p2.el10_2.6",
            repo="rhel-10-for-x86_64-baseos-rpms",
        ),
    ]


def test_parse_updateinfo() -> None:

    testr_str = "Not root, Subscription Management repositories not updated\nless\nRHBA-2026:69944 bugfix bind-libs-32:9.18.33-15.el10_2.11.x86_64\nRHBA-2026:67590 bugfix cairo-1.18.2-2.el10_2.1.x86_64"
    test_result = _parse_updateinfo(testr_str)

    assert test_result == {
        "bind-libs-32:9.18.33-15.el10_2.11.x86_64": [
            AdvisoryInfo(advisory_id="RHBA-2026:69944", severity_or_type="bugfix")
        ],
        "cairo-1.18.2-2.el10_2.1.x86_64": [
            AdvisoryInfo(advisory_id="RHBA-2026:67590", severity_or_type="bugfix")
        ],
    }


def test_build_nevra() -> None:

    test_result_generic = _build_nevra("kernel.x86_64", "6.12.0-211.56.1.el10_2")
    test_result_epoch = _build_nevra("microcode_ctl.noarch", "4:20260812-0.el10_2")

    assert test_result_generic == "kernel-6.12.0-211.56.1.el10_2.x86_64"
    assert test_result_epoch == "microcode_ctl-4:20260812-0.el10_2.noarch"


def test_parse_updateinfo_same_nevra_multiple_advisories() -> None:

    testr_str = "RHSA-2026:67471 Important/Sec. kernel-6.12.0-211.55.1.el10_2.x86_64\nRHBA-2026:99999 bugfix kernel-6.12.0-211.55.1.el10_2.x86_64"
    test_result = _parse_updateinfo(testr_str)

    assert test_result == {
        "kernel-6.12.0-211.55.1.el10_2.x86_64": [
            AdvisoryInfo(advisory_id="RHSA-2026:67471", severity_or_type="Important/Sec."),
            AdvisoryInfo(advisory_id="RHBA-2026:99999", severity_or_type="bugfix"),
        ],
    }


def test_collect_package_updates_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:

    def fake_run_command(args: list[str]) -> CompletedProcess[str] | None:
        if args == ["dnf", "check-update"]:
            return CompletedProcess(
                args=args,
                returncode=100,
                stdout=(
                    "yggdrasil-worker-package-manager.x86_64 0.2.3-7.el10_2.8 rhel-10-for-x86_64-appstream-rpms\n"
                    "sudo.x86_64 1.9.17-10.p2.el10_2.6 rhel-10-for-x86_64-baseos-rpms"
                ),
                stderr="",
            )
        if args == ["dnf", "updateinfo", "list"]:
            return CompletedProcess(
                args=args,
                returncode=0,
                stdout="RHSA-2026:68692 Important/Sec. sudo-1.9.17-10.p2.el10_2.6.x86_64",
                stderr="",
            )
        raise ValueError(f"unexpected args: {args}")

    monkeypatch.setattr(patch_status, "run_command", fake_run_command)

    results = patch_status._collect_package_updates()
    assert len(results) == 2

    by_target = {r.target: r for r in results}

    yggdrasil = by_target["yggdrasil-worker-package-manager.x86_64"]
    assert yggdrasil.metrics == {"update_available": True, "is_security_update": False}
    assert yggdrasil.details["version"] == "0.2.3-7.el10_2.8"
    assert yggdrasil.details["advisories"] == []

    sudo = by_target["sudo.x86_64"]
    assert sudo.metrics == {"update_available": True, "is_security_update": True}
    assert sudo.details["advisories"] == [
        {"advisory_id": "RHSA-2026:68692", "severity_or_type": "Important/Sec."}
    ]


def test_collect_package_updates_check_update_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    def fake_run_command(args: list[str]) -> CompletedProcess[str] | None:
        return None

    monkeypatch.setattr(patch_status, "run_command", fake_run_command)

    results = _collect_package_updates()
    assert results == []


def test_collect_package_updates_check_update_bad_returncode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    def fake_run_command(args: list[str]) -> CompletedProcess[str] | None:
        return CompletedProcess(args=args, returncode=1, stdout="", stderr="boom")

    monkeypatch.setattr(patch_status, "run_command", fake_run_command)

    results = _collect_package_updates()
    assert results == []


def test_collect_package_updates_updateinfo_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    def fake_run_command(args: list[str]) -> CompletedProcess[str] | None:
        if args == ["dnf", "check-update"]:
            return CompletedProcess(
                args=args,
                returncode=100,
                stdout="sudo.x86_64 1.9.17-10.p2.el10_2.6 rhel-10-for-x86_64-baseos-rpms",
                stderr="",
            )
        return None

    monkeypatch.setattr(patch_status, "run_command", fake_run_command)

    results = _collect_package_updates()
    assert len(results) == 1
    assert results[0].metrics == {"update_available": True, "is_security_update": False}
    assert results[0].details["advisories"] == []
