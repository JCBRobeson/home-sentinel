# src/sentinel/core/collectors/linux.py
import shutil
from datetime import datetime, timezone

def get_disk_usage(path: str = "/") -> dict:
    """  
    Returns disk usage for `path` as structured data.
    Uses shutil.disk_usage() (a thin wrapper over os.statvfs on Linux)
    rather than shelling out to `df` and parsing text — same underlying
    syscall, no fragile string parsing.
    """
    usage = shutil.disk_usage(path)
    
    return {
        "collector": "disk_usage",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "path": path,
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": usage.free,
        "used_percent": round(usage.used / usage.total * 100, 1),
    }