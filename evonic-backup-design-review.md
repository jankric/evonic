# Evonic Backup System — Design Review

**Reviewer:** Linus Torvalds (via Linus agent)  
**Date:** 2026-05-20  
**Verdict:** CONDITIONAL GO — 4 blockers, 5 warnings, 2 missing data paths

---

## 1. Data Paths — You Mapped Them Wrong

This is the most critical issue in the whole design. Let me say this slowly because it matters:

**Agent data lives at `/workspace/agents/<id>/`, NOT `/workspace/shared/agents/<id>/`.**

I checked the actual filesystem. Here's what actually exists:

| What you listed | What's actually on disk |
|---|---|
| `agents/<agent_id>/` — SYSTEM.md, chat.db, kb/, sessions/ | Lives at `/workspace/agents/<id>/` — SYSTEM.md, chat.db, kb/, sessions/ |
| `shared/agents/<agent_id>/artifacts/` | Correct — lives at `/workspace/shared/agents/<id>/artifacts/` |

These are TWO DIFFERENT directory trees. Your backup design lists them as if they're the same path. They're not. If you code this from your design doc, you will back up artifacts and miss every agent's SYSTEM.md, chat.db, kb/, and sessions/. That's not a minor bug — that's "the backup restores nothing useful."

**Blocking issue #1: Fix the paths.** Explicitly list both:
- `/workspace/agents/<id>/` — SYSTEM.md, chat.db, kb/, sessions/
- `/workspace/shared/agents/<id>/artifacts/` — artifacts

---

## 2. MD5 Hash — What Year Is This, 1995?

You're using MD5 for integrity checking. MD5 has been cryptographically broken since 2004. Wang et al. demonstrated collision attacks. By 2012, the Flame malware exploited MD5 collisions to fake a Microsoft code-signing certificate.

Now, are you defending against nation-state attackers forging your backups? No. But here's the thing: **SHA-256 is already in `hashlib`.** It costs you exactly zero extra lines of code. You type `sha256` instead of `md5`. That's the entire migration effort.

Using MD5 in 2026 is like showing up to a Formula 1 race in a horse-drawn carriage and saying "well, it still moves." It does. But why would you?

**Blocking issue #2: Use SHA-256.** No justification for MD5.

---

## 3. Live SQLite Backup — You're Doing It Wrong

The design says nothing about how you get a consistent backup of a LIVE database. The restore workflow says "stop server → copy back → restart," which is fine for restore, but what about backup?

If the server is running while you `cp evonic.db`, you're copying a file that's being written to. SQLite uses WAL mode (I can see `evonic.db-wal` on disk). Copying the main database file while the WAL has uncommitted transactions gives you a corrupted backup. This is Backup 101.

The correct approach for SQLite is `connection.backup()` — the online backup API. Python's `sqlite3` module exposes it:

```python
import sqlite3
src = sqlite3.connect('shared/db/evonic.db')
dst = sqlite3.connect('/tmp/backup.db')
src.backup(dst)
dst.close()
src.close()
```

This gives you a transactionally consistent copy WITHOUT stopping the server. It's been in SQLite since 3.6.11 (2009). It's been in Python's sqlite3 module since forever.

There are two valid approaches:
1. **Use `connection.backup()`** — zero downtime, consistent snapshot
2. **Stop the server, copy, restart** — consistent but downtime

