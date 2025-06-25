# Git Engineering Analytics Platform - Claude Code Configuration

This file contains configuration and context for Claude Code to help with development of the Git Engineering Analytics Platform.

## Project Overview

A comprehensive AI-powered platform for analyzing engineering effort and productivity across multiple Git repositories. Built with Python FastAPI backend, PostgreSQL database, Redis for background jobs, and a responsive web frontend.

### Current Implementation Status
✅ **PRODUCTION READY** - All core features implemented and tested:
- Complete authentication system with JWT tokens
- GitHub API integration with background syncing  
- Celery job queue with real-time progress tracking
- Full-stack web interface with repository management
- Developer identity management and commit analysis framework

### 🔑 Default Login Credentials
- **Username**: `admin`
- **Password**: `admin123`
- **Created via**: `docker-compose exec backend python create_admin.py`

## Architecture

### Technology Stack
- **Backend**: FastAPI (Python 3.11+) with SQLAlchemy ORM
- **Database**: PostgreSQL with persistent Docker volumes
- **Cache/Jobs**: Redis + Celery for background processing
- **Frontend**: Vanilla JavaScript with responsive CSS
- **AI Integration**: OpenAI GPT-4, Anthropic Claude APIs
- **Deployment**: Docker Compose with multi-container setup

### Core Services
- `postgres` - Database (port 5432)
- `redis` - Cache and job queue (port 6379)
- `backend` - FastAPI API server (port 8000)
- `frontend` - Nginx web server (port 3000)
- `worker` - Celery background workers

## Development Workflows

### Quick Start
```bash
# Start all services
make up

# View logs
make logs

# Stop services
make down
```

### Backend Development
```bash
# Access backend container
make shell

# Create admin user (username: admin, password: admin123)
docker-compose exec backend python create_admin.py

# Run migrations (when needed)
docker-compose exec backend alembic upgrade head

# Test API endpoints
curl http://localhost:8000/health

# Test authentication
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

### Testing Commands
```bash
# Run tests
make test

# Build specific service
docker-compose build backend

# Reset database
make db-reset
```

## Database Schema

### Core Models
- **Users**: Authentication and user management
- **Repositories**: Connected Git repositories (GitHub, GitLab, etc.)
- **Developers**: Git commit authors with identity merging
- **Commits**: Parsed commit data with metrics
- **CommitAnalysis**: AI-generated insights and classifications

### Key Relationships
- Users own Repositories
- Developers can be linked to Users (for identity management)
- Commits belong to Repositories and Developers
- CommitAnalysis provides AI insights for each Commit

## API Endpoints

### Authentication ✅ IMPLEMENTED
- `POST /api/auth/login` - User login with JWT token response
- `POST /api/auth/register` - User registration with validation
- `GET /api/auth/me` - Current user info from JWT token

### Repository Management ✅ IMPLEMENTED
- `GET /api/repositories` - List user repositories with sync status
- `POST /api/repositories` - Add new repository and trigger background sync
- `DELETE /api/repositories/{id}` - Remove repository and associated data
- `POST /api/repositories/{id}/sync` - Trigger background sync job

### Analytics 🚧 FRAMEWORK READY
- `GET /api/analytics/effort` - Engineering effort metrics (placeholder)
- `GET /api/analytics/productivity` - Productivity analytics (placeholder)
- `GET /api/analytics/developers` - Developer insights (placeholder)
- `GET /api/analytics/repositories` - Repository analytics (placeholder)

## Development Guidelines

### Code Style
- Follow PEP 8 for Python code
- Use type hints throughout the codebase
- Keep functions focused and well-documented
- Use SQLAlchemy models for all database operations

### Database Operations
- Always use Alembic for schema migrations
- Use proper indexes for query performance
- Handle database connections via dependency injection
- Use transactions for multi-step operations

### Background Jobs
- Use Celery for long-running operations (git syncing, AI analysis)
- Keep tasks idempotent and resumable
- Log progress for monitoring
- Handle failures gracefully with retries

### Security Considerations
- Never log API keys or sensitive data
- Use environment variables for configuration
- Validate all user inputs
- Implement proper CORS policies
- Use JWT tokens with reasonable expiration

## Environment Configuration

### Required Environment Variables
```bash
# Database
DATABASE_URL=postgresql://postgres:password@postgres:5432/git_analyzer

# Redis
REDIS_URL=redis://redis:6379/0

