# DataOps Dashboard - Master Level Project Plan

## Overview
Build an Enterprise Data Platform with:
- Data ingestion (CSV, JSON, API)
- Oracle Database storage
- Data validation pipeline
- Web dashboard for monitoring
- Scheduled jobs and reports

---

# 1. HIGH-LEVEL ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATAOPS DASHBOARD                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐                │
│  │   NGINX      │     │   FASTAPI    │     │   CELERY     │                │
│  │   (Proxy)    │────▶│   (API)      │────▶│   (Workers)  │                │
│  │   Port 80    │     │   Port 8000  │     │              │                │
│  └──────────────┘     └──────┬───────┘     └──────┬───────┘                │
│                              │                     │                        │
│                              ▼                     ▼                        │
│                       ┌──────────────┐     ┌──────────────┐                │
│                       │    REDIS     │     │   ORACLE DB  │                │
│                       │   (Queue +   │     │   (Data +    │                │
│                       │    Cache)    │     │    Config)   │                │
│                       │   Port 6379  │     │   Port 1521  │                │
│                       └──────────────┘     └──────────────┘                │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                           DATA FLOW                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  [CSV/JSON Files]──┐                                                        │
│                    │     ┌─────────┐     ┌─────────┐     ┌─────────┐       │
│  [External API]────┼────▶│ INGEST  │────▶│VALIDATE │────▶│  LOAD   │       │
│                    │     │ Service │     │ Service │     │ Service │       │
│  [Upload via UI]───┘     └─────────┘     └────┬────┘     └────┬────┘       │
│                                               │               │             │
│                                               ▼               ▼             │
│                                         ┌─────────┐     ┌─────────┐        │
│                                         │ ERROR   │     │  MAIN   │        │
│                                         │ TABLES  │     │ TABLES  │        │
│                                         └─────────┘     └─────────┘        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Service Responsibilities

| Service | Technology | Purpose |
|---------|------------|---------|
| nginx | Nginx 1.25 | Reverse proxy, SSL, static files |
| api | FastAPI + Uvicorn | REST API, authentication, web pages |
| worker | Celery | Background jobs, ETL, scheduled tasks |
| redis | Redis 7 | Task queue, caching, rate limiting |
| oracle | Oracle XE 21c | Main database, data storage |
| prometheus | Prometheus | Metrics collection (optional) |

---

# 2. REPOSITORY FOLDER STRUCTURE

```
dataops-dashboard/
├── .github/
│   └── workflows/
│       ├── ci.yml                    # Lint, test, build
│       └── cd.yml                    # Deploy to server
├── docker/
│   ├── api/
│   │   └── Dockerfile               # API container
│   ├── worker/
│   │   └── Dockerfile               # Celery worker container
│   ├── nginx/
│   │   ├── Dockerfile               # Nginx container
│   │   └── nginx.conf               # Nginx configuration
│   └── oracle/
│       └── init/
│           └── 01_init.sql          # Initial DB setup
├── migrations/
│   ├── versions/
│   │   └── 001_initial_schema.sql   # First migration
│   └── migrate.py                   # Migration runner
├── scripts/
│   ├── seed_data.py                 # Load sample data
│   ├── backup_db.sh                 # Database backup
│   └── deploy.sh                    # Deployment script
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app
│   │   ├── config.py                # Settings
│   │   ├── dependencies.py          # DI
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── auth.py              # Login, logout
│   │       ├── data.py              # Data endpoints
│   │       ├── jobs.py              # Job management
│   │       ├── reports.py           # Reports
│   │       └── pages.py             # HTML pages
│   ├── core/
│   │   ├── __init__.py
│   │   ├── database.py              # Oracle connection
│   │   ├── security.py              # JWT, hashing
│   │   ├── logging.py               # Structured logs
│   │   └── exceptions.py            # Custom errors
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py                  # User model
│   │   ├── data_file.py             # Data file model
│   │   ├── job.py                   # Job model
│   │   └── audit.py                 # Audit log model
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── user.py                  # User schemas
│   │   ├── data.py                  # Data schemas
│   │   └── job.py                   # Job schemas
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ingest.py                # File ingestion
│   │   ├── validate.py              # Data validation
│   │   ├── load.py                  # Load to Oracle
│   │   ├── report.py                # Generate reports
│   │   └── external_api.py          # Fetch from APIs
│   ├── workers/
│   │   ├── __init__.py
│   │   ├── celery_app.py            # Celery config
│   │   └── tasks/
│   │       ├── __init__.py
│   │       ├── etl_tasks.py         # ETL jobs
│   │       ├── report_tasks.py      # Report jobs
│   │       └── cleanup_tasks.py     # Cleanup jobs
│   └── templates/
│       ├── base.html                # Base template
│       ├── login.html               # Login page
│       ├── dashboard.html           # Main dashboard
│       ├── data_files.html          # File list
│       ├── upload.html              # Upload page
│       ├── jobs.html                # Jobs list
│       ├── reports.html             # Reports page
│       └── components/
│           ├── navbar.html          # Navigation
│           ├── table.html           # Data table
│           └── chart.html           # Chart component
├── static/
│   ├── css/
│   │   └── app.css                  # Custom styles
│   └── js/
│       └── app.js                   # Custom scripts
├── tests/
│   ├── __init__.py
│   ├── conftest.py                  # Test fixtures
│   ├── test_api/
│   │   ├── test_auth.py
│   │   ├── test_data.py
│   │   └── test_jobs.py
│   ├── test_services/
│   │   ├── test_ingest.py
│   │   ├── test_validate.py
│   │   └── test_load.py
│   └── test_integration/
│       └── test_etl_pipeline.py
├── sample_data/
│   ├── customers.csv                # Sample CSV
│   ├── orders.json                  # Sample JSON
│   └── products.csv                 # Sample CSV
├── .env.example                     # Environment template
├── .gitignore
├── docker-compose.yml               # Dev compose
├── docker-compose.prod.yml          # Prod compose
├── pyproject.toml                   # Python config
├── requirements.txt                 # Dependencies
├── requirements-dev.txt             # Dev dependencies
└── README.md                        # Documentation
```

---

# 3. FILE LIST WITH PURPOSE

## Root Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Run all services locally for development |
| `docker-compose.prod.yml` | Production configuration with replicas |
| `pyproject.toml` | Python project config (ruff, pytest, mypy) |
| `requirements.txt` | Production dependencies |
| `requirements-dev.txt` | Test and dev dependencies |
| `.env.example` | Template for environment variables |
| `.gitignore` | Ignore build files, secrets, venv |
| `README.md` | Setup instructions, usage guide |

## Source Files (src/)

| File | Purpose |
|------|---------|
| `api/main.py` | FastAPI application entry point |
| `api/config.py` | Load settings from environment |
| `api/dependencies.py` | Dependency injection (DB, auth) |
| `api/routes/auth.py` | Login, logout, token refresh |
| `api/routes/data.py` | Upload, list, delete data files |
| `api/routes/jobs.py` | Start, stop, list jobs |
| `api/routes/reports.py` | Generate and download reports |
| `api/routes/pages.py` | Render HTML pages |
| `core/database.py` | Oracle connection pool |
| `core/security.py` | JWT encode/decode, password hash |
| `core/logging.py` | JSON structured logging |
| `core/exceptions.py` | Custom HTTP exceptions |
| `models/user.py` | User table model |
| `models/data_file.py` | Data file metadata model |
| `models/job.py` | Job run history model |
| `models/audit.py` | Audit log model |
| `schemas/user.py` | Pydantic schemas for users |
| `schemas/data.py` | Pydantic schemas for data |
| `schemas/job.py` | Pydantic schemas for jobs |
| `services/ingest.py` | Parse CSV/JSON files |
| `services/validate.py` | Check data rules, find errors |
| `services/load.py` | Insert data into Oracle |
| `services/report.py` | Build reports from data |
| `services/external_api.py` | Fetch data from external APIs |
| `workers/celery_app.py` | Celery configuration |
| `workers/tasks/etl_tasks.py` | Background ETL jobs |
| `workers/tasks/report_tasks.py` | Report generation jobs |
| `workers/tasks/cleanup_tasks.py` | Delete old files, logs |

## Docker Files

| File | Purpose |
|------|---------|
| `docker/api/Dockerfile` | Build API image |
| `docker/worker/Dockerfile` | Build worker image |
| `docker/nginx/Dockerfile` | Build nginx image |
| `docker/nginx/nginx.conf` | Proxy and SSL settings |
| `docker/oracle/init/01_init.sql` | Create users, grants |

## CI/CD Files

| File | Purpose |
|------|---------|
| `.github/workflows/ci.yml` | Run tests on push/PR |
| `.github/workflows/cd.yml` | Deploy on merge to main |

## Test Files

| File | Purpose |
|------|---------|
| `tests/conftest.py` | Shared fixtures (DB, client) |
| `tests/test_api/test_auth.py` | Test login, token |
| `tests/test_api/test_data.py` | Test upload, list |
| `tests/test_api/test_jobs.py` | Test job start, status |
| `tests/test_services/test_ingest.py` | Test file parsing |
| `tests/test_services/test_validate.py` | Test validation rules |
| `tests/test_services/test_load.py` | Test Oracle insert |
| `tests/test_integration/test_etl_pipeline.py` | Full ETL test |

