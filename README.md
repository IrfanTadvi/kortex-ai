<div align="center">

# 🧠 AI Knowledge Copilot

### Enterprise-Grade RAG System with Multi-Agent Architecture

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

*A production-grade AI knowledge assistant that aggregates data from multiple sources and provides context-aware, source-grounded answers with enterprise-level accuracy.*

[Demo](#demo) · [Architecture](#architecture) · [Setup](#quick-start) · [API Docs](#api-documentation)

</div>

---

## 🎯 Overview

AI Knowledge Copilot is a scalable, enterprise-ready Retrieval-Augmented Generation (RAG) system that serves as an internal knowledge assistant. It ingests documents from multiple sources, processes them through an advanced retrieval pipeline, and generates accurate, cited responses using a multi-agent architecture.

**This is NOT a basic chatbot.** It's a production system with:
- Advanced hybrid retrieval (BM25 + Vector + Cross-Encoder re-ranking)
- Multi-agent architecture (Retriever → Reasoning → Answer Generator)
- Action layer for executable operations
- Premium glassmorphism UI with streaming responses
- Full observability with analytics dashboard

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 📄 **Multi-Format Ingestion** | PDF, DOCX, TXT with semantic chunking |
| 🔍 **Hybrid Search** | BM25 + Vector similarity with Reciprocal Rank Fusion |
| 🎯 **Cross-Encoder Re-ranking** | Precision re-ranking for top results |
| 🤖 **Multi-Agent Pipeline** | Retriever → Reasoning → Answer Generator |
| 💬 **Streaming Chat** | Real-time token-by-token response streaming |
| 📊 **Source Citations** | Every answer grounded with source references |
| 🔄 **Query Rewriting** | Intelligent query reformulation for better retrieval |
| 👤 **Role-Based Responses** | HR, Engineer, Manager, Executive personas |
| 🎬 **Action Layer** | Create tickets, schedule meetings, generate reports |
| 💾 **SQL Generation** | Natural language to SQL query conversion |
| 📈 **Analytics Dashboard** | Usage metrics, confidence tracking, latency monitoring |
| 🌙 **Premium UI** | Dark mode, glassmorphism, Framer Motion animations |
| 🐳 **Docker Ready** | One-command deployment with docker-compose |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js 14)                        │
│  ┌───────────┐ ┌──────────────┐ ┌───────────┐ ┌────────────────┐  │
│  │ Chat Panel│ │Document Mgmt │ │ SQL Panel │ │Analytics Board │  │
│  └───────────┘ └──────────────┘ └───────────┘ └────────────────┘  │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ REST API + SSE
┌────────────────────────────────┼────────────────────────────────────┐
│                        BACKEND (FastAPI)                             │
│  ┌─────────────────────────────┼───────────────────────────────┐   │
│  │              API Layer (Routes + Middleware)                  │   │
│  └─────────────────────────────┼───────────────────────────────┘   │
│                                │                                     │
│  ┌─────────────────────────────┼───────────────────────────────┐   │
│  │            MULTI-AGENT ORCHESTRATOR                           │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐  │   │
│  │  │  Retriever  │→ │  Reasoning   │→ │ Answer Generator  │  │   │
│  │  │   Agent     │  │    Agent     │  │      Agent        │  │   │
│  │  └─────────────┘  └──────────────┘  └───────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    RETRIEVAL ENGINE                            │  │
│  │  ┌──────────┐  ┌─────────────┐  ┌────────────┐  ┌────────┐ │  │
│  │  │  Query   │  │   Hybrid    │  │   Cross    │  │Context │ │  │
│  │  │ Rewriter │→ │   Search    │→ │  Encoder   │→ │Compress│ │  │
│  │  │          │  │(BM25+Vector)│  │  Reranker  │  │        │ │  │
│  │  └──────────┘  └─────────────┘  └────────────┘  └────────┘ │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌────────────────┐ ┌────────────────┐ ┌─────────────────────────┐ │
│  │  FAISS Vector  │ │   Embedding    │ │    LLM Client           │ │
│  │    Store       │ │   Manager      │ │  (OpenAI/Anthropic)     │ │
│  └────────────────┘ └────────────────┘ └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### Agent Architecture

1. **Retriever Agent** – Query rewriting, hybrid search, cross-encoder re-ranking
2. **Reasoning Agent** – Context analysis, confidence assessment, answer planning
3. **Answer Generator Agent** – Source-cited response generation with role adaptation

### Retrieval Pipeline

```
User Query → Query Rewriting → Hybrid Search (BM25 ∪ Vector) → RRF Fusion → Cross-Encoder Re-ranking → Context Compression → LLM Generation
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- OpenAI API key (or Anthropic)

### 1. Clone & Setup Environment

```bash
git clone https://github.com/your-username/ai-knowledge-copilot.git
cd ai-knowledge-copilot

# Copy environment config
cp .env.example .env
# Edit .env with your API keys
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

### 4. Access the Application

- **Frontend:** http://localhost:3000
- **API Docs:** http://localhost:8000/api/docs
- **ReDoc:** http://localhost:8000/api/redoc

### Docker Deployment

```bash
# Build and run all services
docker-compose up --build

# Or run in detached mode
docker-compose up -d
```

---

## 📁 Project Structure

