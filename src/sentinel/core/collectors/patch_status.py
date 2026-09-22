import logging
import subprocess
from typing import NamedTuple
from subprocess import CompletedProcess
from datetime import datetime, timezone
from sentinel.core.models import CheckResult

logger = logging.getLogger(__name__)


class PackageUpdate(NamedTuple):
    name_arch: str
    version: str
    repo: str


def collect() -> list[CheckResult]:

    results: list[CheckResult] = []
    results.extend(_collect_package_updates())
    results.extend(_collect_reboot_status())
    results.extend(_collect_patch_staleness())

    return results


def _collect_package_updates() -> list[CheckResult]:

    results: list[CheckResult] = []

    try:
        updates: CompletedProcess[str] = subprocess.run(
            args=["dnf", "check-update"], capture_output=True, text=True
        )
    except FileNotFoundError:
        logger.warning("dnf check-update: command not found")
        return results

    if updates.returncode == 1:
        logger.error("Error Code: %d : %s", updates.returncode, updates.stderr)
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
        results.append(
            PackageUpdate(name_arch=parts[0], version=parts[1], repo=parts[2])
        )

    return results


def _collect_reboot_status() -> list[CheckResult]:

    results: list[CheckResult] = []

    return results


def _collect_patch_staleness() -> list[CheckResult]:

    results: list[CheckResult] = []

    return results