---

# 4. STEP-BY-STEP MILESTONES

## Milestone 1: Project Setup (Day 1-2)
**Goal: Empty project that runs**

- [ ] Create GitHub repository
- [ ] Create folder structure
- [ ] Write `pyproject.toml` with dependencies
- [ ] Write `requirements.txt`
- [ ] Write `.gitignore`
- [ ] Write `.env.example`
- [ ] Create basic `docker-compose.yml` with Oracle + Redis
- [ ] Test: `docker-compose up` starts Oracle

**Commands:**
```bash
mkdir dataops-dashboard && cd dataops-dashboard
git init
python -m venv venv
source venv/bin/activate  # Linux
pip install fastapi uvicorn oracledb celery redis pydantic
pip freeze > requirements.txt
docker-compose up -d
```

**Success: Oracle container running, can connect with SQL client**

---

## Milestone 2: Database Schema (Day 3-4)
**Goal: All tables created in Oracle**

- [ ] Write `01_init.sql` (users, grants)
- [ ] Write migration `001_initial_schema.sql`
- [ ] Create all tables (see section 5)
- [ ] Create indexes
- [ ] Create validation stored procedure
- [ ] Write `migrate.py` script
- [ ] Test: Run migration, tables exist

**Commands:**
```bash
docker exec -it oracle sqlplus system/password@XEPDB1
@/opt/oracle/scripts/001_initial_schema.sql
```

**Success: All tables visible in Oracle, can insert test row**

---

## Milestone 3: Core API (Day 5-7)
**Goal: FastAPI running with basic endpoints**

- [ ] Write `src/api/main.py`
- [ ] Write `src/api/config.py`
- [ ] Write `src/core/database.py` (Oracle pool)
- [ ] Write `src/core/security.py` (JWT)
- [ ] Write `src/api/routes/auth.py` (login)
- [ ] Write `docker/api/Dockerfile`
- [ ] Add API to `docker-compose.yml`
- [ ] Test: Can login, get JWT token

**Commands:**
```bash
docker-compose up -d api
curl -X POST http://localhost:8000/api/auth/login \
  -d '{"username":"admin","password":"admin"}'
```

**Success: Get JWT token in response**

---

## Milestone 4: Data Ingestion (Day 8-10)
**Goal: Upload CSV/JSON, parse, store metadata**

- [ ] Write `src/services/ingest.py`
- [ ] Write `src/api/routes/data.py`
- [ ] Write `src/schemas/data.py`
- [ ] Write `src/models/data_file.py`
- [ ] Add upload endpoint
- [ ] Add list files endpoint
- [ ] Test: Upload CSV, see in database

**Commands:**
```bash
curl -X POST http://localhost:8000/api/data/upload \
  -H "Authorization: Bearer TOKEN" \
  -F "file=@sample_data/customers.csv"
```

**Success: File metadata saved, file stored on disk**

---

## Milestone 5: Data Validation & Loading (Day 11-14)
**Goal: Validate data, load to Oracle, errors to error table**

- [ ] Write `src/services/validate.py`
- [ ] Write `src/services/load.py`
- [ ] Create validation rules (JSON config)
- [ ] Implement Oracle stored procedure call
- [ ] Add process endpoint
- [ ] Test: Good rows in main table, bad rows in error table

**Commands:**
```bash
curl -X POST http://localhost:8000/api/data/process/1 \
  -H "Authorization: Bearer TOKEN"
```

**Success: Data in CUSTOMERS table, errors in DATA_ERRORS table**

---

## Milestone 6: Celery Workers (Day 15-17)
**Goal: Background jobs working**

- [ ] Write `src/workers/celery_app.py`
- [ ] Write `src/workers/tasks/etl_tasks.py`
- [ ] Write `docker/worker/Dockerfile`
- [ ] Add worker to `docker-compose.yml`
- [ ] Add job start endpoint
- [ ] Add job status endpoint
- [ ] Test: Start job, check status, see result

**Commands:**
```bash
docker-compose up -d worker
curl -X POST http://localhost:8000/api/jobs/start/daily_etl \
  -H "Authorization: Bearer TOKEN"
```

**Success: Job runs in background, status shows "completed"**

---

## Milestone 7: Web UI - Basic (Day 18-21)
**Goal: Login page and dashboard working**

- [ ] Write `src/templates/base.html`
- [ ] Write `src/templates/login.html`
- [ ] Write `src/templates/dashboard.html`
- [ ] Write `src/api/routes/pages.py`
- [ ] Add Tailwind CSS
- [ ] Add HTMX for interactions
- [ ] Test: Login via browser, see dashboard

**Commands:**
```bash
# Open browser to http://localhost:8000
# Login with admin/admin
# See dashboard with stats
```

**Success: Can login, see dashboard with data counts**

---

## Milestone 8: Web UI - Data Pages (Day 22-25)
**Goal: Upload, view, filter data in UI**

- [ ] Write `src/templates/data_files.html`
- [ ] Write `src/templates/upload.html`
- [ ] Add HTMX file upload
- [ ] Add data table with pagination
- [ ] Add filters (date, status)
- [ ] Add export button (CSV download)
- [ ] Test: Full data workflow in browser

**Success: Upload file, see processing, view data, export**

---

## Milestone 9: Reports & Scheduling (Day 26-28)
**Goal: Generate reports, schedule jobs**

- [ ] Write `src/services/report.py`
- [ ] Write `src/workers/tasks/report_tasks.py`
- [ ] Write `src/templates/reports.html`
- [ ] Add Celery Beat for scheduling
- [ ] Add weekly report job
- [ ] Test: Generate report, download PDF/Excel

**Commands:**
```bash
# Add to docker-compose.yml: celery beat service
docker-compose up -d beat
```

**Success: Report generates weekly, can download from UI**

---

## Milestone 10: Security & Audit (Day 29-31)
**Goal: RBAC, audit logs, rate limiting**

- [ ] Add roles (admin, analyst, viewer)
- [ ] Add role checks to endpoints
- [ ] Write `src/models/audit.py`
- [ ] Log all actions to AUDIT_LOG table
- [ ] Add rate limiting with Redis
- [ ] Test: Viewer cannot delete, all actions logged

**Success: Roles enforced, audit log shows all actions**

---

## Milestone 11: Testing (Day 32-35)
**Goal: 80%+ test coverage**

- [ ] Write `tests/conftest.py` (fixtures)
- [ ] Write all unit tests
- [ ] Write integration tests with Oracle
- [ ] Add pytest-cov for coverage
- [ ] Fix bugs found by tests
- [ ] Test: All tests pass, coverage > 80%