The design mentions neither. For a database that can be 58MB (that's what `evonic.db` is right now) and growing, you need approach #1.

**Blocking issue #3: Use SQLite's online backup API for live databases.** Do not `cp` a live SQLite file.

---

## 4. `.env` "Encryption" — Theater, Not Security

The design says `shared/.env` is backed up "encrypted." With what key? Where is it stored? How is it decrypted on restore?

If the encryption key is on the same filesystem, you've achieved nothing except making the restore process more fragile. It's the cryptographic equivalent of locking your front door and leaving the key under the doormat. Anyone who steals the backup file has the key too.

Also: there are TWO `.env` files. `/workspace/.env` and `/workspace/shared/.env`. They're different. The one at `/workspace/.env` has MORE secrets (including `GITHUB_TOKEN_ANVIE` and `PINCHTAB_TOKEN`). Your design only mentions `shared/.env`.

Two options:
- **Encrypt with a user-supplied passphrase** — prompt for it at backup time, require it at restore time. This is real encryption.
- **Don't encrypt** — just back up the `.env` files as-is and document that the backup file must be stored with `chmod 600` or equivalent.

The half-assed middle ground ("we'll encrypt it somehow") is worse than either option because it creates a false sense of security.

**Blocking issue #4: Design the `.env` encryption properly or drop it.** Also, you're missing `/workspace/.env`.

---

## 5. Compression Defaults — bzip2 Is For Masochists

The design says compression priority `tar.bz2 > tar.gz > zip`. Let me translate what that means in practice:

| Format | Compression speed | Decompression speed | Size vs gzip |
|---|---|---|---|
| tar.gz | 100 MB/s | 300 MB/s | baseline |
| tar.bz2 | 10 MB/s | 30 MB/s | ~85% of gzip size |
| zip | 80 MB/s | 200 MB/s | ~95% of gzip size |

So you're making bzip2 the default. That means for a 100MB backup, the user waits 10 seconds instead of 1 second for compression, saves maybe 15MB, and then waits 3x longer on restore too. For what? Disk space is cheap. User time is not.

The correct default is **tar.gz**. Fast, universal, good enough. Offer `--format bz2` for people backing up over dial-up (do those still exist?). The "priority" concept itself is weird — it's not a fallback chain. Just pick gzip as default.

**Warning #1: Default to tar.gz, not bz2. Make bz2 opt-in.**

---

## 6. Restore Workflow Order — Confirm Before Extract

Current flow: `verify → extract → confirmation → stop server → copy back → restart`

You extract a potentially multi-GB archive, THEN ask the user "are you sure?" That's backwards. If the user says no, you just wasted their time and disk I/O.

Correct flow: `verify → confirmation → extract → stop server → copy back → restart`

The hash check (`verify`) is cheap — do it upfront. Then confirm. Then do the expensive extract.

**Warning #2: Move confirmation before extraction in the restore workflow.**

---

## 7. `--db-only` Is Dangerous

Restoring only `evonic.db` without plugin databases (`kanban.db`, `agentapi.db`, `model-router.db`) creates referential inconsistency. If someone created kanban tasks that reference agents, those agent IDs exist in the restored `evonic.db` but the task data in `kanban.db` is from a different point in time.

Either:
- **Remove `--db-only`** — it's a footgun
- **Rename to `--main-db-only`** with a BIG WARNING that plugin DBs will be inconsistent
- **Make it restore all databases together** — `evonic.db` + `shared/data/db/plugins/*.db`

**Warning #3: `--db-only` is an inconsistent-state footgun. Remove or add dire warnings.**

---

## 8. Missing Data

Your design misses several data paths:

### 8a. `/workspace/.env` (not just `shared/.env`)

As shown in section 4, there's a root `.env` with additional secrets. Back up both.

### 8b. `/workspace/plan/`

There are ~300+ plan files at `/workspace/plan/` that represent agent session plans. These are tied to agent work state and should be recoverable.

### 8c. `/workspace/agents/shared/`

There's a shared agent with a `kb/` directory. This may contain shared knowledge base data used across agents.

### 8d. `shared/prompjector.py`

This 33KB file in shared/ is arguably configuration/data rather than source code. If it's modified per-installation, it should be backed up. If it's shipped as part of Evonic and never modified, exclude it.

**Warning #4: Add `/workspace/.env`, `/workspace/plan/`, and `/workspace/agents/shared/` to the backup scope. Decide on `prompjector.py`.**

---

## 9. `--format auto` — Auto Based On What?

What does `auto` decide on? Available disk space? File count? Phase of the moon? If you're going to have an auto mode, you need to specify the heuristic. Otherwise it's just a placeholder that means "the developer hasn't decided yet."

Make the default `tar.gz` and drop `auto` until you have an actual decision algorithm.

**Warning #5: Drop `--format auto` until you can define the heuristic. Default: `tar.gz`.**

---

## 10. What's Actually Good

I've spent 8 sections roasting this. Let me acknowledge what's right:

- **Python stdlib only** — no pip dependencies. This is the correct instinct. `tarfile`, `gzip`, `hashlib`, `shutil`, `tempfile` — all stdlib. Good.
- **Dry-run mode** — essential for restore. Correctly included.
- **Atomic file operations** — mentioned, but needs specification of WHICH operations. `shutil.move` is atomic on same-filesystem. Be explicit.
- **Temp staging → copy → compress → cleanup** — good backup pipeline structure.
- **File naming convention** — `evonic-backup-YYYYMMDD-HHMMSS.ext` is sensible and sortable.
- **CLI-based** — the right approach. This isn't a web UI feature.
- **`--quiet` flag** — good for scripting/cron.
- **Hash integrity check** — the concept is correct, just use SHA-256 instead of MD5.

---

## 11. Additional Recommendations

### 11a. Backup Retention

Not needed for v1, but document the intended strategy. Will old backups be auto-pruned? Is there a `--keep N` flag? This matters for cron-based backup scripts that will otherwise fill the disk.

### 11b. `--verify` for Backups

After creating a backup, the user should be able to verify it without restoring. Add `evonic backup --verify <file>` or `evonic backup --check <file>` that extracts to temp and validates the hash.

### 11c. Partial Restore

Being able to restore just one agent's data (`evonic restore backup.tar.gz --agent linus`) would be valuable for disaster recovery when only one agent's state is corrupted. Not v1, but worth designing for.

### 11d. Pre-backup Health Check

Before backing up, check that the database isn't corrupt: `PRAGMA integrity_check`. If it fails, warn the user that the backup will contain corrupted data.

### 11e. Backup Metadata

Include a manifest inside the archive (e.g., `backup-manifest.json`) with:
- Evonic version at backup time
- Schema version
- Timestamp
- SHA-256 of archive
- List of all files included

This makes it possible to detect version mismatches on restore BEFORE overwriting data.

---

## 12. Summary

| # | Severity | Issue | Fix |
|---|---|---|---|
| 1 | **BLOCKER** | Agent data path wrong (`agents/` vs `shared/agents/`) | List both paths explicitly |
| 2 | **BLOCKER** | MD5 for integrity | Use SHA-256 |
| 3 | **BLOCKER** | No live SQLite backup strategy | Use `connection.backup()` |
| 4 | **BLOCKER** | `.env` encryption undefined, missing root `.env` | Design properly or drop encryption; include both `.env` files |
| W1 | Warning | bz2 as default compression | Default to gzip |
| W2 | Warning | Restore confirms after extraction | Confirm before extraction |
| W3 | Warning | `--db-only` creates inconsistency | Remove or add dire warnings |
| W4 | Warning | Missing `/workspace/plan/`, `agents/shared/` | Add to backup scope |
| W5 | Warning | `--format auto` has no heuristic | Drop or define algorithm |

**Verdict: CONDITIONAL GO.** Fix the 4 blockers, address the 5 warnings, and this is a solid v1 backup design. The core structure is sound — you're just sloppy on the details. And in backup systems, the details are where data lives or dies.

---

*— Linus Torvalds*  
*Robin Syihab's agent.*
