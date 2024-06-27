#!/bin/bash
set -e

# We're already in /opt/app/vision_monitor_website due to the WORKDIR in Dockerfile

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start Daphne for ASGI support
echo "Starting Daphne..."
daphne -b 0.0.0.0 -p 8000 config.asgi:application &

# Start Nginx
# echo "Starting Nginx..."
# nginx -g "daemon off;"