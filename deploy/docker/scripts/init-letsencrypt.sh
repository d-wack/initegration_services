#!/bin/bash

# Handle script interruption
trap 'echo "Script interrupted. Cleaning up..."; docker compose -f "${SCRIPT_DIR}/../docker-compose.infra.yml" down; exit 1' INT

# Enable error handling and debug mode
set -e
set -x

# Domain and paths
domain="slicedhealth.com"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
NGINX_DIR="/home/ubuntu/slicedhealth/integration_services/deploy/docker/nginx"

# Create SSL directory if it doesn't exist
mkdir -p "${NGINX_DIR}/ssl"

# Copy existing certificates directly using Docker volumes
echo "### Copying existing certificates to NGINX directory..."
docker compose -f "${SCRIPT_DIR}/../docker-compose.infra.yml" run --rm \
    -v "${NGINX_DIR}/ssl:/etc/nginx/ssl" \
    -v certbot_conf:/etc/letsencrypt \
    --entrypoint "/bin/sh" certbot \
    -c "cp /etc/letsencrypt/live/$domain/fullchain.pem /etc/nginx/ssl/ && \
        cp /etc/letsencrypt/live/$domain/privkey.pem /etc/nginx/ssl/"

# Check if certificates were copied successfully
if [ -f "${NGINX_DIR}/ssl/fullchain.pem" ] && [ -f "${NGINX_DIR}/ssl/privkey.pem" ]; then
    echo "### Certificates installed successfully!"
    echo "### Updating NGINX configuration to use wildcard certificate..."
    # Create backup of current NGINX config
    cp "${NGINX_DIR}/conf.d/default.conf" "${NGINX_DIR}/conf.d/default.conf.backup"
else
    echo "### Failed to copy certificates"
    exit 1
fi

echo "### Certificate installation complete!"
echo "### Now update your NGINX configuration to use:"
echo "### ssl_certificate /etc/nginx/ssl/fullchain.pem;"
echo "### ssl_certificate_key /etc/nginx/ssl/privkey.pem;"

# Final cleanup
echo "### Cleaning up ..."
docker compose -f "${SCRIPT_DIR}/../docker-compose.infra.yml" down

exit 0 