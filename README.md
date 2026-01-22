# DataOps Dashboard

Enterprise-grade data operations platform for file ingestion, validation, ETL processing, and reporting.

## Features

- **File Upload & Processing**: Support for CSV, Excel, and JSON files
- **Data Validation**: Configurable validation rules with detailed error reporting
- **ETL Pipeline**: Automated data transformation and loading into Oracle database
- **Background Jobs**: Celery-based task queue for async processing
- **Real-time Dashboard**: HTMX-powered responsive UI with live updates
- **Reports & Exports**: Generate and download reports in multiple formats
- **Security**: JWT authentication, RBAC, rate limiting, audit logging
- **CI/CD**: GitHub Actions workflows for testing and deployment

## Tech Stack

- **Backend**: Python 3.12, FastAPI, Celery
- **Database**: Oracle SQL with oracledb driver
- **Cache/Queue**: Redis
- **Frontend**: Jinja2 templates, HTMX, Tailwind CSS
- **Infrastructure**: Docker, Docker Compose
- **CI/CD**: GitHub Actions

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.12+
- Git

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/dataops-dashboard.git
   cd dataops-dashboard
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start services with Docker Compose**
   ```bash
   docker-compose up -d
   ```

4. **Wait for Oracle database to initialize** (first run takes a few minutes)
   ```bash
   docker-compose logs -f oracle
   # Wait for "DATABASE IS READY TO USE!"
   ```

5. **Access the application**
   - Dashboard: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Default login: `admin` / `admin123`

### Local Development (without Docker)

1. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   .venv\Scripts\activate     # Windows
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

3. **Start Redis** (required for Celery)
   ```bash
   docker run -d -p 6379:6379 redis:7-alpine
   ```

4. **Run the API server**
   ```bash
   uvicorn src.api.main:app --reload
   ```

5. **Run Celery worker** (in separate terminal)
   ```bash
   celery -A src.workers.celery_app worker --loglevel=info
   ```

## Project Structure

```
dataops-dashboard/
├── src/
│   ├── api/                 # FastAPI application
│   │   ├── main.py         # Application entry point
│   │   ├── config.py       # Configuration management
│   │   └── routes/         # API endpoints
│   ├── core/               # Core utilities
│   │   ├── database.py     # Database connection
│   │   └── security.py     # Authentication
│   ├── services/           # Business logic
│   │   ├── ingest.py       # File ingestion
│   │   ├── validate.py     # Data validation
│   │   └── load.py         # Database loading
│   └── workers/            # Celery tasks
│       ├── celery_app.py   # Celery configuration
│       └── tasks/          # Task modules
├── templates/              # Jinja2 HTML templates
├── docker/                 # Docker configurations
├── tests/                  # Test suite
├── sample_data/           # Sample data files
└── .github/workflows/     # CI/CD pipelines
```

## API Endpoints

### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/register` - User registration
- `GET /api/auth/me` - Current user info

### Data Management
- `GET /api/data/files` - List uploaded files
- `POST /api/data/upload` - Upload new file
- `GET /api/data/files/{id}` - Get file details
- `POST /api/data/preview` - Preview file contents

### Jobs
- `GET /api/jobs` - List background jobs
- `GET /api/jobs/{id}` - Get job details
- `POST /api/jobs/{id}/cancel` - Cancel running job

### Reports
- `GET /api/reports` - List generated reports
- `POST /api/reports/generate` - Generate new report
- `GET /api/reports/{id}/download` - Download report

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test types
pytest tests/unit/
pytest tests/integration/
```

## Deployment

### Using GitHub Actions

1. Push to `main` branch triggers CI pipeline
2. Create a tag `v*` to trigger CD pipeline
3. Deployment requires configured secrets:
   - `KUBECONFIG_STAGING`
   - `KUBECONFIG_PRODUCTION`
   - `SLACK_WEBHOOK_URL` (optional)

### Manual Deployment

```bash
# Build images
docker build -t dataops-api -f docker/api/Dockerfile .
docker build -t dataops-worker -f docker/worker/Dockerfile .

# Push to registry
docker tag dataops-api your-registry/dataops-api:latest
docker push your-registry/dataops-api:latest
```

## Configuration

Key environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Application secret key | Required |
| `ORACLE_HOST` | Oracle database host | localhost |
| `ORACLE_PORT` | Oracle database port | 1521 |
| `REDIS_URL` | Redis connection URL | redis://localhost:6379/0 |
| `JWT_SECRET_KEY` | JWT signing key | Required |
| `UPLOAD_DIR` | File upload directory | ./uploads |

See `.env.example` for all configuration options.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

MIT License - see LICENSE file for details.
