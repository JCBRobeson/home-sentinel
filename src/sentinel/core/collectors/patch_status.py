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


def _build_nevra(name_arch: str, version: str) -> str:
    """This helper builds the nevra to match the serverity information provided by updateinfo.
    This will be used to map update severity to check-updates package information."""
    name, arch = name_arch.rsplit(".", 1)
    return f"{name}-{version}.{arch}"


def _collect_reboot_status() -> list[CheckResult]:

    results: list[CheckResult] = []

    return results


def _collect_patch_staleness() -> list[CheckResult]:

    results: list[CheckResult] = []

    return results
