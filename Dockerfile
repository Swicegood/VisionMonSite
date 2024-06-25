# Use a more recent Python version
FROM python:3.11-slim-buster

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Set up Nginx
COPY nginx.default /etc/nginx/sites-available/default
RUN ln -sf /dev/stdout /var/log/nginx/access.log \
    && ln -sf /dev/stderr /var/log/nginx/error.log

# Create necessary directories and set permissions
RUN mkdir -p /var/lib/nginx/body /var/lib/nginx/fastcgi \
    && chown -R www-data:www-data /var/lib/nginx \
    && chown -R www-data:www-data /var/log/nginx \
    && chown -R www-data:www-data /var/lib/nginx

# Set up application directory
WORKDIR /opt/app/vision_monitor_website

# Copy application files
COPY requirements.txt .
COPY start-server.sh .
COPY manage.py .
COPY ./vision_monitor_website/config ./config
COPY ./vision_monitor_website/monitor ./monitor
COPY ./vision_monitor_website/templates ./templates
COPY ./vision_monitor_website/templates ./static

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Make sure the start script is executable
RUN chmod +x /opt/app/vision_monitor_website/start-server.sh

# Set permissions for the application directory
RUN chown -R www-data:www-data /opt/app

# Expose port
EXPOSE 8000

# Set the user to www-data
USER www-data

# Start the server
CMD ["/opt/app/vision_monitor_website/start-server.sh"]