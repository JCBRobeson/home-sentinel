import logging
import subprocess
from subprocess import CompletedProcess

logger = logging.getLogger(__name__)


def run_command(args: list[str]) -> CompletedProcess[str] | None:
    """Runs a subprocess with the settings every collector needs identically
    (captured output, text mode), returning None when the binary itself is
    missing so callers can branch on that without duplicating a try/except.
    Return-code interpretation stays with each caller."""
    try:
        return subprocess.run(args=args, capture_output=True, text=True)
    except FileNotFoundError:
        logger.warning("%s: command not found", " ".join(args))
        return None


def catch_return_code(return_code: int, failure_condition: set[int], stderr: str) -> int | None:
    """Catches return codes from subprocess.run calls and logs the error code and stderr output"""
    if return_code in failure_condition:
        logger.error("Error Code: %d : %s", return_code, stderr)
        return None
    else:
        return return_code


def strip_noise(stdout: str, prefixes: tuple[str, ...]) -> list[str]:
    """strip noise in stdout. For example, dnf prefixes unprivileged output with boilerplate (subscription-manager
    nag, metadata-expiration notice) that varies by command but always starts
    the same way — filtering it here once means every collector with noise does not reivnent this"""

    return [line for line in stdout.splitlines() if line and not line.startswith(prefixes)]


def extract_by_prefix(stdout: str, prefix: str) -> list[str]:
    """Extract a value based on a prefix i.e. * kernel"""
    return [
        clean.removeprefix(prefix).strip()
        for line in stdout.splitlines()
        if line and (clean := line.lstrip()).startswith(prefix)
    ]