**Commands:**
```bash
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

**Success: All tests green, coverage report shows 80%+**

---

## Milestone 12: CI/CD Pipeline (Day 36-38)
**Goal: Automated test and deploy**

- [ ] Write `.github/workflows/ci.yml`
- [ ] Write `.github/workflows/cd.yml`
- [ ] Set up GitHub secrets
- [ ] Set up Docker Hub registry
- [ ] Set up Linux server
- [ ] Test: Push triggers CI, merge triggers CD

**Success: Code pushed → tests run → image built → deployed**

---

## Milestone 13: Production Ready (Day 39-42)
**Goal: Production deployment working**

- [ ] Write `docker-compose.prod.yml`
- [ ] Write `docker/nginx/nginx.conf` (SSL)
- [ ] Add health checks
- [ ] Add Prometheus metrics (optional)
- [ ] Write `scripts/backup_db.sh`
- [ ] Document everything in README
- [ ] Test: Full production deployment

**Success: App running on server with HTTPS**

---

# 5. ORACLE SQL DESIGN

## 5.1 Table List

### USERS
```sql
CREATE TABLE users (
    id              NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username        VARCHAR2(50) NOT NULL UNIQUE,
    email           VARCHAR2(100) NOT NULL UNIQUE,
    password_hash   VARCHAR2(255) NOT NULL,
    role            VARCHAR2(20) DEFAULT 'viewer' NOT NULL,
    is_active       NUMBER(1) DEFAULT 1 NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_role CHECK (role IN ('admin', 'analyst', 'viewer'))
);
```

### DATA_FILES
```sql
CREATE TABLE data_files (
    id              NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    filename        VARCHAR2(255) NOT NULL,
    original_name   VARCHAR2(255) NOT NULL,
    file_type       VARCHAR2(10) NOT NULL,
    file_size       NUMBER NOT NULL,
    row_count       NUMBER,
    status          VARCHAR2(20) DEFAULT 'uploaded' NOT NULL,
    uploaded_by     NUMBER NOT NULL,
    uploaded_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at    TIMESTAMP,
    error_message   VARCHAR2(1000),
    CONSTRAINT fk_uploaded_by FOREIGN KEY (uploaded_by) REFERENCES users(id),
    CONSTRAINT chk_status CHECK (status IN ('uploaded', 'processing', 'completed', 'failed'))
);
```

### CUSTOMERS (Example data table)
```sql
CREATE TABLE customers (
    id              NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_code   VARCHAR2(20) NOT NULL UNIQUE,
    name            VARCHAR2(100) NOT NULL,
    email           VARCHAR2(100),
    phone           VARCHAR2(20),
    country         VARCHAR2(50),
    segment         VARCHAR2(50),
    credit_limit    NUMBER(12,2),
    is_active       NUMBER(1) DEFAULT 1,
    source_file_id  NUMBER,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_source_file FOREIGN KEY (source_file_id) REFERENCES data_files(id)
);
```

### ORDERS (Example data table)
```sql
CREATE TABLE orders (
    id              NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_number    VARCHAR2(20) NOT NULL UNIQUE,
    customer_id     NUMBER NOT NULL,
    order_date      DATE NOT NULL,
    total_amount    NUMBER(12,2) NOT NULL,
    status          VARCHAR2(20) DEFAULT 'pending',
    source_file_id  NUMBER,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_order_customer FOREIGN KEY (customer_id) REFERENCES customers(id),
    CONSTRAINT fk_order_source FOREIGN KEY (source_file_id) REFERENCES data_files(id)
);
```

### DATA_ERRORS
```sql
CREATE TABLE data_errors (
    id              NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_file_id  NUMBER NOT NULL,
    row_number      NUMBER NOT NULL,
    raw_data        CLOB,
    error_type      VARCHAR2(50) NOT NULL,
    error_message   VARCHAR2(1000) NOT NULL,
    field_name      VARCHAR2(50),
    field_value     VARCHAR2(500),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_error_file FOREIGN KEY (source_file_id) REFERENCES data_files(id)
);
```

### JOBS
```sql
CREATE TABLE jobs (
    id              NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    job_name        VARCHAR2(100) NOT NULL,
    job_type        VARCHAR2(50) NOT NULL,
    status          VARCHAR2(20) DEFAULT 'pending' NOT NULL,
    started_by      NUMBER,
    started_at      TIMESTAMP,
    completed_at    TIMESTAMP,
    parameters      CLOB,
    result          CLOB,
    error_message   VARCHAR2(2000),
    CONSTRAINT fk_started_by FOREIGN KEY (started_by) REFERENCES users(id),
    CONSTRAINT chk_job_status CHECK (status IN ('pending', 'running', 'completed', 'failed'))
);
```

### AUDIT_LOG
```sql
CREATE TABLE audit_log (
    id              NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id         NUMBER,
    action          VARCHAR2(50) NOT NULL,
    resource_type   VARCHAR2(50),
    resource_id     NUMBER,
    old_value       CLOB,
    new_value       CLOB,
    ip_address      VARCHAR2(45),
    user_agent      VARCHAR2(500),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### REPORTS
```sql
CREATE TABLE reports (
    id              NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    report_name     VARCHAR2(100) NOT NULL,
    report_type     VARCHAR2(50) NOT NULL,
    parameters      CLOB,
    file_path       VARCHAR2(500),
    generated_by    NUMBER,
    generated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_generated_by FOREIGN KEY (generated_by) REFERENCES users(id)
);
```

### CONFIG
```sql
CREATE TABLE config (
    id              NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    config_key      VARCHAR2(100) NOT NULL UNIQUE,
    config_value    VARCHAR2(1000),
    description     VARCHAR2(500),
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 5.2 Indexes

```sql
-- Users
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);

-- Data Files
CREATE INDEX idx_files_status ON data_files(status);
CREATE INDEX idx_files_uploaded_by ON data_files(uploaded_by);
CREATE INDEX idx_files_uploaded_at ON data_files(uploaded_at);

-- Customers
CREATE INDEX idx_customers_code ON customers(customer_code);
CREATE INDEX idx_customers_country ON customers(country);
CREATE INDEX idx_customers_segment ON customers(segment);

-- Orders
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_date ON orders(order_date);
CREATE INDEX idx_orders_status ON orders(status);

-- Data Errors
CREATE INDEX idx_errors_file ON data_errors(source_file_id);
CREATE INDEX idx_errors_type ON data_errors(error_type);

-- Jobs
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_type ON jobs(job_type);

-- Audit Log
CREATE INDEX idx_audit_user ON audit_log(user_id);
CREATE INDEX idx_audit_action ON audit_log(action);
CREATE INDEX idx_audit_created ON audit_log(created_at);
```

## 5.3 Example Queries

### Daily Summary Report
```sql
SELECT
    TRUNC(uploaded_at) as upload_date,
    COUNT(*) as total_files,
    SUM(row_count) as total_rows,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
FROM data_files
WHERE uploaded_at >= TRUNC(SYSDATE) - 7
GROUP BY TRUNC(uploaded_at)
ORDER BY upload_date DESC;
```

### Error Summary by Type
```sql
SELECT
    error_type,
    COUNT(*) as error_count,
    COUNT(DISTINCT source_file_id) as affected_files
FROM data_errors
WHERE created_at >= TRUNC(SYSDATE) - 30
GROUP BY error_type
ORDER BY error_count DESC;
```

### Customer Segment Analysis
```sql
SELECT
    segment,
    COUNT(*) as customer_count,
    AVG(credit_limit) as avg_credit_limit,
    SUM(credit_limit) as total_credit
FROM customers
WHERE is_active = 1
GROUP BY segment
ORDER BY customer_count DESC;
```

### Top Customers by Orders
```sql
SELECT
    c.customer_code,
    c.name,
    COUNT(o.id) as order_count,
    SUM(o.total_amount) as total_spent
FROM customers c
JOIN orders o ON c.id = o.customer_id
WHERE o.order_date >= ADD_MONTHS(SYSDATE, -12)
GROUP BY c.customer_code, c.name
ORDER BY total_spent DESC
FETCH FIRST 10 ROWS ONLY;
```

## 5.4 Stored Procedure: Validate and Load Data

```sql
CREATE OR REPLACE PACKAGE pkg_data_loader AS
    -- Types
    TYPE t_error_rec IS RECORD (
        row_number    NUMBER,
        error_type    VARCHAR2(50),
        error_message VARCHAR2(1000),
        field_name    VARCHAR2(50),
        field_value   VARCHAR2(500)
    );
    TYPE t_error_tab IS TABLE OF t_error_rec;

    -- Procedures
    PROCEDURE process_customer_file(
        p_file_id     IN NUMBER,
        p_rows_loaded OUT NUMBER,
        p_rows_error  OUT NUMBER
    );

    PROCEDURE log_error(
        p_file_id      IN NUMBER,
        p_row_number   IN NUMBER,
        p_error_type   IN VARCHAR2,
        p_error_msg    IN VARCHAR2,
        p_field_name   IN VARCHAR2 DEFAULT NULL,
        p_field_value  IN VARCHAR2 DEFAULT NULL
    );
END pkg_data_loader;
/

CREATE OR REPLACE PACKAGE BODY pkg_data_loader AS

    PROCEDURE log_error(
        p_file_id      IN NUMBER,
        p_row_number   IN NUMBER,
        p_error_type   IN VARCHAR2,
        p_error_msg    IN VARCHAR2,
        p_field_name   IN VARCHAR2 DEFAULT NULL,
        p_field_value  IN VARCHAR2 DEFAULT NULL
    ) IS
        PRAGMA AUTONOMOUS_TRANSACTION;
    BEGIN
        INSERT INTO data_errors (
            source_file_id, row_number, error_type,
            error_message, field_name, field_value
        ) VALUES (
            p_file_id, p_row_number, p_error_type,
            p_error_msg, p_field_name, p_field_value
        );
        COMMIT;
    END log_error;

    PROCEDURE process_customer_file(
        p_file_id     IN NUMBER,
        p_rows_loaded OUT NUMBER,
        p_rows_error  OUT NUMBER
    ) IS
        v_row_count NUMBER := 0;
        v_err_count NUMBER := 0;
    BEGIN
        -- Update file status
        UPDATE data_files
        SET status = 'processing'
        WHERE id = p_file_id;
        COMMIT;

        -- Process staging data (assume loaded to staging table)
        FOR rec IN (
            SELECT rownum as rn, s.*
            FROM staging_customers s
            WHERE file_id = p_file_id
        ) LOOP
            BEGIN
                -- Validation rules
                IF rec.customer_code IS NULL THEN
                    log_error(p_file_id, rec.rn, 'REQUIRED',
                              'Customer code is required', 'customer_code', NULL);
                    v_err_count := v_err_count + 1;
                    CONTINUE;
                END IF;

                IF rec.email IS NOT NULL AND
                   NOT REGEXP_LIKE(rec.email, '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$') THEN
                    log_error(p_file_id, rec.rn, 'FORMAT',
                              'Invalid email format', 'email', rec.email);
                    v_err_count := v_err_count + 1;
                    CONTINUE;
                END IF;

                IF rec.credit_limit < 0 THEN
                    log_error(p_file_id, rec.rn, 'RANGE',
                              'Credit limit cannot be negative', 'credit_limit',
                              TO_CHAR(rec.credit_limit));
                    v_err_count := v_err_count + 1;
                    CONTINUE;
                END IF;

                -- Insert valid row
                INSERT INTO customers (
                    customer_code, name, email, phone,
                    country, segment, credit_limit, source_file_id
                ) VALUES (
                    rec.customer_code, rec.name, rec.email, rec.phone,
                    rec.country, rec.segment, rec.credit_limit, p_file_id
                );

                v_row_count := v_row_count + 1;

            EXCEPTION
                WHEN DUP_VAL_ON_INDEX THEN
                    log_error(p_file_id, rec.rn, 'DUPLICATE',
                              'Customer code already exists', 'customer_code',
                              rec.customer_code);
                    v_err_count := v_err_count + 1;
                WHEN OTHERS THEN
                    log_error(p_file_id, rec.rn, 'UNKNOWN',
                              SQLERRM, NULL, NULL);
                    v_err_count := v_err_count + 1;
            END;
        END LOOP;

        -- Update file status
        UPDATE data_files
        SET status = CASE WHEN v_err_count = 0 THEN 'completed' ELSE 'completed' END,
            row_count = v_row_count,
            processed_at = CURRENT_TIMESTAMP
        WHERE id = p_file_id;

        COMMIT;

        p_rows_loaded := v_row_count;
        p_rows_error := v_err_count;

    EXCEPTION
        WHEN OTHERS THEN
            UPDATE data_files
            SET status = 'failed',
                error_message = SQLERRM
            WHERE id = p_file_id;
            COMMIT;
            RAISE;
    END process_customer_file;

