import logging
import shutil
from datetime import datetime, timezone
from sentinel.core.models import CheckResult

logger = logging.getLogger(__name__)

DEFAULT_MOUNTS = ["/", "/var", "/home"]

def collect(path: str | None = None) -> list[CheckResult]:
    """
    Disk usage collector.
    If `path` is given, checks only that path.
    If not, checks each of DEFAULT_MOUNTS independently — on RHEL, /var
    can fill from logs or container images while / stays fine, so a
    single root-only check would miss that.
    """
    mounts = [path] if path else DEFAULT_MOUNTS
    results: list[CheckResult] = []
    
    for mount in mounts:
        try:
            usage = shutil.disk_usage(mount)
        except FileNotFoundError:
            logger.warning("Mount path not found, skipping: %s", mount)
            continue
        
        results.append(
            CheckResult(
               collector="disk_usage",
               target=mount,
               timestamp=datetime.now(timezone.utc),
               metrics={
                    "total_bytes": usage.total,
                    "used_bytes": usage.used,
                    "free_bytes": usage.free,
                    "used_percent": round(usage.used / usage.total * 100, 1),
               }
            )
        )
        
    logger.info("disk_usage collector completed, checked %d mount(s)", len(results))    
    return results