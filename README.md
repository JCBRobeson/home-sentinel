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

## Logging

Sentinel logs to `/var/log/sentinel/sentinel.log`, not `/var/lib/sentinel/`.

**Why not `/var/lib/sentinel`:** that directory is `700`, owned solely by `sentinel` — correct for _application state_ (SQLite store, etc.), which nobody but the service account should touch. But logs aren't state, they're operational output a human needs to read. Putting logs inside that same locked-down directory means no one — not even the person operating the box — could ever read a log line without `sudo`-ing into the `sentinel` account first. `/var/log/sentinel` is the standard FHS location for exactly this reason, and it lets us set up real group-based read access instead of forcing root for every `tail`.

**One-time host setup** (same category as service-account creation above — do this once per host):

```bash
sudo mkdir -p /var/log/sentinel
sudo chown sentinel:sentinel /var/log/sentinel
sudo chmod 2770 /var/log/sentinel
sudo usermod -aG sentinel <your-username>
```

- `chmod 2770` — the leading `2` sets the **setgid bit** on the directory: any file created inside inherits the directory's group (`sentinel`) regardless of which user created it, so dev-created and production-created log files stay consistently group-owned instead of a mix. `770` = owner and group get full read/write/traverse, everyone else gets nothing.
- `usermod -aG sentinel <your-username>` — adds your personal account to the `sentinel` group _in addition to_ existing groups (`-a` = append; omitting it wipes other group memberships). This is what lets a human read/tail logs without becoming the service account.

**Rotation:** handled in-process via Python's `RotatingFileHandler` — 5MB per file, 5 backups retained (~30MB ceiling, roughly 4–5 months of history at expected v1 log volume). No external `logrotate` config needed.

### Reading logs as a human (dev and production, same answer)

`sentinel` (the process) writes logs. A human operator needs to read them without becoming the `sentinel` account. Linux's standard answer when two different identities need shared access to the same files is: put them in the same group, and grant that group access — which is exactly what the setup above does.

**This is not a dev-only workaround — it's also the production answer.** Nothing about it needs to be reversed or redone in Phase 6. The only thing that changes in production is _who starts the Sentinel process_ (systemd, running it natively as `User=sentinel`, instead of a human invoking it by hand) — the log directory, its permissions, and group-based read access stay exactly as already configured.

To grant a new operator read access to logs on any host, ever:

```bash
sudo usermod -aG sentinel <their-username>
```

**Why a fresh login is needed after `usermod`:** group membership is read once, when a shell/process starts — not re-checked afterward. Adding someone to a group doesn't retroactively affect their already-running shell. A full logout/login (or reboot) is what makes new group membership take effect, with no special command needed afterward.

`newgrp sentinel` is a shortcut for testing in the same terminal session without fully logging out — it spawns a new child shell that re-reads group membership immediately. It's temporary and scoped to that one nested shell only (`exit` returns you to the original, stale-group shell); it is **not** required on every login going forward, and isn't part of normal day-to-day use once you've logged out/in once.

**Alternative for later, not implemented:** systemd's own `journald` can capture a service's output directly, queryable via `journalctl -u sentinel`, with its own separate access model (see the `systemd-journal` group grant in the Service Account section above — used currently for the journald _collector_, not for Sentinel's own output). Worth knowing this exists if flat-file logging ever stops being the right fit; not needed for anything currently built.

**Revisit in Phase 6:** once a systemd unit file exists, its `LogsDirectory=` directive can create and own this directory declaratively instead of the manual `mkdir`/`chown`/`chmod` above — at that point, drop this manual setup section and document the unit file's handling instead.
Systemctl Begins