END pkg_data_loader;
/
```

---

# 6. API DESIGN

## 6.1 Endpoints List

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | Get JWT token |
| POST | `/api/auth/logout` | Invalidate token |
| POST | `/api/auth/refresh` | Refresh token |
| GET | `/api/auth/me` | Get current user |

### Users (Admin only)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/users` | List all users |
| POST | `/api/users` | Create user |
| GET | `/api/users/{id}` | Get user by ID |
| PUT | `/api/users/{id}` | Update user |
| DELETE | `/api/users/{id}` | Delete user |

### Data Files
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/data/files` | List files (with filters) |
| POST | `/api/data/upload` | Upload file |
| GET | `/api/data/files/{id}` | Get file details |
| POST | `/api/data/files/{id}/process` | Process file |
| DELETE | `/api/data/files/{id}` | Delete file |
| GET | `/api/data/files/{id}/errors` | Get file errors |
| GET | `/api/data/files/{id}/preview` | Preview file data |

### Data Tables
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/data/customers` | List customers |
| GET | `/api/data/customers/{id}` | Get customer |
| GET | `/api/data/orders` | List orders |
| GET | `/api/data/orders/{id}` | Get order |
| GET | `/api/data/errors` | List all errors |

### Jobs
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/jobs` | List jobs |
| POST | `/api/jobs` | Create/start job |
| GET | `/api/jobs/{id}` | Get job details |
| POST | `/api/jobs/{id}/cancel` | Cancel job |
| GET | `/api/jobs/schedules` | List schedules |
| POST | `/api/jobs/schedules` | Create schedule |

### Reports
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/reports` | List reports |
| POST | `/api/reports/generate` | Generate report |
| GET | `/api/reports/{id}` | Get report |
| GET | `/api/reports/{id}/download` | Download report |

### Dashboard
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard/stats` | Get dashboard stats |
| GET | `/api/dashboard/charts/uploads` | Upload chart data |
| GET | `/api/dashboard/charts/errors` | Error chart data |

## 6.2 Request/Response Examples

### Login
```http
POST /api/auth/login
Content-Type: application/json

{
    "username": "admin",
    "password": "admin123"
}
```

Response:
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 3600,
    "user": {
        "id": 1,
        "username": "admin",
        "email": "admin@example.com",
        "role": "admin"
    }
}
```

### Upload File
```http
POST /api/data/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: customers.csv
```

Response:
```json
{
    "id": 42,
    "filename": "20240115_123456_customers.csv",
    "original_name": "customers.csv",
    "file_type": "csv",
    "file_size": 15234,
    "status": "uploaded",
    "uploaded_at": "2024-01-15T12:34:56Z"
}
```

### Process File
```http
POST /api/data/files/42/process
Authorization: Bearer <token>
Content-Type: application/json

{
    "target_table": "customers",
    "validation_rules": {
        "required_fields": ["customer_code", "name"],
        "email_format": ["email"],
        "positive_numbers": ["credit_limit"]
    }
}
```

Response:
```json
{
    "job_id": 123,
    "file_id": 42,
    "status": "processing",
    "message": "Processing started"
}
```

### Get Dashboard Stats
```http
GET /api/dashboard/stats
Authorization: Bearer <token>
```

Response:
```json
{
    "files": {
        "total": 156,
        "today": 12,
        "processing": 2,
        "failed": 3
    },
    "records": {
        "customers": 45230,
        "orders": 128456
    },
    "errors": {
        "total": 234,
        "today": 15
    },
    "jobs": {
        "running": 1,
        "queued": 3
    }
}
```

### List Files with Filters
```http
GET /api/data/files?status=completed&page=1&limit=20&sort=-uploaded_at
Authorization: Bearer <token>
```

Response:
```json
{
    "items": [
        {
            "id": 42,
            "filename": "customers.csv",
            "status": "completed",
            "row_count": 1500,
            "uploaded_at": "2024-01-15T12:34:56Z"
        }
    ],
    "total": 156,
    "page": 1,
    "pages": 8,
    "limit": 20
}
```

## 6.3 OpenAPI Notes

```yaml
openapi: 3.0.3
info:
  title: DataOps Dashboard API
  version: 1.0.0
  description: Enterprise data platform API

servers:
  - url: http://localhost:8000
    description: Development
  - url: https://api.dataops.example.com
    description: Production

security:
  - bearerAuth: []

components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

  schemas:
    Error:
      type: object
      properties:
        detail:
          type: string
        code:
          type: string

    DataFile:
      type: object
      properties:
        id:
          type: integer
        filename:
          type: string
        status:
          type: string
          enum: [uploaded, processing, completed, failed]
        row_count:
          type: integer
        uploaded_at:
          type: string
          format: date-time

  responses:
    Unauthorized:
      description: Invalid or missing token
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
    Forbidden:
      description: Permission denied
    NotFound:
      description: Resource not found
```

---

# 7. UI PAGES

## 7.1 Page List

| Page | Route | Description |
|------|-------|-------------|
| Login | `/login` | User login form |
| Dashboard | `/` | Main dashboard with stats |
| Files | `/files` | List uploaded files |
| Upload | `/upload` | Upload new file |
| File Detail | `/files/{id}` | File details, errors |
| Customers | `/data/customers` | Customer data table |
| Orders | `/data/orders` | Order data table |
| Jobs | `/jobs` | Job list and management |
| Reports | `/reports` | Report generation |
| Users | `/admin/users` | User management (admin) |
| Settings | `/settings` | User settings |

## 7.2 Page Details

### Dashboard (`/`)
**Shows:**
- Stats cards: Total files, Records, Errors, Running jobs
- Upload trend chart (last 7 days)
- Error distribution pie chart
- Recent files table (last 10)
- Recent errors list

**HTMX Interactions:**
```html
<!-- Auto-refresh stats every 30 seconds -->
<div hx-get="/api/dashboard/stats"
     hx-trigger="load, every 30s"
     hx-target="#stats-cards">
</div>

<!-- Load chart data -->
<canvas id="uploadChart"
        hx-get="/api/dashboard/charts/uploads"
        hx-trigger="load"
        hx-swap="none">
</canvas>
```

### Files (`/files`)
**Shows:**
- Filter form (status, date range)
- Files table with columns: Name, Type, Status, Rows, Uploaded, Actions
- Pagination

**HTMX Interactions:**
```html
<!-- Filter and update table -->
<form hx-get="/pages/files/table"
      hx-target="#files-table"
      hx-trigger="change from:select, submit">
    <select name="status">
        <option value="">All</option>
        <option value="completed">Completed</option>
        <option value="failed">Failed</option>
    </select>
</form>

<!-- Delete file with confirmation -->
<button hx-delete="/api/data/files/42"
        hx-confirm="Delete this file?"
        hx-target="closest tr"
        hx-swap="outerHTML">
    Delete
</button>

<!-- Process file -->
<button hx-post="/api/data/files/42/process"
        hx-target="#file-status-42">
    Process
</button>
```

### Upload (`/upload`)
**Shows:**
- Drag and drop zone
- File type selector
- Target table selector
- Upload progress bar

**HTMX Interactions:**
```html
<!-- File upload with progress -->
<form hx-post="/api/data/upload"
      hx-encoding="multipart/form-data"
      hx-target="#upload-result"
      hx-indicator="#progress">
    <input type="file" name="file" accept=".csv,.json">
    <button type="submit">Upload</button>
</form>

<div id="progress" class="htmx-indicator">
    <div class="progress-bar"></div>
</div>
```

### File Detail (`/files/{id}`)
**Shows:**
- File info card (name, size, status, dates)
- Data preview table (first 100 rows)
- Errors table (if any)
- Actions: Reprocess, Download, Delete

**HTMX Interactions:**
```html
<!-- Load errors tab -->
<button hx-get="/pages/files/42/errors"
        hx-target="#tab-content"
        class="tab-btn">
    Errors (15)
</button>

<!-- Load preview tab -->
<button hx-get="/pages/files/42/preview"
        hx-target="#tab-content"
        class="tab-btn">
    Preview
</button>
```

### Data Tables (`/data/customers`, `/data/orders`)
**Shows:**
- Search box
- Column filters
- Sortable table
- Pagination
- Export button

