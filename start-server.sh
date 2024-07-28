#!/bin/bash
set -e

# We're already in /opt/app/vision_monitor_website due to the WORKDIR in Dockerfile

# Set default path for Daphne if not specified
DAPHNE_EXECUTABLE_PATH=${DAPHNE_EXECUTABLE_PATH:-"~/.vision_mon_site/bin/"}

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start Daphne for ASGI support
echo "Starting Daphne..."
${DAPHNE_EXECUTABLE_PATH}daphne -b 0.0.0.0 -p 8001 config.asgi:application &

# Start Redis Listener
echo "Starting Redis Listener..."
python manage.py redis_listener --daemon &

# Start scheduler
echo "Starting Scheduler..."
python manage.py run_scheduler --daemon &

# Start Nginx
echo "Starting Nginx..."
nginx -g "daemon off;"