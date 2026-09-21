import logging
import subprocess
from subprocess import CompletedProcess
from datetime import datetime, timezone
from sentinel.core.models import CheckResult

logger = logging.getLogger(__name__)

def collect() -> list[CheckResult]:
    """
    Failed units collector.
    Aggregates data on failed systemd service units.
    Filters to --state=failed at the systemctl level (not in Python)
    so the collector only produces output when something is actually
    wrong, rather than reporting every healthy service on every run.
    """
    results: list[CheckResult] = []
    
    try:
        failed_units: CompletedProcess[str] = subprocess.run(args=["systemctl", "list-units", "-t", "service", "--state=failed","--no-legend", "--plain"], capture_output=True, text=True)
        failed_units_lines: list[str] = failed_units.stdout.splitlines()
    except FileNotFoundError:
       logger.warning("systemctl: command not found")
       return results     
    
    if failed_units.returncode != 0:
        logger.error("Error Code: %d : %s", failed_units.returncode, failed_units.stderr)
        return results
    
    for line in failed_units_lines:
        sub_line = line.split(maxsplit=4)
        if len(sub_line) < 5:
            logger.warning("Unexpected line format, skipping %s", line)
            continue
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
    logger.info("failed_units collector completed. Found %d failing units", len(results))
    return results
       
