# Law School - Legal Intelligence Platform

A Retrieval-Augmented Generation (RAG) based legal intelligence platform built with Django, FAISS, and Celery. This system enables ingestion of legal documents (PDF format), transforms them into vector embeddings, and provides citation-aware question-answering capabilities.

## Features

- 📄 **Document Ingestion**: Upload and process legal PDF documents
- 🔍 **Semantic Search**: Vector-based similarity search using FAISS
- 🤖 **AI-Powered Q&A**: Contextual question answering with citation support
- ⚡ **Background Processing**: Asynchronous document processing with Celery
- 🔐 **RESTful API**: Scalable API endpoints for document management and queries

## Technology Stack

- **Backend**: Django 4.2, Django REST Framework
- **Vector Database**: FAISS
- **Task Queue**: Celery with Redis
- **Database**: PostgreSQL
- **Embeddings**: OpenAI / Sentence Transformers
- **PDF Processing**: PyPDF2, PDFMiner

## Prerequisites

- Python 3.9+
- PostgreSQL 12+
- Redis 6+
- Docker and Docker Compose (optional, for containerized deployment)

## Installation

### Option 1: Local Development Setup

1. **Clone the repository** (if applicable) or navigate to the project directory:
   ```bash
   cd Law_school
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Set up PostgreSQL database**:
   ```bash
   # Create database
   createdb law_school_db
   ```

6. **Run migrations**:
   ```bash
   python manage.py migrate
   ```

7. **Create a superuser** (optional):
   ```bash
   python manage.py createsuperuser
   ```

8. **Start Redis** (required for Celery):
   ```bash
   redis-server
   ```

9. **Start Celery worker** (in a separate terminal):
   ```bash
   celery -A law_school worker -l info
   ```

10. **Start Celery beat** (optional, for scheduled tasks, in another terminal):
    ```bash
    celery -A law_school beat -l info
    ```

11. **Start the Django development server**:
    ```bash
    python manage.py runserver
    ```

### Option 2: Docker Setup

1. **Create `.env` file**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Build and start containers**:
   ```bash
   docker-compose up --build
   ```

3. **Run migrations** (first time only):
   ```bash
   docker-compose exec web python manage.py migrate
   ```

4. **Create superuser** (optional):
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

The application will be available at `http://localhost:8000`

## Environment Variables

Key environment variables (see `.env.example` for full list):

- `SECRET_KEY`: Django secret key
- `DEBUG`: Debug mode (True/False)
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`: PostgreSQL configuration
- `REDIS_HOST`, `REDIS_PORT`: Redis configuration
- `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`: Celery configuration
- `OPENAI_API_KEY`: OpenAI API key (optional)
- `EMBEDDING_MODEL`: Embedding model name
- `FAISS_INDEX_PATH`: Path to store FAISS indexes
- `FAISS_INDEX_DIMENSION`: Dimension of embeddings (default: 384)

## API Endpoints

### Document Upload
```
POST /api/v1/documents/upload/
Content-Type: multipart/form-data

Body:
- file: PDF file

Response:
{
  "status": "success",
  "document_id": "uuid",
  "chunks_indexed": 152
}
```

### List Documents
```
GET /api/v1/documents/

Response:
[
  {
    "id": "uuid",
    "name": "document.pdf",
    "status": "completed",
    "chunks_indexed": 152,
    ...
  }
]
```

### Document Detail
```
GET /api/v1/documents/<document_id>/

Response:
{
  "id": "uuid",
  "name": "document.pdf",
  "status": "completed",
  ...
}
```

### Query
```
POST /api/v1/query/
Content-Type: application/json

Body:
{
  "query": "What is the penalty for..."
}

Response:
{
  "answer": "According to Section 45 of the Act...",
  "citations": [
    {
      "document_name": "Criminal Law Act",
      "section": "Section 45",
      "page": 12
    }
  ],
  "confidence_score": 0.87
}
```

## Project Structure

```
Law_school/
├── law_school/          # Main Django project
│   ├── settings.py      # Django settings
│   ├── urls.py          # URL configuration
│   ├── celery.py        # Celery configuration
│   └── wsgi.py          # WSGI configuration
├── api/                 # API app
│   ├── views.py         # Query API views
│   └── urls.py          # API URL routing
├── documents/           # Documents app
│   ├── models.py        # Document models
│   ├── views.py         # Document upload views
│   ├── serializers.py   # DRF serializers
│   ├── tasks.py         # Celery tasks
│   └── admin.py         # Admin configuration
├── manage.py            # Django management script
├── requirements.txt     # Python dependencies
├── docker-compose.yml   # Docker Compose configuration
├── Dockerfile           # Docker image definition
└── README.md           # This file
```

## Development

### Running Tests
```bash
python manage.py test
```

### Accessing Admin Panel
Navigate to `http://localhost:8000/admin/` and login with your superuser credentials.

### Monitoring Celery Tasks
You can monitor Celery tasks using Flower (optional):
```bash
pip install flower
celery -A law_school flower
```

## Next Steps

The following features are planned for implementation:

1. PDF text extraction and preprocessing
2. Document chunking strategies for legal texts
3. Embedding generation (OpenAI or Sentence Transformers)
4. FAISS index creation and management
5. Query processing and RAG pipeline
6. Citation extraction and formatting
7. Rate limiting and authentication
8. Logging and monitoring

## License

Mason Omare Designs

## Contributing

Mason Omare
