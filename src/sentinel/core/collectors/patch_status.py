import logging
from datetime import datetime, timezone
from typing import NamedTuple
from sentinel.core.models import CheckResult
from sentinel.core.process import run_command, catch_return_code, strip_noise, extract_by_prefix

logger = logging.getLogger(__name__)


class PackageUpdate(NamedTuple):
    name_arch: str
    version: str
    repo: str


class AdvisoryInfo(NamedTuple):
    advisory_id: str
    severity_or_type: str


class StalenessInfo(NamedTuple):
    last_update: datetime
    update_action: str


def collect() -> list[CheckResult]:

    results: list[CheckResult] = []
    results.extend(_collect_package_updates())
    results.extend(_collect_reboot_status())
    results.extend(_collect_patch_staleness())

    return results


def _collect_package_updates() -> list[CheckResult]:

    results: list[CheckResult] = []

    updates = run_command(["dnf", "check-update"])

    if updates is None:
        return results

    if catch_return_code(updates.returncode, {1, 3}, updates.stderr) is None:
        return results

    updateinfo = run_command(["dnf", "updateinfo", "list"])

    if (
        updateinfo is None
        or catch_return_code(updateinfo.returncode, {1, 3}, updateinfo.stderr) is None
    ):
        advisories_by_nevra = {}
    else:
        advisories_by_nevra = _parse_updateinfo(updateinfo.stdout)

    for update in _parse_check_update(updates.stdout):

        update_advisories = advisories_by_nevra.get(
            _build_nevra(name_arch=update.name_arch, version=update.version), []
        )

        is_security_update = any(
            "Sec" in advisory.severity_or_type for advisory in update_advisories
        )

        json_safe_advisories = [adv._asdict() for adv in update_advisories]

        results.append(
            CheckResult(
                collector="patch_status",
                target=update.name_arch,
                timestamp=datetime.now(timezone.utc),
                metrics={
                    "update_available": True,
                    "is_security_update": is_security_update,
                },
                details={
                    "version": update.version,
                    "repo": update.repo,
                    "advisories": json_safe_advisories,
                },
            )
        )

    logger.info(
        "patch_status collector complete. Found %d package(s) updates",
        len(results),
    )
    return results


def _parse_check_update(stdout: str) -> list[PackageUpdate]:
    """Pure parse: (name_arch, version, repo) tuples from check-update's stdout."""
    stdout_lines = stdout.splitlines()
    results: list[PackageUpdate] = []

    for line in stdout_lines:
        parts = line.split()

        if len(parts) != 3:
            continue

        name_arch, version, repo = parts
        results.append(PackageUpdate(name_arch=name_arch, version=version, repo=repo))

    return results


def _parse_updateinfo(stdout: str) -> dict[str, list[AdvisoryInfo]]:
    """Pure parse: NEVRA -> list of {advisory_id, type_or_severity} from updateinfo's stdout."""
    stdout_lines = stdout.splitlines()
    results: dict[str, list[AdvisoryInfo]] = {}

    for line in stdout_lines:
        parts = line.split()

        if len(parts) != 3:
            continue
        advisory_id, severity_or_type, nevra = parts
        results.setdefault(nevra, []).append(
            AdvisoryInfo(advisory_id=advisory_id, severity_or_type=severity_or_type)
        )
    return results


def _parse_staleness(stdout: str) -> list[StalenessInfo]:
    """Pure parse: (last_update, update_action) tuples from history list's stdout."""
    results: list[StalenessInfo] = []

    for line in stdout.splitlines():
        parts = line.split("|")
        if len(parts) != 5:
            continue
        if parts[0].strip() == "ID":
            continue
        results.append(
            StalenessInfo(
                last_update=datetime.strptime(parts[2].strip(), "%Y-%m-%d %H:%M"),
                update_action=parts[3].strip(),
            )
        )

    return results


def _build_nevra(name_arch: str, version: str) -> str:
    """This helper builds the nevra to match the serverity information provided by updateinfo.
    This will be used to map update severity to check-updates package information."""
    name, arch = name_arch.rsplit(".", 1)
    return f"{name}-{version}.{arch}"


def _collect_reboot_status() -> list[CheckResult]:

    results: list[CheckResult] = []
    reboot_status = run_command(["dnf", "needs-restarting", "-r"])

    if reboot_status is None:
        return results

    reboot_return_code = reboot_status.returncode

    results.append(
        CheckResult(
            collector="patch_status",
            target=None,
            timestamp=datetime.now(timezone.utc),
            metrics={"reboot_required": bool(reboot_return_code)},
            details={
                "description": "\n".join(
                    strip_noise(
                        reboot_status.stdout, ("Not root,", "Last metadata expiration check:")
                    )
                ),
                "packages": extract_by_prefix(reboot_status.stdout, "*"),
            },
        )
    )

    # NOTE: dnf's general docs say 1 = "an error dnf handled" for most subcommands,
    # but needs-restarting -r's own docs override that meaning specifically for
    # this flag: 1 = reboot required, 0 = not required. If -r ever hit a genuine
    # error that also happened to exit 1, this would misreport it as "reboot
    # required" rather than surfacing the error. Accepted looseness for now —
    # disambiguating would mean inspecting stdout content, more than this
    # concern calls for.

    return results


def _collect_patch_staleness() -> list[CheckResult]:

    results: list[CheckResult] = []

    history = run_command(["dnf", "history", "list"])

    if history is None:
        return results
    if catch_return_code(history.returncode, {1, 3}, history.stderr) is None:
        return results

    parsed_history = _parse_staleness(history.stdout)

    if len(parsed_history) == 0:
        logger.info("patch_status collector complete. No patch history found")
        results.append(
            CheckResult(
                collector="patch_status",
                target=None,
                timestamp=datetime.now(timezone.utc),
                metrics={"patch_history_found": False},
                details={
                    "last_update": None,
                    "last_update_action": None,
                    "days_since_last_patch": None,
                },
            )
        )
        return results

    qualifying_entries: list[StalenessInfo] = [
        entry
        for entry in parsed_history
        if "U" in entry.update_action.split(", ") or "Upgrade" in entry.update_action.split(", ")
    ]

    if len(qualifying_entries) == 0:
        logger.info(
            "patch_status collector complete. No qualifying patch updates found. Only install/erase actions found."
        )
        results.append(
            CheckResult(
                collector="patch_status",
                target=None,
                timestamp=datetime.now(timezone.utc),
                metrics={"patch_history_found": True},
                details={
                    "last_update": None,
                    "last_update_action": None,
                    "days_since_last_patch": None,
                },
            )
        )
        return results

    latest_entry = max(qualifying_entries, key=lambda e: e.last_update)

    results.append(
        CheckResult(
            collector="patch_status",
            target=None,
            timestamp=datetime.now(timezone.utc),
            metrics={"patch_history_found": True},
            details={
                "last_update": latest_entry.last_update.isoformat(),
                "last_update_action": latest_entry.update_action,
                "days_since_last_patch": (datetime.now() - latest_entry.last_update).days,
            },
        )
    )

    return results
