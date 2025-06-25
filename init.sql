-- Database initialization script
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable additional extensions that might be useful for analytics
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Set timezone
SET timezone = 'UTC';

-- Basic indexes and constraints will be handled by SQLAlchemy migrations