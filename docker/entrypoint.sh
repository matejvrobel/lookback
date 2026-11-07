#!/bin/sh
set -e

PUID="${PUID:-1000}"
PGID="${PGID:-1000}"

if [ "$(id -u)" != "0" ]; then
    exec "$@"
fi

for dir in /config /cache; do
    mkdir -p "$dir"
    if [ "$(stat -c %u:%g "$dir")" != "$PUID:$PGID" ]; then
        echo "Setting owner of $dir to $PUID:$PGID"
        chown -R "$PUID:$PGID" "$dir"
    fi
done

groups=""
for device in /dev/dri/renderD* /dev/dri/card*; do
    if [ -e "$device" ]; then
        groups="$groups,$(stat -c %g "$device")"
    fi
done

if [ -n "$groups" ]; then
    exec setpriv --reuid="$PUID" --regid="$PGID" --groups="${groups#,}" "$@"
fi
exec setpriv --reuid="$PUID" --regid="$PGID" --clear-groups "$@"
