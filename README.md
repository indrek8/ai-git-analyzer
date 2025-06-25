# Git Engineering Analytics Platform

An AI-powered platform for analyzing engineering effort and productivity across multiple Git repositories.

## Features

- 🔐 User authentication and management
- 📊 Multi-repository tracking (GitHub, GitLab, Bitbucket)
- 🤖 AI-powered commit analysis and classification
- 👥 Developer identity management and merging
- 📈 Engineering effort analytics and insights
- 🐳 Full Docker deployment with persistent data
- ⚡ Background job processing for repository syncing

## Technology Stack

- **Backend**: FastAPI (Python) with SQLAlchemy ORM
- **Frontend**: Vanilla JavaScript with responsive design
- **Database**: PostgreSQL with persistent Docker volumes
- **Background Jobs**: Celery + Redis
- **AI Integration**: OpenAI GPT-4, Anthropic Claude
- **Deployment**: Docker Compose

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Git

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd git-ai-analyzer
```

### 2. Environment Setup

Copy the example environment file and configure your settings:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```bash
# Required for AI analysis
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Required for GitHub integration
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret

# Update these for production
SECRET_KEY=your_secret_key_for_jwt_tokens
POSTGRES_PASSWORD=your_secure_password
```

### 3. Start the Application

```bash
docker-compose up -d
```

This will start:
- **PostgreSQL** database (port 5432)
- **Redis** cache and job queue (port 6379)
- **Backend API** (port 8000)
- **Frontend** web interface (port 3000)
- **Celery Worker** for background processing

### 4. Access the Application

Open your browser and go to: http://localhost:3000

Default login credentials (for development):
- Username: `admin`
- Password: `admin`

## Project Structure

```
git-ai-analyzer/
├── backend/                  # FastAPI backend
│   ├── app/
│   │   ├── api/             # API endpoints
│   │   ├── models/          # Database models
│   │   ├── auth/            # Authentication
│   │   ├── repositories/    # Git provider integrations
│   │   ├── analytics/       # AI analysis engine
│   │   └── background/      # Celery tasks
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                # Static web interface
│   ├── static/
│   │   ├── index.html
│   │   ├── styles.css
│   │   └── script.js
│   └── Dockerfile
├── docker-compose.yml       # Multi-service orchestration
├── .env.example            # Environment template
└── README.md
```

## API Endpoints

### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/register` - User registration
- `GET /api/auth/me` - Get current user

### Repositories
- `GET /api/repositories` - List repositories
- `POST /api/repositories` - Add repository
- `DELETE /api/repositories/{id}` - Remove repository
- `POST /api/repositories/{id}/sync` - Trigger sync

### Analytics
- `GET /api/analytics/effort` - Get effort analytics
- `GET /api/analytics/productivity` - Get productivity metrics
- `GET /api/analytics/developers` - Get developer analytics

## Development

### Running in Development Mode

```bash
# Start only the database and Redis
docker-compose up postgres redis -d

# Run backend locally
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run Celery worker
celery -A app.background.celery_app worker --loglevel=info
```

### Database Migrations

```bash
# Generate migration
alembic revision --autogenerate -m "Description"

# Run migrations
alembic upgrade head
```

## Configuration

### GitHub Integration

1. Create a GitHub OAuth App in your GitHub settings
2. Set the callback URL to: `http://localhost:3000/auth/github/callback`
3. Add the client ID and secret to your `.env` file

### AI Configuration

The platform supports multiple AI providers:

- **OpenAI**: Add your API key to `OPENAI_API_KEY`
- **Anthropic**: Add your API key to `ANTHROPIC_API_KEY`

## Features in Development

- [ ] GitLab integration
- [ ] Advanced analytics dashboard
- [ ] Team collaboration metrics
- [ ] Real-time notifications
- [ ] Multi-tenant support
- [ ] Advanced AI insights

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details