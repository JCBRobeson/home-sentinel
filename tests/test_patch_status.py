# pyright: reportPrivateUsage=false
import pytest
from datetime import datetime
from subprocess import CompletedProcess
from sentinel.core.collectors import patch_status
from sentinel.core.collectors.patch_status import (
    _parse_check_update,
    _parse_updateinfo,
    _parse_staleness,
    _build_nevra,
    _collect_package_updates,
    _collect_reboot_status,
    _collect_patch_staleness,
    AdvisoryInfo,
    PackageUpdate,
    StalenessInfo,
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


def test_parse_staleness() -> None:
    test_str = """Not root, Subscription Management repositories not updated
ID     | Command line                                                                                                                                 | Date and time    | Action(s)      | Altered
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    10 | update                                                                                                                                       | 2026-09-30 09:05 | C, E, I, U     |   92 EE
     9 | install git -y                                                                                                                               | 2026-09-13 05:53 | Install        |    7   
     8 | update                                                                                                                                       | 2026-09-11 07:15 | I, U           |   16   
     7 | install vim-enhanced                                                                                                                         | 2026-09-10 16:09 | Upgrade        |    4   
     6 | upgrade                                                                                                                                      | 2026-09-06 15:44 | I, U           |   16   
     5 | install nfs-utils                                                                                                                            | 2026-09-06 15:43 | Install        |    7 EE
     4 | update                                                                                                                                       | 2026-09-02 13:04 | Upgrade        |    1   
     3 | install cloud-utils-growpart -y                                                                                                              | 2026-09-02 13:03 | Install        |    1  <
     2 | install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin                                                     | 2026-09-01 08:03 | Install        |    6 ><
     1 |    """

    test_result = _parse_staleness(test_str)
    assert len(test_result) == 9
    assert test_result == [
        StalenessInfo(
            last_update=datetime.strptime("2026-09-30 09:05", "%Y-%m-%d %H:%M"),
            update_action="C, E, I, U",
        ),
        StalenessInfo(
            last_update=datetime.strptime("2026-09-13 05:53", "%Y-%m-%d %H:%M"),
            update_action="Install",
        ),
        StalenessInfo(
            last_update=datetime.strptime("2026-09-11 07:15", "%Y-%m-%d %H:%M"),
            update_action="I, U",
        ),
        StalenessInfo(
            last_update=datetime.strptime("2026-09-10 16:09", "%Y-%m-%d %H:%M"),
            update_action="Upgrade",
        ),
        StalenessInfo(
            last_update=datetime.strptime("2026-09-06 15:44", "%Y-%m-%d %H:%M"),
            update_action="I, U",
        ),
        StalenessInfo(
            last_update=datetime.strptime("2026-09-06 15:43", "%Y-%m-%d %H:%M"),
            update_action="Install",
        ),
        StalenessInfo(
            last_update=datetime.strptime("2026-09-02 13:04", "%Y-%m-%d %H:%M"),
            update_action="Upgrade",
        ),
        StalenessInfo(
            last_update=datetime.strptime("2026-09-02 13:03", "%Y-%m-%d %H:%M"),
            update_action="Install",
        ),
        StalenessInfo(
            last_update=datetime.strptime("2026-09-01 08:03", "%Y-%m-%d %H:%M"),
            update_action="Install",
        ),
    ]


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


def test_collect_reboot_status_reboot_not_required(monkeypatch: pytest.MonkeyPatch) -> None:

    def fake_run_command(args: list[str]) -> CompletedProcess[str] | None:
        return CompletedProcess(
            args=args,
            returncode=0,
            stdout="Not root, Subscription Management repositories not updated\nNo core libraries or services have been updated since boot-up.\nReboot should not be necessary.",
            stderr="",
        )

    monkeypatch.setattr(patch_status, "run_command", fake_run_command)

    results = _collect_reboot_status()
    assert len(results) == 1
    assert (
        results[0].details["description"]
        == "No core libraries or services have been updated since boot-up.\nReboot should not be necessary."
    )
    assert results[0].details["packages"] == []
    assert results[0].metrics["reboot_required"] == False


def test_collect_reboot_status_reboot_required(monkeypatch: pytest.MonkeyPatch) -> None:

    def fake_run_command(args: list[str]) -> CompletedProcess[str] | None:
        return CompletedProcess(
            args=args,
            returncode=1,
            stdout="Core libraries or services have been updated since boot-up:\n * kernel\n * systemd\n\nReboot is required to fully utilize these updates.\n",
            stderr="",
        )

    monkeypatch.setattr(patch_status, "run_command", fake_run_command)

    results = _collect_reboot_status()
    assert len(results) == 1
    assert (
        results[0].details["description"]
        == "Core libraries or services have been updated since boot-up:\n * kernel\n * systemd\nReboot is required to fully utilize these updates."
    )
    assert results[0].details["packages"] == ["kernel", "systemd"]
    assert results[0].metrics["reboot_required"] == True


def test_collect_patch_staleness_does_not_qualify(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_command(args: list[str]) -> CompletedProcess[str] | None:
        return CompletedProcess(
            args=args,
            returncode=0,
            stdout="""Not root, Subscription Management repositories not updated
ID     | Command line                                                                                                                                 | Date and time    | Action(s)      | Altered
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    10 | update                                                                                                                                       | 2026-09-30 09:05 | C, E, I    |   92 EE
     9 | install git -y                                                                                                                               | 2026-09-13 05:53 | Install        |    7     
     5 | install nfs-utils                                                                                                                            | 2026-09-06 15:43 | Install        |    7 EE
     1 |    """,
            stderr="",
        )

    monkeypatch.setattr(patch_status, "run_command", fake_run_command)

    results = _collect_patch_staleness()
    assert len(results) == 1
    assert results[0].metrics["patch_history_found"] == True
    assert results[0].details["last_update"] is None
    assert results[0].details["last_update_action"] is None
    assert results[0].details["days_since_last_patch"] is None


def test_collect_patch_staleness_empty_history(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_command(args: list[str]) -> CompletedProcess[str] | None:
        return CompletedProcess(
            args=args,
            returncode=0,
            stdout="""Not root, Subscription Management repositories not updated
ID     | Command line                                                                                                                                 | Date and time    | Action(s)      | Altered
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------""",
            stderr="",
        )

    monkeypatch.setattr(patch_status, "run_command", fake_run_command)

    results = _collect_patch_staleness()
    assert len(results) == 1
    assert results[0].metrics["patch_history_found"] == False
    assert results[0].details["last_update"] is None
    assert results[0].details["last_update_action"] is None
    assert results[0].details["days_since_last_patch"] is None


def test_collect_patch_staleness_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_command(args: list[str]) -> CompletedProcess[str] | None:
        return CompletedProcess(
            args=args,
            returncode=0,
            stdout="""Not root, Subscription Management repositories not updated
ID     | Command line                                                                                                                                 | Date and time    | Action(s)      | Altered
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    10 | update                                                                                                                                       | 2026-09-30 09:05 | C, E, I, U     |   92 EE
     9 | install git -y                                                                                                                               | 2026-09-13 05:53 | Install        |    7   
     8 | update                                                                                                                                       | 2026-09-11 07:15 | I, U           |   16   
     7 | install vim-enhanced                                                                                                                         | 2026-09-10 16:09 | Upgrade        |    4   
     6 | upgrade                                                                                                                                      | 2026-09-06 15:44 | I, U           |   16   
     5 | install nfs-utils                                                                                                                            | 2026-09-06 15:43 | Install        |    7 EE
     4 | update                                                                                                                                       | 2026-09-02 13:04 | Upgrade        |    1   
     3 | install cloud-utils-growpart -y                                                                                                              | 2026-09-02 13:03 | Install        |    1  <
     2 | install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin                                                     | 2026-09-01 08:03 | Install        |    6 ><
     1 |    """,
            stderr="",
        )

    monkeypatch.setattr(patch_status, "run_command", fake_run_command)

    results = _collect_patch_staleness()
    assert len(results) == 1
    assert results[0].metrics["patch_history_found"] == True
    assert (
        results[0].details["last_update"]
        == datetime.strptime("2026-09-30 09:05", "%Y-%m-%d %H:%M").isoformat()
    )
    assert results[0].details["last_update_action"] == "C, E, I, U"
