import grp
import logging
import pwd
from datetime import datetime
from typing import NamedTuple

logger = logging.getLogger(__name__)

DEFAULT_UID_MIN = 1000
DEFAULT_UID_MAX = 60000


class PasswdEntry(NamedTuple):
    name: str
    uid: int
    gid: int
    shell: str
    uses_shadowed_password: bool


class UIDRange(NamedTuple):
    uid_min: int
    uid_max: int


class LoginHistory(NamedTuple):
    latest_logins: dict[str, datetime]
    history_begins: datetime | None


def _parse_uid_range(login_defs: str) -> UIDRange:
    """Extract the human UID range from /etc/login.defs.

    Exact key match keeps SYS_UID_* and commented keys out. Missing or
    invalid keys fall back to RHEL defaults with a warning, never silently.
    """
    uid_min: int | None = None
    uid_max: int | None = None

    for line in login_defs.splitlines():
        parts = line.split()
        if len(parts) != 2:
            continue

        key, value = parts
        if key not in ("UID_MIN", "UID_MAX"):
            continue

        try:
            parsed = int(value)
        except ValueError:
            logger.warning("Non-numeric %s in login.defs: %r", key, value)
            continue

        if key == "UID_MIN":
            uid_min = parsed
        else:
            uid_max = parsed

    if uid_min is None:
        logger.warning(
            "UID_MIN missing or invalid in login.defs, using default %s", DEFAULT_UID_MIN
        )
        uid_min = DEFAULT_UID_MIN
    if uid_max is None:
        logger.warning(
            "UID_MAX missing or invalid in login.defs, using default %s", DEFAULT_UID_MAX
        )
        uid_max = DEFAULT_UID_MAX

    return UIDRange(uid_min=uid_min, uid_max=uid_max)


def _parse_last(stdout: str) -> LoginHistory:
    """Parse `last -w -i --time-format iso` output into each user's latest login.

    The source IP column is never read or stored (privacy). Reboot lines are
    skipped before the field-count guard because their terminal column
    ("system boot") is two words. Latest login is chosen by comparison, not
    output order.
    """
    latest_logins: dict[str, datetime] = {}
    history_begins: datetime | None = None

    for line in stdout.splitlines():
        if not line.strip():
            continue

        if line.startswith("wtmp begins "):
            stamp = line.removeprefix("wtmp begins ")
            try:
                history_begins = datetime.fromisoformat(stamp)
            except ValueError:
                logger.warning("Unparseable wtmp begins timestamp: %r", stamp)
            continue

        parts = line.split(maxsplit=4)
        if parts[0] == "reboot":
            continue

        if len(parts) != 5:
            logger.warning("Skipping last line: expected 5 fields, got %s", len(parts))
            continue

        user = parts[0]
        try:
            login_time = datetime.fromisoformat(parts[3])
        except ValueError:
            logger.warning("Skipping login for %s: unparseable time %r", user, parts[3])
            continue

        current = latest_logins.get(user)
        if current is None or login_time > current:
            latest_logins[user] = login_time

    return LoginHistory(latest_logins=latest_logins, history_begins=history_begins)
