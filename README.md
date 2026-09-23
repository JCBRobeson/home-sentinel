# Home Sentinel

A self hosted monitoring, alerting, and self healing tool for my home lab. I built this as a DevOps/cloud portfolio piece, so the goal isn't just "does it work," it's "does it look like infrastructure ownership." Code quality and architecture clarity matter here as much as feature count.

## Setup

Sentinel runs under a dedicated, unprivileged system service account. Not root, not my personal user.

**1. Create the service account:**

```bash
sudo useradd -r -s /sbin/nologin -d /var/lib/sentinel -m sentinel
```

`-r` gives it a system account (UID pulled from the reserved system range, not a regular user UID). `-s /sbin/nologin` means no interactive shell, so the account can only run commands via `sudo -u sentinel <cmd>`, never log in directly. `-d /var/lib/sentinel -m` sets up a home directory under `/var/lib`, which is the FHS convention for service state data (also where the SQLite store will eventually live).

**2. Grant journal read access:**

```bash
sudo usermod -aG systemd-journal sentinel
```

Journald log access is gated by group membership, not file permissions or sudo. Skip this and the journald collector silently returns nothing (or errors) with no obvious cause.

**3. No sudoers entry.**

Every v1 collector I've built so far (disk usage, systemd unit status, package update status, and eventually the passwd/wheel group audit) reads data that's world readable on a standard RHEL box. `sentinel` gets no sudo grants at all. That's intentional. If a future check genuinely needs elevated access, I'll scope a narrow, single command rule under `/etc/sudoers.d/sentinel` for exactly that need, rather than granting broad access up front.

## Logging

Sentinel logs to `/var/log/sentinel/sentinel.log`, not `/var/lib/sentinel/`.

**Why not `/var/lib/sentinel`:** that directory is `700`, owned solely by `sentinel`. That's the right call for application state (the SQLite store, etc.), which nobody but the service account should be touching. But logs aren't state, they're operational output a human actually needs to read. If logs lived inside that same locked down directory, nobody, not even me operating the box, could read a log line without sudoing into the `sentinel` account first. `/var/log/sentinel` is the standard FHS location for exactly this reason, and it lets me set up real group based read access instead of requiring root for every `tail`.

**One time host setup** (same category as the service account creation above, do this once per host):

```bash
sudo mkdir -p /var/log/sentinel
sudo chown sentinel:sentinel /var/log/sentinel
sudo chmod 2770 /var/log/sentinel
sudo usermod -aG sentinel <your-username>
```

The leading `2` in `chmod 2770` sets the setgid bit on the directory. Any file created inside inherits the directory's group (`sentinel`) no matter which user created it, so dev created and production created log files all stay consistently group owned instead of a mix. The `770` part means owner and group get full read/write/traverse, everyone else gets nothing. `usermod -aG sentinel <your-username>` adds my personal account to the `sentinel` group in addition to my existing groups (the `-a` flag matters here, leaving it off wipes other group memberships).

**Rotation** is handled in process via Python's `RotatingFileHandler`, 5MB per file, 5 backups retained (about a 30MB ceiling, roughly 4 to 5 months of history at expected v1 log volume). No external `logrotate` config needed.

### Reading logs as a human (dev and production, same answer)

`sentinel` the process writes logs. A human operator needs to read them without becoming the `sentinel` account. Linux's standard answer when two different identities need shared access to the same files is put them in the same group and grant that group access, which is exactly what the setup above does.

**This isn't a dev only workaround, it's also the production answer.** Nothing about it gets reversed or redone in Phase 6. The only thing that changes in production is who starts the Sentinel process (systemd running it natively as `User=sentinel`, instead of me invoking it by hand). The log directory, its permissions, and group based read access stay exactly as configured here.

To grant a new operator read access to logs on any host, ever:

```bash
sudo usermod -aG sentinel <their-username>
```

**Why a fresh login is needed after `usermod`:** group membership gets read once, when a shell or process starts, not re-checked afterward. Adding someone to a group doesn't retroactively affect their already running shell. A full logout/login (or reboot) is what makes new group membership take effect, no special command needed after that.

`newgrp sentinel` is a shortcut for testing in the same terminal session without fully logging out. It spawns a new child shell that re-reads group membership immediately. It's temporary and scoped to that one nested shell only (`exit` returns you to the original, stale group shell). It's not required on every login going forward, and isn't part of normal day to day use once I've logged out and back in once.

**Alternative for later, not implemented:** systemd's own journald can capture a service's output directly, queryable via `journalctl -u sentinel`, with its own separate access model (see the `systemd-journal` group grant in the Service Account section above, used currently for the journald collector, not Sentinel's own output). Worth knowing this exists if flat file logging ever stops being the right fit. Not needed for anything currently built.

**Revisit in Phase 6:** once a systemd unit file exists, its `LogsDirectory=` directive can create and own this directory declaratively instead of the manual `mkdir`/`chown`/`chmod` above. At that point I'll drop this manual setup section and document the unit file's handling instead.

## Collectors

Every collector implements `collect() -> list[CheckResult]`, reporting plain facts (metrics as numeric/boolean, details as anything richer), never judgments or severity labels. That's the rules engine's job later, not the collector's.

### Disk usage (`disk.py`)

Checks `/`, `/var`, and `/home` by default via `shutil.disk_usage`. Skips a mount cleanly with a logged warning if it's missing rather than crashing the whole run.

### Failed systemd units (`failed_units.py`)

Runs `systemctl list-units -t service --state=failed --no-legend --plain` and reports one result per failed unit. Only produces output when something's actually wrong, never a healthy service report.

### Patch status (`patch_status.py`)

This one covers four separate concerns under one collector, since they're really all angles on the same question: is this box current on patches and running clean.

1. **Available updates**, via `dnf check-update`. One result per package, covers every repo including third party ones like docker-ce-stable. I'm on dnf4 here (RHEL 10's default, dnf5 isn't out on RHEL yet), so exit codes are 0 for nothing pending, 100 for updates found (both count as success, not an error), 1 and 3 for real errors per `man dnf`'s own return value docs.

2. **Security severity**, via `dnf updateinfo list`, joined onto the check-update results. I reconstruct each package's NEVRA string from check-update's own clean name/version/arch fields rather than trying to parse updateinfo's NEVRA text apart, since package names have dashes and digits in them and splitting that string back into parts reliably isn't worth the risk. Bugfix advisories carry no severity field at all, only RHSA security advisories do. Third party packages like the Docker ones just get an empty advisories list since Red Hat has no idea they exist.

3. **Reboot required**, via `dnf needs-restarting -r`. Not built yet. One system wide result, not per package, since a pending reboot is a fact about the whole box.

4. **Patch staleness**, via `dnf history list`, using dnf's own transaction history instead of anything SQLite or database dependent. Not built yet. The key detail here is that "last patched" needs to filter by the Action column actually containing an Upgrade, not just by scanning command text, since a plain `install vim-enhanced` can still trigger dependency upgrades under the hood.

I deliberately did not go anywhere near `/var/lib/dnf/history.sqlite` directly, even though it's technically readable. The schema isn't stable across dnf versions, the storage path itself has moved before, and it's disposable cache from dnf's own point of view (corruption reports just say delete it and let dnf rebuild it). `dnf history list` is the real, maintained interface, so that's what I'm using.