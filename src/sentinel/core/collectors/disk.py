import shutil
from datetime import datetime, timezone
from sentinel.core.models import CheckResult

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
    results = []
    
    for mount in mounts:
        try:
            usage = shutil.disk_usage(mount)
        except FileNotFoundError:
            continue
        
        results.append(
            CheckResult(
               collector="disk_usage",
               target=mount,
               timestamp=datetime.now(timezone.utc).isoformat(),
               metrics={
                    "total_bytes": usage.total,
                    "used_bytes": usage.used,
                    "free_bytes": usage.free,
                    "used_percent": round(usage.used / usage.total * 100, 1),
               }
            )
        )
    return results