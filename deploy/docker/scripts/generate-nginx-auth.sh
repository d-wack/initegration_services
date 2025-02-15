#!/bin/bash

# Check if apache2-utils (for htpasswd) is installed
if ! command -v htpasswd &> /dev/null; then
    echo "Installing required packages..."
    apt-get update && apt-get install -y apache2-utils
fi

# Set the correct nginx directory path
NGINX_DIR="/home/ubuntu/slicedhealth/integration_services/deploy/docker/nginx"

# Create auth directory if it doesn't exist
mkdir -p "${NGINX_DIR}/auth"

# Generate basic auth credentials
echo "Generating basic auth credentials..."
read -p "Enter username for admin access [admin]: " USERNAME
USERNAME=${USERNAME:-admin}

# Generate a random password if none is provided
read -s -p "Enter password for admin access (or press enter for random): " PASSWORD
echo
if [ -z "$PASSWORD" ]; then
    PASSWORD=$(openssl rand -base64 12)
    echo "Generated password: $PASSWORD"
fi

# Create or update htpasswd file
htpasswd -bc "${NGINX_DIR}/auth/.htpasswd" "$USERNAME" "$PASSWORD"
chmod 600 "${NGINX_DIR}/auth/.htpasswd"

echo "
Credentials have been generated:
Username: $USERNAME
Password: $PASSWORD

Basic auth file has been generated in:
- ${NGINX_DIR}/auth/.htpasswd

Please save these credentials securely.
"

# Create a credentials file for reference
echo "# Admin Credentials - KEEP SECURE
ADMIN_USERNAME=$USERNAME
ADMIN_PASSWORD=$PASSWORD" > "${NGINX_DIR}/auth/credentials.txt"
chmod 600 "${NGINX_DIR}/auth/credentials.txt" 