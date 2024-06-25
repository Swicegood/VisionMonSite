#!/bin/bash
set -e

# We're already in /opt/app/vision_monitor_website due to the WORKDIR in Dockerfile
cd /opt/app/vision_monitor_website


# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start Gunicorn
echo "Starting Gunicorn..."
gunicorn config.wsgi:application \
    --name vision_monitor_website \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --log-level=info \
    --access-logfile=- \
    --error-logfile=- &

# Start Nginx
echo "Starting Nginx..."
nginx -g "daemon off; error_log /dev/stderr; pid /tmp/nginx.pid;"