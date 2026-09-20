import logging
import subprocess
from subprocess import CompletedProcess
from datetime import datetime, timezone
from sentinel.core.models import CheckResult

logger = logging.getLogger(__name__)

def collect() -> list[CheckResult]:
    """
    Failed units collector.
    Aggregates data on failed units via systemd.
    """
    failed_units: CompletedProcess = subprocess.run(["systemctl", "list-units", "-t service", "--no-legend", "--plain"])
    results: list[CheckResult] = []
    
    return results
       