**HTMX Interactions:**
```html
<!-- Search with debounce -->
<input type="search"
       name="q"
       hx-get="/pages/data/customers/table"
       hx-trigger="keyup changed delay:300ms"
       hx-target="#data-table">

<!-- Sort columns -->
<th hx-get="/pages/data/customers/table?sort=name"
    hx-target="#data-table"
    class="cursor-pointer">
    Name
</th>

<!-- Export -->
<button hx-get="/api/data/customers/export?format=csv"
        hx-swap="none">
    Export CSV
</button>
```

### Jobs (`/jobs`)
**Shows:**
- Job queue list
- Running jobs with progress
- Completed jobs history
- Schedule list

**HTMX Interactions:**
```html
<!-- Start job -->
<button hx-post="/api/jobs"
        hx-vals='{"job_type": "daily_etl"}'
        hx-target="#job-list">
    Run Daily ETL
</button>

<!-- Cancel job -->
<button hx-post="/api/jobs/123/cancel"
        hx-target="#job-123">
    Cancel
</button>

<!-- Auto-refresh running jobs -->
<div hx-get="/pages/jobs/running"
     hx-trigger="every 5s"
     hx-target="this">
</div>
```

### Reports (`/reports`)
**Shows:**
- Report type selector
- Date range picker
- Generate button
- Report history table

**HTMX Interactions:**
```html
<!-- Generate report -->
<form hx-post="/api/reports/generate"
      hx-target="#report-result">
    <select name="report_type">
        <option value="daily_summary">Daily Summary</option>
        <option value="error_analysis">Error Analysis</option>
        <option value="customer_segment">Customer Segments</option>
    </select>
    <input type="date" name="start_date">
    <input type="date" name="end_date">
    <button type="submit">Generate</button>
</form>
```

## 7.3 UI Components

### Base Template Structure
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{% block title %}DataOps{% endblock %}</title>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100">
    {% include "components/navbar.html" %}

    <main class="container mx-auto px-4 py-8">
        {% block content %}{% endblock %}
    </main>

    {% include "components/toast.html" %}
</body>
</html>
```

### Navbar Component
```html
<nav class="bg-white shadow">
    <div class="container mx-auto px-4">
        <div class="flex justify-between h-16">
            <div class="flex items-center">
                <a href="/" class="text-xl font-bold">DataOps</a>
                <a href="/files" class="ml-8">Files</a>
                <a href="/jobs" class="ml-4">Jobs</a>
                <a href="/reports" class="ml-4">Reports</a>
            </div>
            <div class="flex items-center">
                <span>{{ user.username }}</span>
                <a href="/logout" class="ml-4">Logout</a>
            </div>
        </div>
    </div>
</nav>
```

### Data Table Component
```html
<div class="bg-white rounded shadow overflow-hidden">
    <table class="min-w-full">
        <thead class="bg-gray-50">
            <tr>
                {% for col in columns %}
                <th hx-get="{{ url }}?sort={{ col.key }}"
                    hx-target="#table-body"
                    class="px-4 py-3 text-left cursor-pointer">
                    {{ col.label }}
                </th>
                {% endfor %}
            </tr>
        </thead>
        <tbody id="table-body">
            {% for row in data %}
            <tr class="border-t">
                {% for col in columns %}
                <td class="px-4 py-3">{{ row[col.key] }}</td>
                {% endfor %}
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <!-- Pagination -->
    <div class="px-4 py-3 border-t flex justify-between">
        <span>Page {{ page }} of {{ pages }}</span>
        <div>
            <button hx-get="{{ url }}?page={{ page - 1 }}"
                    hx-target="#table-body"
                    {% if page == 1 %}disabled{% endif %}>
                Previous
            </button>
            <button hx-get="{{ url }}?page={{ page + 1 }}"
                    hx-target="#table-body"
                    {% if page == pages %}disabled{% endif %}>
                Next
            </button>
        </div>
    </div>
</div>
```

---

# 8. DOCKER COMPOSE PLAN

## 8.1 Development docker-compose.yml

```yaml
version: '3.8'

services:
  # Oracle Database
  oracle:
    image: container-registry.oracle.com/database/express:21.3.0-xe
    container_name: dataops-oracle
    environment:
      - ORACLE_PWD=OraclePassword123
      - ORACLE_CHARACTERSET=AL32UTF8
    ports:
      - "1521:1521"
      - "5500:5500"
    volumes:
      - oracle_data:/opt/oracle/oradata
      - ./docker/oracle/init:/opt/oracle/scripts/startup
    healthcheck:
      test: ["CMD", "sqlplus", "-L", "sys/OraclePassword123@//localhost:1521/XEPDB1 as sysdba", "@/dev/null"]
      interval: 30s
      timeout: 10s
      retries: 10
    networks:
      - dataops-network

  # Redis
  redis:
    image: redis:7-alpine
    container_name: dataops-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - dataops-network

  # FastAPI Application
  api:
    build:
      context: .
      dockerfile: docker/api/Dockerfile
    container_name: dataops-api
    environment:
      - ENV=development
      - DEBUG=true
      - DATABASE_URL=oracle+oracledb://dataops:dataops123@oracle:1521/?service_name=XEPDB1
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=dev-secret-key-change-in-production
      - CORS_ORIGINS=http://localhost:3000,http://localhost:8000
    ports:
      - "8000:8000"
    volumes:
      - ./src:/app/src
      - ./templates:/app/templates
      - ./static:/app/static
      - ./uploads:/app/uploads
    depends_on:
      oracle:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
    networks:
      - dataops-network

  # Celery Worker
  worker:
    build:
      context: .
      dockerfile: docker/worker/Dockerfile
    container_name: dataops-worker
    environment:
      - ENV=development
      - DATABASE_URL=oracle+oracledb://dataops:dataops123@oracle:1521/?service_name=XEPDB1
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ./src:/app/src
      - ./uploads:/app/uploads
    depends_on:
      oracle:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: celery -A src.workers.celery_app worker --loglevel=info
    networks:
      - dataops-network

  # Celery Beat (Scheduler)
  beat:
    build:
      context: .
      dockerfile: docker/worker/Dockerfile
    container_name: dataops-beat
    environment:
      - ENV=development
      - DATABASE_URL=oracle+oracledb://dataops:dataops123@oracle:1521/?service_name=XEPDB1
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - worker
    command: celery -A src.workers.celery_app beat --loglevel=info
    networks:
      - dataops-network

volumes:
  oracle_data:
  redis_data:

networks:
  dataops-network:
    driver: bridge
```

## 8.2 Production docker-compose.prod.yml

```yaml
version: '3.8'

services:
  # Nginx Reverse Proxy
  nginx:
    build:
      context: .
      dockerfile: docker/nginx/Dockerfile
    container_name: dataops-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./docker/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./static:/usr/share/nginx/html/static:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
    depends_on:
      - api
    restart: always
    networks:
      - dataops-network

  # Oracle Database
  oracle:
    image: container-registry.oracle.com/database/express:21.3.0-xe
    container_name: dataops-oracle
    environment:
      - ORACLE_PWD=${ORACLE_PASSWORD}
      - ORACLE_CHARACTERSET=AL32UTF8
    volumes:
      - oracle_data:/opt/oracle/oradata
      - ./docker/oracle/init:/opt/oracle/scripts/startup
    healthcheck:
      test: ["CMD", "sqlplus", "-L", "sys/${ORACLE_PASSWORD}@//localhost:1521/XEPDB1 as sysdba", "@/dev/null"]
      interval: 30s
      timeout: 10s
      retries: 10
    restart: always
    networks:
      - dataops-network

  # Redis
  redis:
    image: redis:7-alpine
    container_name: dataops-redis
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: always
    networks:
      - dataops-network

  # FastAPI Application
  api:
    image: ${DOCKER_REGISTRY}/dataops-api:${VERSION:-latest}
    container_name: dataops-api
    environment:
      - ENV=production
      - DEBUG=false
      - DATABASE_URL=oracle+oracledb://dataops:${DB_PASSWORD}@oracle:1521/?service_name=XEPDB1
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
      - CORS_ORIGINS=${CORS_ORIGINS}
    volumes:
      - uploads_data:/app/uploads
      - logs_data:/app/logs
    depends_on:
      oracle:
        condition: service_healthy
      redis:
        condition: service_healthy
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '1'
          memory: 1G
    restart: always
    networks:
      - dataops-network

  # Celery Worker
  worker:
    image: ${DOCKER_REGISTRY}/dataops-worker:${VERSION:-latest}
    container_name: dataops-worker
    environment:
      - ENV=production
      - DATABASE_URL=oracle+oracledb://dataops:${DB_PASSWORD}@oracle:1521/?service_name=XEPDB1
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
    volumes:
      - uploads_data:/app/uploads
      - logs_data:/app/logs
    depends_on:
      oracle:
        condition: service_healthy
      redis:
        condition: service_healthy
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
    restart: always
    networks:
      - dataops-network

  # Celery Beat
  beat:
    image: ${DOCKER_REGISTRY}/dataops-worker:${VERSION:-latest}
    container_name: dataops-beat
    environment:
      - ENV=production
      - DATABASE_URL=oracle+oracledb://dataops:${DB_PASSWORD}@oracle:1521/?service_name=XEPDB1
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
    command: celery -A src.workers.celery_app beat --loglevel=warning
    depends_on:
      - worker
    restart: always
    networks:
      - dataops-network

  # Prometheus (Optional)
  prometheus:
    image: prom/prometheus:v2.45.0
    container_name: dataops-prometheus
    volumes:
      - ./docker/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    restart: always
    networks:
      - dataops-network

