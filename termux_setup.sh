#!/bin/bash

# Termux setup script for Bodaboda SACCO Registration System

echo "Setting up Bodaboda SACCO Registration System on Termux..."

# Update packages
pkg update -y
pkg upgrade -y

# Install required packages
pkg install -y python python-pip postgresql libjpeg-turbo libpng zlib freetype

# Install Python dependencies
pip install --upgrade pip
pip install flask psycopg2-binary python-dotenv pillow qrcode gunicorn flask-wtf

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

echo "Setup complete on Termux!"
echo "To start the application:"
echo "python app.py"
echo ""
echo "For production with Gunicorn:"
echo "gunicorn wsgi:app --bind 0.0.0.0:5000"