```
ai-knowledge-copilot/
├── backend/
│   ├── app/
│   │   ├── api/                 # REST API routes
│   │   │   ├── chat.py         # Chat endpoints + streaming
│   │   │   ├── documents.py    # Document management
│   │   │   ├── sessions.py     # Chat session management
│   │   │   ├── sql_query.py    # NL-to-SQL endpoint
│   │   │   └── analytics.py    # Usage metrics
│   │   ├── agents/             # Multi-agent system
│   │   │   ├── orchestrator.py # Agent pipeline orchestration
│   │   │   ├── actions.py      # Action layer (ticket, meeting, etc.)
│   │   │   └── sql_agent.py    # SQL generation agent
│   │   ├── core/               # Core infrastructure
│   │   │   ├── database.py     # SQLAlchemy models & session
│   │   │   ├── document_processor.py  # Ingestion & chunking
│   │   │   ├── embeddings.py   # Embedding generation
│   │   │   ├── llm_client.py   # LLM provider abstraction
│   │   │   ├── retrieval.py    # Hybrid search & re-ranking
│   │   │   └── vector_store.py # FAISS vector database
│   │   ├── models/
│   │   │   └── schemas.py      # Pydantic request/response models
│   │   ├── config.py           # Application configuration
│   │   └── main.py             # FastAPI app entry point
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/                # Next.js app router
│   │   ├── components/         # React components
│   │   │   ├── Sidebar.tsx     # Navigation sidebar
│   │   │   ├── ChatPanel.tsx   # Chat interface
│   │   │   ├── DocumentPanel.tsx    # Document management
│   │   │   ├── AnalyticsDashboard.tsx # Metrics dashboard
│   │   │   └── SQLPanel.tsx    # SQL query interface
│   │   └── lib/
│   │       └── api.ts          # API client
│   ├── package.json
│   └── tailwind.config.js
├── sample_data/                # Test documents
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
├── .env.example
└── README.md
```

---

## 🔌 API Documentation

### Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/chat` | Send message (supports streaming) |

### Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/documents/upload` | Upload document |
| GET | `/api/v1/documents` | List all documents |
| DELETE | `/api/v1/documents/{id}` | Delete document |
| POST | `/api/v1/documents/summarize` | Summarize document |
| POST | `/api/v1/documents/ingest-mock` | Import mock data |

### Sessions

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/sessions` | List sessions |
| POST | `/api/v1/sessions` | Create session |
| GET | `/api/v1/sessions/{id}` | Get session history |
| DELETE | `/api/v1/sessions/{id}` | Delete session |

### SQL

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/sql/query` | Execute NL-to-SQL query |

### Analytics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/analytics` | Get system metrics |
| POST | `/api/v1/analytics/feedback` | Submit feedback |

---

## ⚙️ Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_PROVIDER` | LLM provider (openai/anthropic) | openai |
| `LLM_MODEL` | Model name | gpt-4o |
| `EMBEDDING_PROVIDER` | Embedding provider | sentence-transformers |
| `EMBEDDING_MODEL` | Embedding model name | all-MiniLM-L6-v2 |
| `VECTOR_DB_TYPE` | Vector database type | faiss |
| `CHUNK_SIZE` | Target chunk size (tokens) | 512 |
| `HYBRID_SEARCH_ALPHA` | Vector weight in hybrid search | 0.7 |
| `TOP_K_RESULTS` | Initial retrieval count | 10 |
| `RERANK_TOP_K` | Final results after re-ranking | 5 |

---

## 🧪 Testing

```bash
cd backend

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

---

## 🔮 Advanced Features

### Action Layer
The system can detect actionable intents and execute simulated enterprise operations:

```
User: "Create a support ticket for the login page being slow"
→ System detects action intent
→ Extracts parameters (title, priority, description)
→ Simulates ticket creation
→ Returns: ✅ Ticket TKT-A3F2B1 created successfully!
```

### Role-Based Responses
Responses adapt based on the selected role:
- **Engineer**: Technical details, code examples, system specifics
- **HR**: Policy-focused, empathetic, employee-centric
- **Manager**: Strategic, metrics-driven, actionable
- **Executive**: High-level summaries, KPIs, business impact

### Query Rewriting
Ambiguous queries are automatically reformulated:
```
Original: "What about the time off thing?"
Rewritten: "What is the company paid time off PTO policy and how many days do employees receive?"
```

---

## 📊 Evaluation

The system includes built-in evaluation through:
- **Confidence Scoring**: Each response includes a confidence score (0-100%)
- **Source Grounding**: Answers are always tied to specific source documents
- **Query Logging**: All queries logged with latency, confidence, and retrieval metrics
- **User Feedback**: Thumbs up/down feedback captured for continuous improvement

---

## 🛣️ Roadmap

- [ ] Pinecone cloud vector store integration
- [ ] Multi-modal support (images, tables from PDFs)
- [ ] Fine-tuned embedding models
- [ ] Advanced caching layer (semantic cache)
- [ ] WebSocket for real-time collaboration
- [ ] RBAC with JWT authentication
- [ ] Kubernetes Helm charts
- [ ] Automated evaluation with RAGAS

---

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

---

<div align="center">
  <sub>Built with ❤️ for enterprise knowledge management</sub>
</div>
