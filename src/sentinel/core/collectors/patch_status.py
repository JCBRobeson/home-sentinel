import logging
from datetime import datetime, timezone
from typing import NamedTuple
from sentinel.core.models import CheckResult
from sentinel.core.process import run_command, catch_return_code

logger = logging.getLogger(__name__)


class PackageUpdate(NamedTuple):
    name_arch: str
    version: str
    repo: str


class AdvisoryInfo(NamedTuple):
    advisory_id: str
    severity_or_type: str


def collect() -> list[CheckResult]:

    results: list[CheckResult] = []
    results.extend(_collect_package_updates())
    results.extend(_collect_reboot_status())
    results.extend(_collect_patch_staleness())

    return results


def _collect_package_updates() -> list[CheckResult]:

    results: list[CheckResult] = []

    updates = run_command(["dnf", "check-update"])
    updateinfo = run_command(["dnf", "updateinfo", "list"])

    if updates is None or updateinfo is None:
        return results

    if catch_return_code(updates.returncode, {1, 3}, updates.stderr) is None:
        return results
    if catch_return_code(updateinfo.returncode, {1, 3}, updateinfo.stderr) is None:
        return results

    for update in _parse_check_update(updates.stdout):
        results.append(
            CheckResult(
                collector="patch_status",
                target=update.name_arch,
                timestamp=datetime.now(timezone.utc),
                metrics={"update_available": True},
                details={"version": update.version, "repo": update.repo},
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


def _collect_reboot_status() -> list[CheckResult]:

    results: list[CheckResult] = []

    return results


def _collect_patch_staleness() -> list[CheckResult]:

    results: list[CheckResult] = []

    return results