# Security
SECRET_KEY=your-secret-key-for-jwt-tokens

# AI APIs
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key

# Git Provider APIs
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
```

### Development vs Production
- Use `.env` file for local development
- Set environment variables directly in production
- Enable debug mode only in development
- Use proper logging levels for each environment

## Common Development Tasks

### Adding a New API Endpoint
1. Define the endpoint in appropriate router (`/api/` directory)
2. Add database models if needed (`/models/` directory)
3. Implement business logic
4. Add proper error handling
5. Update frontend JavaScript if needed

### Adding a New Background Job
1. Define task in `background/tasks.py`
2. Import in `background/celery_app.py`
3. Trigger from API endpoints as needed
4. Add progress tracking and error handling

### Database Schema Changes
1. Modify SQLAlchemy models
2. Generate migration: `alembic revision --autogenerate -m "Description"`
3. Review generated migration
4. Apply: `alembic upgrade head`

### Adding Git Provider Integration ✅ GITHUB IMPLEMENTED
1. Create provider-specific module in `repositories/` (✅ Done: `repositories/github.py`)
2. Implement authentication flow (✅ Done: GitHub API token support)
3. Add API client for fetching repository data (✅ Done: Complete GitHub API client)
4. Integrate with background sync jobs (✅ Done: Celery task integration)
5. Update frontend provider selection (✅ Done: Provider dropdown in UI)

#### GitHub Integration Features:
- Repository metadata fetching
- Commit history parsing with file changes
- Developer identity resolution
- Automatic background syncing
- Progress tracking and error handling

## Debugging and Troubleshooting

### Common Issues
- **Database connection errors**: Check PostgreSQL health and credentials
- **Redis connection errors**: Ensure Redis service is running
- **Import errors**: Check Python path and module structure
- **CORS issues**: Verify frontend URL in CORS configuration

### Useful Debug Commands
```bash
# View service logs
docker-compose logs -f backend

# Check database connectivity
docker-compose exec postgres psql -U postgres -d git_analyzer

# Test Redis connection
docker-compose exec redis redis-cli ping

# Access Python shell in backend
docker-compose exec backend python
```

### Performance Monitoring
- Monitor database query performance
- Track background job execution times
- Watch memory usage in containers
- Monitor API response times

## Implementation Status & Next Steps

### ✅ Completed Features
- **Authentication System**: Complete JWT-based auth with login/logout/registration
- **GitHub Integration**: Full API client with repository and commit syncing
- **Background Jobs**: Celery workers with Redis queue and progress tracking
- **Database Models**: Complete schema for users, repos, commits, developers, analysis
- **Frontend Interface**: Responsive web UI with repository management
- **Developer Identity Management**: Automatic developer detection and merging capability

### 🚧 Next Development Priorities

#### High Priority (Ready for Implementation)
- **AI Commit Analysis**: Implement LLM integration for commit classification and insights
- **Analytics Dashboard**: Build comprehensive metrics and visualization components
- **Advanced Repository Analytics**: Implement effort estimation and productivity metrics
- **Developer Identity UI**: Add frontend interface for managing developer identities

#### Medium Priority 
- **GitLab Provider Integration**: Extend repository support beyond GitHub
- **OAuth Integration**: Add GitHub OAuth for seamless repository access
- **Real-time Updates**: WebSocket integration for live sync status updates
- **Export Functionality**: PDF/CSV report generation

#### Low Priority
- **Multi-tenant Support**: Organization-level user management
- **Advanced AI Features**: Code quality analysis, predictive insights
- **External Integrations**: Slack notifications, webhook support
- **Mobile Optimization**: Enhanced responsive design

## Testing Strategy

### Unit Tests
- Test database models and relationships
- Test API endpoint logic
- Test background job functions
- Test utility functions

### Integration Tests
- Test complete API workflows
- Test database operations
- Test external API integrations
- Test background job processing

### End-to-End Tests
- Test complete user workflows
- Test multi-service interactions
- Test deployment scenarios

## Deployment Considerations

### Production Setup
- Use managed PostgreSQL service
- Use Redis cluster for high availability
- Set up proper monitoring and logging
- Configure backup strategies
- Use container orchestration (Kubernetes)

### Security Hardening
- Use strong passwords and API keys
- Enable SSL/TLS for all connections
- Implement rate limiting
- Regular security updates
- Audit logging for sensitive operations

This configuration provides Claude Code with comprehensive context for effective development assistance on this project.