#!/usr/bin/env bash
#
# Print the PlayFab join code for every running Valheim server.
#
# With CROSSPLAY=true the server is reachable only by join code -- it never
# binds its game port, so there is nothing to connect to by IP and no status
# endpoint to query. The code is assigned by PlayFab when the session
# registers and changes on every restart, so the server log is the only
# place it exists. This scrapes it back out.
#
# Run it on the host that runs the stacks (the repo is cloned there):
#
#     ./join-codes.sh
#
# Or from anywhere, naming an SSH host from your ~/.ssh/config:
#
#     ./join-codes.sh unraid
#     VALHEIM_SSH_HOST=unraid ./join-codes.sh
#
# Every container whose name matches FILTER is picked up, so additional
# valheim-server-* stacks need no change here. Servers that are still
# booting report no code yet rather than being skipped silently.

set -euo pipefail

FILTER=${VALHEIM_FILTER:-valheim}
SSH_HOST=${1:-${VALHEIM_SSH_HOST:-}}

# Feed this same script to a remote bash rather than quoting it inline.
# FILTER is passed explicitly -- the local environment does not cross SSH.
if [ -n "$SSH_HOST" ]; then
    exec ssh "$SSH_HOST" "VALHEIM_FILTER=$(printf '%q' "$FILTER") bash -s" < "$0"
fi

if ! command -v docker >/dev/null 2>&1; then
    echo "docker not found -- run this on the Docker host, or pass an SSH host" >&2
    exit 1
fi

# A reachable CLI is not a reachable daemon: the client is commonly installed
# on a workstation with nothing listening. Fail on that rather than reporting
# it as "no servers running".
if ! containers=$(docker ps --format '{{.Names}}' --filter "name=$FILTER" 2>/dev/null); then
    echo "cannot reach the Docker daemon -- run this on the Docker host," >&2
    echo "or pass an SSH host, e.g. $(basename "$0") unraid" >&2
    exit 1
fi

found=0
for container in $containers; do
    found=1

    # "Session "Midgaard" with join code 808417 and IP 1.2.3.4:2456 is active
    # with 0 player(s)" -- logged at registration and on each join/leave, so
    # the last one is current. Not time-bounded: a long-lived server may have
    # registered days ago.
    line=$(docker logs "$container" 2>&1 | grep -E 'join code [0-9]+ and IP' | tail -1 || true)

    if [ -z "$line" ]; then
        printf '%-16s %s\n' "$container" "(no join code yet)"
        continue
    fi

    world=$(printf '%s' "$line"   | sed -E 's/.*Session "([^"]+)".*/\1/')
    code=$(printf '%s' "$line"    | sed -E 's/.*join code ([0-9]+).*/\1/')
    players=$(printf '%s' "$line" | sed -E 's/.*with ([0-9]+) player.*/\1/')

    printf '%-16s %-8s %s online\n' "$world" "$code" "$players"
done

if [ "$found" = 0 ]; then
    echo "no running containers match name=$FILTER" >&2
    exit 1
fi
