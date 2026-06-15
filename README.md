# AEKA — AI-Powered Enterprise Knowledge Assistant

> A production-grade, multi-agent knowledge assistant demonstrating end-to-end Full-Stack AI Engineering: from LangGraph orchestration and RAG pipelines to streaming React frontends, cloud deployment, and LLM observability.

![Architecture](docs/architecture.png)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Frontend (Next.js 14 + React)                          │
│  • Streaming chat (SSE) • Agent visualizer              │
│  • HITL review queue    • Cost/latency dashboard        │
└────────────────────────┬────────────────────────────────┘
                         │ REST + SSE + WebSocket
┌────────────────────────▼────────────────────────────────┐
│  Backend (FastAPI + Python 3.12)                        │
│  • LangGraph multi-agent orchestration                  │
│  • RAG pipeline (chunking → embedding → hybrid search)  │
│  • Evaluation & guardrails layer                        │
│  • MCP server (tool integrations)                       │
└───┬──────────┬──────────┬──────────┬───────────────────┘
    │          │          │          │
 PostgreSQL  pgvector    Redis    S3/MinIO
 (relational) (vectors)  (cache)  (documents)
```

## 🚀 Quick Start

```bash
# Prerequisites: Docker, Docker Compose, Node.js 20+, Python 3.12+

# Clone and start all services
git clone <repo-url> aeka && cd aeka
cp .env.example .env  # Add your API keys

# Start everything
docker compose up -d

# Backend available at http://localhost:8000
# Frontend available at http://localhost:3000
# API docs at http://localhost:8000/docs
```

## 📁 Project Structure

```
aeka/
├── backend/              # FastAPI + LangGraph + RAG
│   ├── app/
│   │   ├── api/          # REST endpoints
│   │   ├── agents/       # LangGraph multi-agent system
│   │   ├── services/     # Business logic (ingestion, retrieval, LLM)
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── mcp/          # MCP server & tool definitions
│   │   └── core/         # Config, dependencies, middleware
│   └── tests/
├── frontend/             # Next.js 14 + React + Zustand
│   └── src/
│       ├── app/          # App Router pages
│       ├── components/   # UI components
│       ├── stores/       # Zustand state
│       └── hooks/        # Custom hooks (SSE, WebSocket)
├── infrastructure/       # Docker, Terraform, CI/CD
│   ├── docker/
│   ├── terraform/
│   └── observability/
└── docs/                 # Architecture diagrams & ADRs
```

## 🧠 Key Features

### Multi-Agent Orchestration (LangGraph)
- **Router Agent** — classifies query intent, delegates to specialists
- **Research Agent** — performs RAG retrieval and synthesizes cited answers
- **Validator Agent** — detects hallucinations by cross-referencing source chunks
- **Escalation Agent** — routes low-confidence answers to human reviewers (HITL)

### RAG Pipeline
- Multiple chunking strategies (fixed-size, semantic, recursive)
- Hybrid search: pgvector cosine similarity + BM25 keyword ranking
- Token budget management and context window optimization
- Embedding cache with Redis

### AI-Native Frontend
- Real-time streaming chat via Server-Sent Events
- Agent activity visualizer (shows reasoning steps live)
- Human-in-the-Loop admin panel with approval workflows
- LLM cost/latency monitoring dashboard

### Production Infrastructure
- Multi-stage Docker builds with health checks
- AWS deployment (ECS Fargate, RDS, ElastiCache, S3, CloudFront)
- OpenTelemetry distributed tracing with LLM-specific metrics
- CI/CD with automated testing and staged deployments

## 🔑 Skills Demonstrated

| Category | Technologies |
|----------|-------------|
| AI/LLM Frameworks | LangGraph, LangChain, OpenAI/Anthropic/Gemini APIs |
| Vector Databases | pgvector (PostgreSQL) |
| Backend | Python, FastAPI, async/await, MCP |
| Frontend | React, Next.js 14, Zustand, SSE, WebSocket |
| Databases | PostgreSQL, Redis, S3 |
| DevOps | Docker, AWS (ECS/RDS/S3), Terraform, GitHub Actions |
| Observability | OpenTelemetry, Grafana, structured logging |
| AI Quality | Hallucination detection, guardrails, eval frameworks |

## 📖 Phase-by-Phase Build Guide

Each phase is independently runnable. See individual READMEs:

1. **[Backend & RAG](backend/README.md)** — FastAPI + document pipeline + hybrid search
2. **[Multi-Agent System](backend/app/agents/README.md)** — LangGraph orchestration + HITL
3. **[Frontend](frontend/README.md)** — Next.js streaming chat + admin panel
4. **[Infrastructure](infrastructure/README.md)** — Docker + AWS + CI/CD + observability
5. **[MCP & Evaluation](backend/app/mcp/README.md)** — Tool server + eval harness

## 📄 License

MIT
