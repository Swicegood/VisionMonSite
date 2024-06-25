# Use a more recent Python version
FROM python:3.11-slim-buster

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    vim \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# Set up Nginx
COPY nginx.default /etc/nginx/sites-available/default
RUN ln -sf /dev/stdout /var/log/nginx/access.log \
    && ln -sf /dev/stderr /var/log/nginx/error.log

# Set up application directory
WORKDIR /opt/app

# Copy application files
COPY requirements.txt start-server.sh ./
COPY vision_monitor_website ./vision_monitor_website

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set permissions
RUN chown -R www-data:www-data /opt/app

# Make sure the start script is executable
RUN chmod +x /opt/app/start-server.sh

# Expose port
EXPOSE 8000

# Set stop signal
STOPSIGNAL SIGTERM

# Start the server
CMD ["/opt/app/start-server.sh"]