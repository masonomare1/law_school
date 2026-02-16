#!/bin/bash

# Law School Project Setup Script

echo "Setting up Law School project..."

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp env.example .env
    echo "Please edit .env file with your configuration"
fi

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p media staticfiles faiss_indexes logs

# Check if PostgreSQL is running
echo "Checking PostgreSQL..."
if ! pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    echo "Warning: PostgreSQL doesn't seem to be running on localhost:5432"
    echo "Please start PostgreSQL before running migrations"
fi

# Check if Redis is running
echo "Checking Redis..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo "Warning: Redis doesn't seem to be running"
    echo "Please start Redis before running Celery workers"
fi

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your configuration"
echo "2. Make sure PostgreSQL and Redis are running"
echo "3. Run migrations: python manage.py migrate"
echo "4. Create superuser: python manage.py createsuperuser"
echo "5. Start Celery worker: celery -A law_school worker -l info"
echo "6. Start Django server: python manage.py runserver"
