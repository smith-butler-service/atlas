#!/bin/bash
# ATLAS recovery — restart the monitor daemon if it is not running.
# Idempotent and safe to run from cron, systemd, or by hand.
# Serialized with flock so concurrent runs cannot start duplicate daemons.
#
# F1 fix (2026-11-18, Mission 2): the daemon's stdout/stderr is APPENDED
# to logs/monitor.log (">>"), never truncated (">"), and the existing log
# is rotated aside before a restart — so a crash traceback survives the
# restart that follows it. The daemon's own in-process 1 MB rotation
# (monitor.log -> monitor.log.1) uses the same "9>&-" closes the flock fd
# in the child: without it the daemon inherits fd 9 and holds the lock for
# its whole lifetime, so every later recover.sh run fails flock and exits
# before it can even log a no-op (found 2026-11-18: pid 18910 held
# data/recover.lock via inherited fd 9).
#
# M14 (2026-11-19, Mission 14): retention — the old rotation kept ONE
# backup, so a spontaneous death's traceback was destroyed by the very
# next restart minutes later. Rotation is now timestamped archives,
# newest 10 kept. Scratch mode — ATLAS_SCRATCH_DIR set: operate on a
# scratch ATLAS tree (diagnostics tests 10/11) so they never touch the
# live daemon; the scratch daemon runs with a '--scratch' argument so its
# process can be told apart. Default (unset) behavior is unchanged.
set -u
if [ -n "${ATLAS_SCRATCH_DIR:-}" ]; then
  ATLAS="$ATLAS_SCRATCH_DIR"
  PGREP_PAT='atlas_monitor\.py --scratch$'
  PGREP_PAT_BRACKET='atlas_[m]onitor\.py --scratch$'
  DAEMON_ARGS="--scratch"
  # The daemon resolves its data paths from $HOME (expanduser), so the
  # scratch daemon must run with HOME pointed at the scratch home — else
  # it would write metrics/startup events into the LIVE database.
  # Scratch home is the grandparent of <scratch>/workspace/atlas.
  export HOME="$(dirname "$(dirname "$ATLAS")")"
else
  ATLAS="${HOME:-/home/hatch}/workspace/atlas"
  PGREP_PAT='atlas_monitor\.py$'
  PGREP_PAT_BRACKET='atlas_[m]onitor\.py$'
  DAEMON_ARGS=""
fi
LOCK="$ATLAS/data/recover.lock"
mkdir -p "$ATLAS/data" "$ATLAS/logs"
exec 9>"$LOCK"
flock -n 9 || exit 0
if pgrep -f "$PGREP_PAT" >/dev/null 2>&1; then
  echo "$(date -u +%FT%TZ) recover: no-op daemon already running pid $(pgrep -f "$PGREP_PAT_BRACKET" | head -n 1)" >> "$ATLAS/logs/recover.log"
  exit 0
fi
cd "$ATLAS" || exit 1
# Rotate the existing log aside as a timestamped archive (newest 10 kept)
# instead of truncating it and instead of the old one-backup rotation.
if [ -s logs/monitor.log ]; then
  mv logs/monitor.log "logs/monitor-$(date -u +%Y%m%d-%H%M%S).log"
  ls -t logs/monitor-*.log 2>/dev/null | tail -n +11 | xargs -r rm -f
fi
nohup python3 core/atlas_monitor.py $DAEMON_ARGS >> logs/monitor.log 2>&1 9>&- &
echo "$(date -u +%FT%TZ) recover: restarted atlas_monitor pid $!" >> logs/recover.log