volumes:
  oracle_data:
  redis_data:
  uploads_data:
  logs_data:
  prometheus_data:

networks:
  dataops-network:
    driver: bridge
```

## 8.3 Dockerfiles

### API Dockerfile (docker/api/Dockerfile)
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install Oracle Instant Client
RUN apt-get update && apt-get install -y \
    libaio1 \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ ./src/
COPY templates/ ./templates/
COPY static/ ./static/

# Create upload directory
RUN mkdir -p /app/uploads /app/logs

# Non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Worker Dockerfile (docker/worker/Dockerfile)
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install Oracle Instant Client
RUN apt-get update && apt-get install -y \
    libaio1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ ./src/

# Create directories
RUN mkdir -p /app/uploads /app/logs

# Non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

CMD ["celery", "-A", "src.workers.celery_app", "worker", "--loglevel=info"]
```

### Nginx Dockerfile (docker/nginx/Dockerfile)
```dockerfile
FROM nginx:1.25-alpine

COPY docker/nginx/nginx.conf /etc/nginx/nginx.conf
COPY static/ /usr/share/nginx/html/static/

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
```

## 8.4 Nginx Configuration (docker/nginx/nginx.conf)
```nginx
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    # Logging
    log_format json_combined escape=json '{'
        '"time":"$time_iso8601",'
        '"remote_addr":"$remote_addr",'
        '"method":"$request_method",'
        '"uri":"$request_uri",'
        '"status":$status,'
        '"body_bytes_sent":$body_bytes_sent,'
        '"request_time":$request_time,'
        '"upstream_response_time":"$upstream_response_time"'
    '}';

    access_log /var/log/nginx/access.log json_combined;
    error_log /var/log/nginx/error.log warn;

    # Gzip
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;

    # Upstream
    upstream api {
        server api:8000;
    }

    server {
        listen 80;
        server_name _;

        # Redirect to HTTPS in production
        # return 301 https://$server_name$request_uri;

        # Static files
        location /static/ {
            alias /usr/share/nginx/html/static/;
            expires 30d;
            add_header Cache-Control "public, immutable";
        }

        # API endpoints
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Login endpoint (stricter rate limit)
        location /api/auth/login {
            limit_req zone=login burst=5 nodelay;
            proxy_pass http://api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        # Web pages
        location / {
            proxy_pass http://api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        # Health check
        location /health {
            access_log off;
            return 200 "OK";
        }
    }
}
```

---

# 9. CI WORKFLOW YAML

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: '3.12'

jobs:
  lint:
    name: Lint & Format
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install ruff mypy

      - name: Run Ruff (lint)
        run: ruff check src/ tests/

      - name: Run Ruff (format check)
        run: ruff format --check src/ tests/

      - name: Run MyPy (optional)
        run: mypy src/ --ignore-missing-imports || true

  test:
    name: Tests
    runs-on: ubuntu-latest
    needs: lint

    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      oracle:
        image: gvenzl/oracle-xe:21-slim
        ports:
          - 1521:1521
        env:
          ORACLE_PASSWORD: testpassword
        options: >-
          --health-cmd "healthcheck.sh"
          --health-interval 30s
          --health-timeout 10s
          --health-retries 10

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Cache pip
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('requirements*.txt') }}
          restore-keys: |
            ${{ runner.os }}-pip-

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Wait for Oracle
        run: |
          for i in {1..30}; do
            if python -c "import oracledb; oracledb.connect(user='system', password='testpassword', dsn='localhost:1521/XEPDB1')" 2>/dev/null; then
              echo "Oracle is ready!"
              break
            fi
            echo "Waiting for Oracle... ($i/30)"
            sleep 10
          done

      - name: Run database migrations
        env:
          DATABASE_URL: oracle+oracledb://system:testpassword@localhost:1521/?service_name=XEPDB1
        run: python migrations/migrate.py

      - name: Run tests
        env:
          DATABASE_URL: oracle+oracledb://system:testpassword@localhost:1521/?service_name=XEPDB1
          REDIS_URL: redis://localhost:6379/0
          SECRET_KEY: test-secret-key
        run: |
          pytest tests/ -v --cov=src --cov-report=xml --cov-report=html

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
          fail_ci_if_error: false

  build:
    name: Build Docker Images
    runs-on: ubuntu-latest
    needs: test

    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build API image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/api/Dockerfile
          push: false
          tags: dataops-api:test
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Build Worker image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/worker/Dockerfile
          push: false
          tags: dataops-worker:test
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

---

# 10. CD WORKFLOW YAML

```yaml
# .github/workflows/cd.yml
name: CD

on:
  push:
    branches: [main]
    tags: ['v*']

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build-and-push:
    name: Build and Push Images
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=semver,pattern={{version}}
            type=sha,prefix=

      - name: Build and push API image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/api/Dockerfile
          push: true
          tags: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-api:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Build and push Worker image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/worker/Dockerfile
          push: true
          tags: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-worker:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  deploy:
    name: Deploy to Server
    runs-on: ubuntu-latest
    needs: build-and-push
    environment: production

    steps:
      - uses: actions/checkout@v4

      - name: Copy files to server
        uses: appleboy/scp-action@v0.1.7
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          source: "docker-compose.prod.yml,docker/,migrations/,scripts/"
          target: "/opt/dataops"

      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /opt/dataops

            # Set environment variables
            export VERSION=${{ github.sha }}
            export DOCKER_REGISTRY=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}

            # Pull new images
            docker-compose -f docker-compose.prod.yml pull

            # Run database migrations
            docker-compose -f docker-compose.prod.yml run --rm api \
              python migrations/migrate.py

            # Deploy with zero downtime
            docker-compose -f docker-compose.prod.yml up -d --remove-orphans

            # Wait for health check
            sleep 10
            curl -f http://localhost/health || exit 1

            # Cleanup old images
            docker image prune -af --filter "until=24h"

            echo "Deployment completed successfully!"

      - name: Notify on success
        if: success()
        run: |
          echo "Deployment to production successful!"
          # Add Slack/Discord notification here

      - name: Notify on failure
        if: failure()
        run: |
          echo "Deployment failed!"
          # Add alert notification here
```

---

# 11. TESTING PLAN

## 11.1 Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── test_api/
│   ├── test_auth.py         # Authentication tests
│   ├── test_data.py         # Data endpoint tests
│   └── test_jobs.py         # Job endpoint tests
├── test_services/
│   ├── test_ingest.py       # File parsing tests
│   ├── test_validate.py     # Validation tests
│   └── test_load.py         # Oracle loading tests
└── test_integration/
    └── test_etl_pipeline.py # Full pipeline tests
```

## 11.2 Test Fixtures (conftest.py)

```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
import oracledb
from src.api.main import app
from src.core.database import get_db

@pytest.fixture(scope="session")
def oracle_connection():
    """Create Oracle connection for tests."""
    conn = oracledb.connect(
        user="dataops_test",
        password="test123",
        dsn="localhost:1521/XEPDB1"
    )
    yield conn
    conn.close()

@pytest.fixture
def db_session(oracle_connection):
    """Create database session with rollback."""
    cursor = oracle_connection.cursor()
    yield cursor
    oracle_connection.rollback()
    cursor.close()

@pytest.fixture
def client(db_session):
    """Create test client with DB override."""
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def auth_headers(client):
    """Get authenticated headers."""
    response = client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "testpass"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def sample_csv(tmp_path):
    """Create sample CSV file."""
    csv_content = """customer_code,name,email,credit_limit
CUST001,John Doe,john@example.com,1000.00
CUST002,Jane Smith,jane@example.com,2000.00
CUST003,Bad Email,invalid-email,3000.00
"""
    file_path = tmp_path / "test.csv"
    file_path.write_text(csv_content)
    return file_path

@pytest.fixture
def sample_json(tmp_path):
    """Create sample JSON file."""
    import json
    data = [
        {"order_number": "ORD001", "customer_id": 1, "total": 100.00},
        {"order_number": "ORD002", "customer_id": 2, "total": 200.00}
    ]
    file_path = tmp_path / "test.json"
    file_path.write_text(json.dumps(data))
    return file_path
```

## 11.3 Sample Test Cases

### Authentication Tests
```python
# tests/test_api/test_auth.py
import pytest

