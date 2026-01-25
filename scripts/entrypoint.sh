#!/bin/bash
set -e

# Support for PUID and PGID
PUID=${PUID:-1000}
PGID=${PGID:-1000}

# Update user/group IDs if they are different from current appuser
if [ "$(id -u appuser)" != "$PUID" ] || [ "$(id -g appuser)" != "$PGID" ]; then
    echo "Processing PUID/PGID: $PUID/$PGID"
    groupmod -o -g "$PGID" appgroup
    usermod -o -u "$PUID" appuser
    
    # Update ownership of data directories
    echo "Updating permissions..."
    chown -R appuser:appgroup /app/downloads
    chown -R appuser:appgroup /app/cookies
fi

# Switch to appuser and run the command
exec gosu appuser "$@"
