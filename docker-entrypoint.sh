#!/bin/sh
set -e

# Headed Chromium needs a display. Start Xvfb ourselves instead of via xvfb-run,
# whose readiness handshake hangs in containers (never exec'ing the server).
DISPLAY_NUM="${DISPLAY_NUM:-99}"
Xvfb ":${DISPLAY_NUM}" -screen 0 1920x1080x24 -nolisten tcp &
export DISPLAY=":${DISPLAY_NUM}"

# wait for the X socket so the first browser launch has a ready display
for _ in $(seq 1 50); do
    [ -S "/tmp/.X11-unix/X${DISPLAY_NUM}" ] && break
    sleep 0.1
done

exec python3 server.py "$@"