class TestAuth:
    def test_login_success(self, client):
        response = client.post("/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_login_wrong_password(self, client):
        response = client.post("/api/auth/login", json={
            "username": "admin",
            "password": "wrongpassword"
        })
        assert response.status_code == 401

    def test_login_missing_fields(self, client):
        response = client.post("/api/auth/login", json={})
        assert response.status_code == 422

    def test_protected_endpoint_no_token(self, client):
        response = client.get("/api/data/files")
        assert response.status_code == 401

    def test_protected_endpoint_with_token(self, client, auth_headers):
        response = client.get("/api/data/files", headers=auth_headers)
        assert response.status_code == 200
```

### Data Validation Tests
```python
# tests/test_services/test_validate.py
import pytest
from src.services.validate import DataValidator

class TestDataValidator:
    @pytest.fixture
    def validator(self):
        rules = {
            "required_fields": ["customer_code", "name"],
            "email_format": ["email"],
            "positive_numbers": ["credit_limit"],
            "max_length": {"name": 100, "email": 100}
        }
        return DataValidator(rules)

    def test_valid_row(self, validator):
        row = {
            "customer_code": "CUST001",
            "name": "John Doe",
            "email": "john@example.com",
            "credit_limit": 1000.00
        }
        errors = validator.validate_row(row)
        assert len(errors) == 0

    def test_missing_required_field(self, validator):
        row = {
            "name": "John Doe",
            "email": "john@example.com"
        }
        errors = validator.validate_row(row)
        assert len(errors) == 1
        assert errors[0]["type"] == "REQUIRED"
        assert errors[0]["field"] == "customer_code"

    def test_invalid_email(self, validator):
        row = {
            "customer_code": "CUST001",
            "name": "John Doe",
            "email": "invalid-email"
        }
        errors = validator.validate_row(row)
        assert len(errors) == 1
        assert errors[0]["type"] == "FORMAT"

    def test_negative_number(self, validator):
        row = {
            "customer_code": "CUST001",
            "name": "John Doe",
            "credit_limit": -100.00
        }
        errors = validator.validate_row(row)
        assert len(errors) == 1
        assert errors[0]["type"] == "RANGE"

    def test_max_length_exceeded(self, validator):
        row = {
            "customer_code": "CUST001",
            "name": "A" * 150  # Exceeds 100
        }
        errors = validator.validate_row(row)
        assert len(errors) == 1
        assert errors[0]["type"] == "LENGTH"
```

### Integration Test
```python
# tests/test_integration/test_etl_pipeline.py
import pytest

class TestETLPipeline:
    def test_full_pipeline(self, client, auth_headers, sample_csv):
        # Step 1: Upload file
        with open(sample_csv, "rb") as f:
            response = client.post(
                "/api/data/upload",
                headers=auth_headers,
                files={"file": ("test.csv", f, "text/csv")}
            )
        assert response.status_code == 200
        file_id = response.json()["id"]

        # Step 2: Process file
        response = client.post(
            f"/api/data/files/{file_id}/process",
            headers=auth_headers,
            json={"target_table": "customers"}
        )
        assert response.status_code == 200
        job_id = response.json()["job_id"]

        # Step 3: Wait for job completion
        import time
        for _ in range(30):
            response = client.get(
                f"/api/jobs/{job_id}",
                headers=auth_headers
            )
            if response.json()["status"] in ["completed", "failed"]:
                break
            time.sleep(1)

        # Step 4: Check results
        response = client.get(
            f"/api/data/files/{file_id}",
            headers=auth_headers
        )
        file_data = response.json()
        assert file_data["status"] == "completed"
        assert file_data["row_count"] == 2  # 2 valid rows

        # Step 5: Check errors
        response = client.get(
            f"/api/data/files/{file_id}/errors",
            headers=auth_headers
        )
        errors = response.json()["items"]
        assert len(errors) == 1  # 1 invalid email
        assert errors[0]["error_type"] == "FORMAT"
```

## 11.4 Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=src --cov-report=html

# Run specific test file
pytest tests/test_services/test_validate.py -v

# Run only fast tests (no DB)
pytest tests/ -v -m "not slow"

# Run integration tests
pytest tests/test_integration/ -v
```

---

# 12. SAMPLE DATA AND SCRIPTS

## 12.1 Sample CSV (sample_data/customers.csv)
```csv
customer_code,name,email,phone,country,segment,credit_limit
CUST001,John Doe,john.doe@email.com,+1-555-0101,USA,Enterprise,50000.00
CUST002,Jane Smith,jane.smith@email.com,+1-555-0102,USA,SMB,15000.00
CUST003,Bob Wilson,bob@company.co.uk,+44-20-7946-0958,UK,Enterprise,75000.00
CUST004,Alice Brown,alice.b@gmail.com,+1-555-0104,Canada,SMB,10000.00
CUST005,Charlie Davis,charlie@tech.io,+49-30-12345678,Germany,Startup,5000.00
CUST006,Invalid Email,not-an-email,+1-555-0106,USA,SMB,8000.00
CUST007,Missing Phone,missing@email.com,,France,Enterprise,45000.00
CUST008,Negative Credit,neg@email.com,+1-555-0108,USA,SMB,-1000.00
CUST009,Long Name Very Very Very Very Very Very Very Very Very Very Long,long@email.com,+1-555-0109,USA,SMB,12000.00
CUST010,Unicode Test,unicode@email.com,+81-3-1234-5678,Japan,Enterprise,60000.00
```

## 12.2 Sample JSON (sample_data/orders.json)
```json
[
  {
    "order_number": "ORD-2024-001",
    "customer_code": "CUST001",
    "order_date": "2024-01-15",
    "items": [
      {"product": "Widget A", "qty": 10, "price": 25.00},
      {"product": "Widget B", "qty": 5, "price": 50.00}
    ],
    "total_amount": 500.00,
    "status": "completed"
  },
  {
    "order_number": "ORD-2024-002",
    "customer_code": "CUST002",
    "order_date": "2024-01-16",
    "items": [
      {"product": "Gadget X", "qty": 2, "price": 150.00}
    ],
    "total_amount": 300.00,
    "status": "pending"
  },
  {
    "order_number": "ORD-2024-003",
    "customer_code": "INVALID",
    "order_date": "2024-01-17",
    "items": [],
    "total_amount": 0.00,
    "status": "cancelled"
  }
]
```

## 12.3 Seed Script (scripts/seed_data.py)
```python
#!/usr/bin/env python3
"""Seed database with initial data."""
import oracledb
import os
from datetime import datetime

def get_connection():
    return oracledb.connect(
        user=os.getenv("DB_USER", "dataops"),
        password=os.getenv("DB_PASSWORD", "dataops123"),
        dsn=os.getenv("DB_DSN", "localhost:1521/XEPDB1")
    )

def seed_users(cursor):
    """Create default users."""
    users = [
        ("admin", "admin@dataops.local",
         "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4", "admin"),
        ("analyst", "analyst@dataops.local",
         "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4", "analyst"),
        ("viewer", "viewer@dataops.local",
         "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4", "viewer"),
    ]

    for username, email, password_hash, role in users:
        cursor.execute("""
            MERGE INTO users u
            USING (SELECT :1 as username FROM dual) s
            ON (u.username = s.username)
            WHEN NOT MATCHED THEN
                INSERT (username, email, password_hash, role)
                VALUES (:1, :2, :3, :4)
        """, [username, email, password_hash, role])

    print(f"Seeded {len(users)} users")

def seed_config(cursor):
    """Create default configuration."""
    configs = [
        ("max_upload_size_mb", "100", "Maximum file upload size in MB"),
        ("retention_days", "90", "Days to keep processed files"),
        ("batch_size", "1000", "Rows per batch for processing"),
        ("report_schedule", "0 6 * * 1", "Weekly report cron schedule"),
    ]

    for key, value, desc in configs:
        cursor.execute("""
            MERGE INTO config c
            USING (SELECT :1 as config_key FROM dual) s
            ON (c.config_key = s.config_key)
            WHEN NOT MATCHED THEN
                INSERT (config_key, config_value, description)
                VALUES (:1, :2, :3)
            WHEN MATCHED THEN
                UPDATE SET config_value = :2, description = :3
        """, [key, value, desc])

    print(f"Seeded {len(configs)} config entries")

def seed_sample_customers(cursor):
    """Insert sample customers."""
    customers = [
        ("DEMO001", "Demo Company A", "demo.a@example.com", "USA", "Enterprise", 50000),
        ("DEMO002", "Demo Company B", "demo.b@example.com", "UK", "SMB", 25000),
        ("DEMO003", "Demo Company C", "demo.c@example.com", "Germany", "Startup", 10000),
    ]

    for code, name, email, country, segment, credit in customers:
        cursor.execute("""
            MERGE INTO customers c
            USING (SELECT :1 as customer_code FROM dual) s
            ON (c.customer_code = s.customer_code)
            WHEN NOT MATCHED THEN
                INSERT (customer_code, name, email, country, segment, credit_limit)
                VALUES (:1, :2, :3, :4, :5, :6)
        """, [code, name, email, country, segment, credit])

    print(f"Seeded {len(customers)} sample customers")

def main():
    print("Starting database seed...")
    print(f"Time: {datetime.now()}")

    conn = get_connection()
    cursor = conn.cursor()

    try:
        seed_users(cursor)
        seed_config(cursor)
        seed_sample_customers(cursor)
        conn.commit()
        print("\nSeed completed successfully!")
    except Exception as e:
        conn.rollback()
        print(f"\nSeed failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()
```

## 12.4 Loader Script (scripts/load_sample_data.py)
```python
#!/usr/bin/env python3
"""Load sample data files into database."""
import csv
import json
import oracledb
import os
import sys

def load_csv(filepath, cursor, table_name):
    """Load CSV file into table."""
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print(f"No data in {filepath}")
        return 0

    columns = rows[0].keys()
    placeholders = ', '.join([f':{i+1}' for i in range(len(columns))])
    sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"

    loaded = 0
    errors = 0

    for row in rows:
        try:
            values = [row[col] if row[col] != '' else None for col in columns]
            cursor.execute(sql, values)
            loaded += 1
        except oracledb.Error as e:
            print(f"Error loading row: {e}")
            errors += 1

    print(f"Loaded {loaded} rows, {errors} errors from {filepath}")
    return loaded

def load_json(filepath, cursor, table_name):
    """Load JSON file into table."""
    with open(filepath, 'r') as f:
        data = json.load(f)

    if not data:
        print(f"No data in {filepath}")
        return 0

    loaded = 0
    for item in data:
        # Flatten nested structures if needed
        flat_item = {}
        for key, value in item.items():
            if isinstance(value, (list, dict)):
                flat_item[key] = json.dumps(value)
            else:
                flat_item[key] = value

        columns = flat_item.keys()
        placeholders = ', '.join([f':{i+1}' for i in range(len(columns))])
        sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"

        try:
            cursor.execute(sql, list(flat_item.values()))
            loaded += 1
        except oracledb.Error as e:
            print(f"Error: {e}")

    print(f"Loaded {loaded} rows from {filepath}")
    return loaded

def main():
    conn = oracledb.connect(
        user=os.getenv("DB_USER", "dataops"),
        password=os.getenv("DB_PASSWORD", "dataops123"),
        dsn=os.getenv("DB_DSN", "localhost:1521/XEPDB1")
    )
    cursor = conn.cursor()

    try:
        # Load sample data
        load_csv("sample_data/customers.csv", cursor, "staging_customers")
        load_json("sample_data/orders.json", cursor, "staging_orders")
        conn.commit()
        print("\nData loading complete!")
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()
```

---

# 13. EXTRA "MASTER" OPTIONS

## 13.1 Monitoring with Prometheus

### Prometheus Config (docker/prometheus/prometheus.yml)
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: /metrics

  - job_name: 'celery'
    static_configs:
      - targets: ['worker:9808']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:9121']
```

### FastAPI Metrics
```python
# src/core/metrics.py
from prometheus_client import Counter, Histogram, generate_latest
from fastapi import Response

REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

ETL_JOBS = Counter(
    'etl_jobs_total',
    'Total ETL jobs',
    ['job_type', 'status']
)

ROWS_PROCESSED = Counter(
    'rows_processed_total',
    'Total rows processed',
    ['table', 'status']
)

def metrics_endpoint():
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )
```

## 13.2 RBAC Implementation

```python
# src/core/rbac.py
from enum import Enum
from functools import wraps
from fastapi import HTTPException, Depends
from src.core.security import get_current_user

