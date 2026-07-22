# AI Workspace

A production-ready AI knowledge workspace that centralizes document management, semantic search, RAG-powered chat, and multi-agent AI workflows into a single modular platform.

> Built to demonstrate production-level AI engineering practices — not a "Chat with PDF" tutorial project.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React · TypeScript · Vite · Tailwind CSS · shadcn/ui |
| Backend | FastAPI · Python 3.12 |
| AI | LangChain · LangGraph |
| Database | PostgreSQL 16 |
| Vector DB | Qdrant |
| Storage | MinIO (S3-compatible) |
| Cache | Redis 7 |
| Infrastructure | Docker · Docker Compose |

---

## Project Structure

```
AI-Workspace/
├── backend/                  # FastAPI application
│   ├── app/
│   │   ├── api/              # Route definitions (versioned)
│   │   ├── core/             # App factory, logging
│   │   ├── config/           # Settings via pydantic-settings
│   │   ├── database/         # Async SQLAlchemy session
│   │   ├── models/           # ORM models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # Business logic
│   │   ├── repositories/     # Data access layer
│   │   ├── middleware/        # Custom middleware
│   │   └── utils/            # Shared utilities
│   ├── tests/
│   ├── main.py
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/                 # React + Vite application
│   └── src/
│       ├── components/       # Reusable UI components
│       ├── pages/            # Page-level components
│       ├── layouts/          # Layout wrappers
│       ├── features/         # Feature modules
│       ├── hooks/            # Custom React hooks
│       ├── services/         # API client & services
│       ├── store/            # State management (Zustand)
│       ├── routes/           # Route definitions
│       ├── types/            # TypeScript types
│       └── utils/            # Helper functions
│
├── docker/
│   ├── backend/Dockerfile
│   └── frontend/Dockerfile
│
├── docs/
│   ├── PROJECT.md
│   ├── AI_CONTEXT.md
│   └── STATUS.md
│
├── docker-compose.yml
├── .gitignore
└── README.md
```

---

## Local Development Setup

### Prerequisites

- [Python 3.12+](https://www.python.org/downloads/)
- [Node.js 22+](https://nodejs.org/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)

### Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your values

# Start development server
uvicorn main:app --reload
```

API docs available at: http://localhost:8000/docs

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
# Edit .env.local if needed

# Start development server
npm run dev
```

App available at: http://localhost:5173

---

## Docker Startup

The fastest way to run all services together.

```bash
# Copy and configure environment file first
cp backend/.env.example backend/.env

# Build and start all services
docker compose up --build

# Start in background
docker compose up -d --build
```

### Service URLs

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| MinIO Console | http://localhost:9001 |
| Qdrant Dashboard | http://localhost:6333/dashboard |

### Stop Services

```bash
docker compose down

# Remove volumes (clears all data)
docker compose down -v
```

---

## Development Roadmap

| Phase | Description | Status |
|---|---|---|
| 0 | Project Foundation | ✅ Complete |
| 1 | Backend + Frontend + Docker | ✅ Complete |
| 2 | Authentication | Planned |
| 3 | Document Management | Planned |
| 4 | RAG Pipeline | Planned |
| 5 | Workspace & AI Productivity | Planned |
| 6 | LangGraph Multi-Agent | Planned |
| 7 | Voice Interaction | Planned |
| 8 | GitHub Intelligence | Planned |
| 9 | External Integrations | Planned |
| 10 | Deployment & Optimization | Planned |

---

## License

MIT
