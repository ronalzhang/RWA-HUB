#!/bin/bash

# Go to the app directory
cd /root/RWA-HUB/

# Activate the virtual environment
source /root/RWA-HUB/venv/bin/activate

# Start the Gunicorn server
# The --env flags are for Gunicorn to pass the environment variables to the app
exec gunicorn --workers 5 --bind 0.0.0.0:9000 app:app
