.PHONY: help install migrate runserver celery celery-beat test clean docker-up docker-down

help:
	@echo "Law School - Available commands:"
	@echo "  make install      - Install dependencies"
	@echo "  make migrate      - Run database migrations"
	@echo "  make runserver    - Start Django development server"
	@echo "  make celery       - Start Celery worker"
	@echo "  make celery-beat  - Start Celery beat scheduler"
	@echo "  make test         - Run tests"
	@echo "  make clean        - Clean Python cache files"
	@echo "  make docker-up    - Start Docker containers"
	@echo "  make docker-down  - Stop Docker containers"

install:
	pip install -r requirements.txt

migrate:
	python manage.py migrate

makemigrations:
	python manage.py makemigrations

runserver:
	python manage.py runserver

celery:
	celery -A law_school worker -l info

celery-beat:
	celery -A law_school beat -l info

test:
	python manage.py test

clean:
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

docker-up:
	docker-compose up --build

docker-down:
	docker-compose down

superuser:
	python manage.py createsuperuser