class Role(str, Enum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"

# Permission matrix
PERMISSIONS = {
    Role.ADMIN: ["*"],  # All permissions
    Role.ANALYST: [
        "files:read", "files:create", "files:process",
        "jobs:read", "jobs:create",
        "reports:read", "reports:create",
        "data:read", "data:export"
    ],
    Role.VIEWER: [
        "files:read",
        "jobs:read",
        "reports:read",
        "data:read"
    ]
}

def has_permission(user_role: str, permission: str) -> bool:
    """Check if role has permission."""
    role_permissions = PERMISSIONS.get(Role(user_role), [])
    return "*" in role_permissions or permission in role_permissions

def require_permission(permission: str):
    """Decorator to require permission."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, user=Depends(get_current_user), **kwargs):
            if not has_permission(user.role, permission):
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission denied: {permission}"
                )
            return await func(*args, user=user, **kwargs)
        return wrapper
    return decorator

# Usage:
# @router.delete("/files/{id}")
# @require_permission("files:delete")
# async def delete_file(id: int, user: User = Depends(get_current_user)):
#     ...
```

## 13.3 Audit Logging

```python
# src/core/audit.py
import json
from datetime import datetime
from fastapi import Request
from src.core.database import get_db

async def log_action(
    user_id: int,
    action: str,
    resource_type: str = None,
    resource_id: int = None,
    old_value: dict = None,
    new_value: dict = None,
    request: Request = None
):
    """Log user action to audit table."""
    db = next(get_db())

    ip_address = None
    user_agent = None
    if request:
        ip_address = request.client.host
        user_agent = request.headers.get("user-agent", "")[:500]

    db.execute("""
        INSERT INTO audit_log (
            user_id, action, resource_type, resource_id,
            old_value, new_value, ip_address, user_agent
        ) VALUES (
            :user_id, :action, :resource_type, :resource_id,
            :old_value, :new_value, :ip_address, :user_agent
        )
    """, {
        "user_id": user_id,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "old_value": json.dumps(old_value) if old_value else None,
        "new_value": json.dumps(new_value) if new_value else None,
        "ip_address": ip_address,
        "user_agent": user_agent
    })
    db.connection.commit()

# Usage:
# await log_action(
#     user_id=user.id,
#     action="DELETE",
#     resource_type="file",
#     resource_id=file_id,
#     old_value={"filename": file.filename},
#     request=request
# )
```

## 13.4 Rate Limiting

```python
# src/core/rate_limit.py
import redis
from fastapi import HTTPException, Request
from functools import wraps
import time

redis_client = redis.from_url("redis://localhost:6379/0")

def rate_limit(max_requests: int, window_seconds: int):
    """Rate limit decorator."""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Create key from IP and endpoint
            client_ip = request.client.host
            endpoint = request.url.path
            key = f"rate_limit:{client_ip}:{endpoint}"

            # Get current count
            current = redis_client.get(key)

            if current is None:
                # First request
                redis_client.setex(key, window_seconds, 1)
            elif int(current) >= max_requests:
                # Rate limit exceeded
                ttl = redis_client.ttl(key)
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Try again in {ttl} seconds."
                )
            else:
                # Increment counter
                redis_client.incr(key)

            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

# Usage:
# @router.post("/api/auth/login")
# @rate_limit(max_requests=5, window_seconds=60)
# async def login(request: Request, ...):
#     ...
```

## 13.5 Performance Tuning Tips

### Oracle Performance
```sql
-- 1. Analyze tables regularly
EXEC DBMS_STATS.GATHER_TABLE_STATS('DATAOPS', 'CUSTOMERS');
EXEC DBMS_STATS.GATHER_TABLE_STATS('DATAOPS', 'ORDERS');

-- 2. Use bind variables (done automatically with oracledb)

-- 3. Batch inserts
-- Instead of single inserts, use executemany:
-- cursor.executemany(sql, batch_of_1000_rows)

-- 4. Partition large tables
CREATE TABLE orders (
    id NUMBER,
    order_date DATE,
    ...
)
PARTITION BY RANGE (order_date) (
    PARTITION p_2024_q1 VALUES LESS THAN (DATE '2024-04-01'),
    PARTITION p_2024_q2 VALUES LESS THAN (DATE '2024-07-01'),
    PARTITION p_2024_q3 VALUES LESS THAN (DATE '2024-10-01'),
    PARTITION p_2024_q4 VALUES LESS THAN (DATE '2025-01-01')
);

-- 5. Use parallel processing for large operations
ALTER SESSION ENABLE PARALLEL DML;
INSERT /*+ PARALLEL(4) */ INTO customers ...

-- 6. Monitor slow queries
SELECT sql_text, elapsed_time/1000000 as seconds
FROM v$sql
WHERE elapsed_time > 1000000
ORDER BY elapsed_time DESC;
```

### Python Performance
```python
# 1. Use connection pooling
import oracledb
pool = oracledb.create_pool(
    user="dataops",
    password="password",
    dsn="oracle:1521/XEPDB1",
    min=2,
    max=10,
    increment=1
)

# 2. Batch processing
def process_in_batches(data, batch_size=1000):
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        cursor.executemany(sql, batch)
        connection.commit()

# 3. Use async where possible
async def fetch_data():
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_url(session, url) for url in urls]
        return await asyncio.gather(*tasks)

# 4. Cache expensive queries
from functools import lru_cache

@lru_cache(maxsize=100)
def get_customer(customer_id):
    ...

# 5. Profile your code
import cProfile
cProfile.run('your_function()')
```

### Docker Performance
```yaml
# docker-compose.prod.yml optimizations
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
    healthcheck:
      interval: 10s
      timeout: 5s
      retries: 3
```

---

# Quick Start Commands

```bash
# 1. Clone and setup
git clone https://github.com/yourusername/dataops-dashboard.git
cd dataops-dashboard
cp .env.example .env

# 2. Start services
docker-compose up -d

# 3. Wait for Oracle (takes ~2 minutes first time)
docker-compose logs -f oracle

# 4. Run migrations
docker-compose exec api python migrations/migrate.py

# 5. Seed data
docker-compose exec api python scripts/seed_data.py

# 6. Open browser
open http://localhost:8000
# Login: admin / admin123

# 7. Run tests
docker-compose exec api pytest tests/ -v

# 8. View logs
docker-compose logs -f api worker
```

---

# Summary Checklist

- [ ] **Week 1-2**: Setup, Docker, Oracle, basic API
- [ ] **Week 3-4**: Data ingestion, validation, loading
- [ ] **Week 5-6**: Celery workers, job scheduling
- [ ] **Week 7-8**: Web UI with HTMX
- [ ] **Week 9-10**: Reports, security, testing
- [ ] **Week 11-12**: CI/CD, production deployment
- [ ] **Week 13+**: Monitoring, optimization, documentation

Total estimated time: **10-14 weeks** for a complete, production-ready system.

Good luck with your Master project!
