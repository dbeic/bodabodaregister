#!/bin/bash

# Setup script for Bodaboda SACCO Registration System

echo "Setting up Bodaboda SACCO Registration System..."

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
mkdir -p static/uploads static/badges static/qr
mkdir -p templates utils

# Set permissions
chmod -R 755 static/uploads static/badges static/qr

# Copy .env.example to .env if it doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Please update .env file with your database credentials"
fi

echo "Setup complete!"
echo "To start the application:"
echo "source venv/bin/activate"
echo "python app.py"
echo ""
echo "For production with Gunicorn:"
echo "gunicorn wsgi:app"
