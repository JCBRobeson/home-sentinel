import logging
import subprocess
from subprocess import CompletedProcess
from datetime import datetime, timezone
from sentinel.core.models import CheckResult

logger = logging.getLogger(__name__)


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
        packages_for_update: list[str] = updates.stdout.splitlines()
    except FileNotFoundError:
        logger.warning("dnf check-update: command not found")
        return results

    if updates.returncode == 1:
        logger.error("Error Code: %d : %s", updates.returncode, updates.stderr)
        return results

    for line in packages_for_update:
        parts = line.split()
        if len(parts) != 3:
            continue
        results.append(
            CheckResult(
                collector="patch_status",
                target=parts[0],
                timestamp=datetime.now(timezone.utc),
                metrics={"update_available": True},
                details={"version": parts[1], "repo": parts[2]},
            )
        )
    logger.info(
        "patch_status collector complete. Found %d package(s) updates",
        len(results),
    )
    return results


def _collect_reboot_status() -> list[CheckResult]:

    results: list[CheckResult] = []

    return results


def _collect_patch_staleness() -> list[CheckResult]:

    results: list[CheckResult] = []

    return results
