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

    return results


def _collect_reboot_status() -> list[CheckResult]:

    results: list[CheckResult] = []

    return results


def _collect_patch_staleness() -> list[CheckResult]:

    results: list[CheckResult] = []

    return results
