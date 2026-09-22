import logging
import subprocess
from subprocess import CompletedProcess
from datetime import datetime, timezone
from sentinel.core.models import CheckResult

logger = logging.getLogger(__name__)


def collect() -> list[CheckResult]:

    results: list[CheckResult] = []

    return results
