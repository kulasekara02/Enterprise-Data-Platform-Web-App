-- DataOps Dashboard Database Schema
-- Run as DATAOPS user

-- =====================================================
-- USERS TABLE
-- =====================================================
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

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);

-- =====================================================
-- DATA_FILES TABLE
-- =====================================================
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
    CONSTRAINT chk_file_status CHECK (status IN ('uploaded', 'processing', 'completed', 'failed'))
);

CREATE INDEX idx_files_status ON data_files(status);
CREATE INDEX idx_files_uploaded_by ON data_files(uploaded_by);
CREATE INDEX idx_files_uploaded_at ON data_files(uploaded_at);

-- =====================================================
-- CUSTOMERS TABLE (Example data table)
-- =====================================================
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
    CONSTRAINT fk_cust_source_file FOREIGN KEY (source_file_id) REFERENCES data_files(id)
);

CREATE INDEX idx_customers_code ON customers(customer_code);
CREATE INDEX idx_customers_country ON customers(country);
CREATE INDEX idx_customers_segment ON customers(segment);

-- =====================================================
-- ORDERS TABLE (Example data table)
-- =====================================================
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

CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_date ON orders(order_date);
CREATE INDEX idx_orders_status ON orders(status);

-- =====================================================
-- DATA_ERRORS TABLE
-- =====================================================
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

CREATE INDEX idx_errors_file ON data_errors(source_file_id);
CREATE INDEX idx_errors_type ON data_errors(error_type);

-- =====================================================
-- JOBS TABLE
-- =====================================================
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
    CONSTRAINT fk_job_started_by FOREIGN KEY (started_by) REFERENCES users(id),
    CONSTRAINT chk_job_status CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled'))
);

CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_type ON jobs(job_type);

-- =====================================================
-- AUDIT_LOG TABLE
-- =====================================================
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

CREATE INDEX idx_audit_user ON audit_log(user_id);
CREATE INDEX idx_audit_action ON audit_log(action);
CREATE INDEX idx_audit_created ON audit_log(created_at);

-- =====================================================
-- REPORTS TABLE
-- =====================================================
CREATE TABLE reports (
    id              NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    report_name     VARCHAR2(100) NOT NULL,
    report_type     VARCHAR2(50) NOT NULL,
    parameters      CLOB,
    file_path       VARCHAR2(500),
    generated_by    NUMBER,
    generated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_report_generated_by FOREIGN KEY (generated_by) REFERENCES users(id)
);

-- =====================================================
-- CONFIG TABLE
-- =====================================================
CREATE TABLE config (
    id              NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    config_key      VARCHAR2(100) NOT NULL UNIQUE,
    config_value    VARCHAR2(1000),
    description     VARCHAR2(500),
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- SEED DATA: Default Admin User
-- Password: admin123 (bcrypt hash)
-- =====================================================
INSERT INTO users (username, email, password_hash, role)
VALUES ('admin', 'admin@dataops.local', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.oMlNVhTuFTa/LO', 'admin');

INSERT INTO users (username, email, password_hash, role)
VALUES ('analyst', 'analyst@dataops.local', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.oMlNVhTuFTa/LO', 'analyst');

INSERT INTO users (username, email, password_hash, role)
VALUES ('viewer', 'viewer@dataops.local', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.oMlNVhTuFTa/LO', 'viewer');

-- =====================================================
-- SEED DATA: Config
-- =====================================================
INSERT INTO config (config_key, config_value, description)
VALUES ('max_upload_size_mb', '100', 'Maximum file upload size in MB');

INSERT INTO config (config_key, config_value, description)
VALUES ('retention_days', '90', 'Days to keep processed files');

INSERT INTO config (config_key, config_value, description)
VALUES ('batch_size', '1000', 'Rows per batch for processing');

COMMIT;
