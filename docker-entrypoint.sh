#!/bin/sh
set -eu

# Headed Chromium needs a display. Start Xvfb ourselves instead of via xvfb-run,
# whose readiness handshake hangs in containers (never exec'ing the server).
DISPLAY_NUM="${DISPLAY_NUM:-99}"
DISPLAY_SOCKET="/tmp/.X11-unix/X${DISPLAY_NUM}"
DISPLAY_LOCK="/tmp/.X${DISPLAY_NUM}-lock"

# Docker restarts preserve the container filesystem. Remove stale Xvfb files
# left behind when the previous process was stopped.
rm -f "${DISPLAY_LOCK}" "${DISPLAY_SOCKET}"

Xvfb ":${DISPLAY_NUM}" -screen 0 1920x1080x24 -nolisten tcp &
XVFB_PID=$!
export DISPLAY=":${DISPLAY_NUM}"

# Wait for the X socket and also make sure Xvfb did not exit during startup.
for _ in $(seq 1 50); do
    if [ -S "${DISPLAY_SOCKET}" ] && kill -0 "${XVFB_PID}" 2>/dev/null; then
        exec python3 server.py "$@"
    fi

    if ! kill -0 "${XVFB_PID}" 2>/dev/null; then
        echo "Xvfb failed to start on display ${DISPLAY}." >&2
        wait "${XVFB_PID}" || true
        exit 1
    fi

    sleep 0.1
done

echo "Xvfb did not become ready on display ${DISPLAY}." >&2
kill "${XVFB_PID}" 2>/dev/null || true
exit 1
