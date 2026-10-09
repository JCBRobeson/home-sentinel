import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import NamedTuple
from sentinel.core.models import CheckResult
from sentinel.core.process import run_command, catch_return_code

logger = logging.getLogger(__name__)


class PasswdEntry(NamedTuple):
    name: str
    uid: int
    gid: int
    shell: str


class UIDRange(NamedTuple):
    uid_min: int
    uid_max: int


def _parse_passwd(stdout: str) -> list[PasswdEntry]:
    results: list[PasswdEntry] = []

    for line in stdout.splitlines():
        parts = line.split(":")

        if len(parts) != 7:
            logger.warning("Unexpected format found %s field(s) instead of 7. Skipping", len(parts))
            continue

        try:
            uid = int(parts[2])
            gid = int(parts[3])
        except ValueError:
            logger.warning(
                "Skipping account %s: non-numeric uid/gid (%r, %r)", parts[0], parts[2], parts[3]
            )
            continue

        results.append(
            PasswdEntry(
                name=parts[0],
                uid=uid,
                gid=gid,
                shell=parts[6],
            )
        )
    return results


def _parse_UID_range(logindefs: str) -> UIDRange:
    logindefs = Path("/etc/login.defs").read_text()
    good_lines: list[str] = []

    for line in logindefs.splitlines():
        if line.startswith("#") or line.startswith(" "):
            continue
        good_lines.append(line)
