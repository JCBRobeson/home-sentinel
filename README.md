# Home Sentinel

## Setup

Sentinel runs under a dedicated, unprivileged system service account rather than root or your personal user.

**1. Create the service account:**

```bash
sudo useradd -r -s /sbin/nologin -d /var/lib/sentinel -m sentinel
```

- `-r` — system account (UID pulled from the reserved system range, not a regular user UID)
- `-s /sbin/nologin` — no interactive shell; the account can only run commands via `sudo -u sentinel <cmd>`, never log in directly
- `-d /var/lib/sentinel -m` — home directory under `/var/lib`, per FHS convention for service state data (this is also where the SQLite store will live)

**2. Grant journal-read access:**

```bash
sudo usermod -aG systemd-journal sentinel
```

Journald log access is gated by group membership, not by file permissions or sudo — without this, the journald collector silently returns nothing (or errors) with no obvious cause.

**3. No sudoers entry.**

Every other v1 collector (disk usage, systemd unit status, package update status, `/etc/passwd`/wheel-group audit) reads data that's world-readable on a standard RHEL system. `sentinel` has **no sudo grants** — this is intentional, not an oversight. If a future check genuinely needs elevated access, add a narrowly scoped rule under `/etc/sudoers.d/sentinel` for that specific command at that time, rather than granting broadly up front.
