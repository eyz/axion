#!/bin/bash
# View discussion.log with colors using Rich
# Usage: ./view_log.sh [follow]

if [ "$1" = "follow" ] || [ "$1" = "-f" ]; then
    # Follow mode - live tail with colors
    tail -f discussion.log | python3 -m rich.console -
else
    # Static view with colors
    python3 -m rich.console discussion.log
fi

