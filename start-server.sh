#!/usr/bin/env bash
# start-server.sh

set -e

# Function to wait for a service to be ready
wait_for_service() {
    local service=$1
    local host=$2
    local port=$3
    echo "Waiting for $service to be ready..."
    while ! nc -z $host $port; do
        sleep 1
    done
    echo "$service is ready!"
}

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate --noinput

# Create superuser if environment variables are set
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ] && [ -n "$DJANGO_SUPERUSER_EMAIL" ]; then
    echo "Creating superuser..."
    python manage.py createsuperuser --noinput
fi

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start Gunicorn
echo "Starting Gunicorn..."
gunicorn vision_monitor_website.wsgi:application \
    --name vision_monitor_website \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --log-level=info \
    --log-file=/var/log/gunicorn.log \
    --access-logfile=/var/log/gunicorn-access.log &

# Start Nginx
echo "Starting Nginx..."
nginx -g "daemon off;"