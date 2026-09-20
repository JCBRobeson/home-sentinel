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
    
    failed_units: CompletedProcess[str] | None = None
    failed_units_lines = []
    results: list[CheckResult] = []
    
    try:
        failed_units = subprocess.run(args=["systemctl", "list-units", "-t", "service", "--state=failed","--no-legend", "--plain"], capture_output=True, text=True)
        failed_units_lines = failed_units.stdout.splitlines()
    except FileNotFoundError:
       logger.warning("systemctl: command not found")     
    
    if failed_units is not None and failed_units.returncode != 0:
        logger.error("Error Code: %d : %s", failed_units.returncode, failed_units.stderr)
    else:
        for line in failed_units_lines:
            sub_line = line.split(maxsplit=4)
            results.append(
                CheckResult(
                    collector="failed_units",
                    target= sub_line[0],
                    timestamp=datetime.now(timezone.utc),
                    metrics={
                        "failed": True
                    },
                    details={
                        "service": sub_line[0],
                        "load": sub_line[1],
                        "sub": sub_line[3],
                        "description": sub_line[4]
                    }
                    
                )
            )
    
    return results
       
