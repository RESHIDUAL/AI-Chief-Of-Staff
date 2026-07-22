# AI Chief of Staff (Executive Intelligence & Memory Automation Platform)

An enterprise executive automation platform engineered to capture, structure, verify, and recall organizational memory with sub-second accuracy. It converts unstructured meeting dialogue into verified decisions and tasks, enforces strict Role-Based Access Control (RBAC), and serves executive queries with precision.

---

## Demo Video

[![Watch the demo](https://img.shields.io/badge/Watch%20Demo-Google%20Drive-blue?style=for-the-badge&logo=googledrive&logoColor=white)](https://drive.google.com/file/d/1j7ogzK03_VOVbIMK7wgl1ZGRKuvV5owJ/view?usp=sharing)

Click the button above to watch the walkthrough video.

---

## Key Capabilities & Features

- **Google OAuth 2.0 & JWT Authentication**: Enterprise workspace authentication with URL fragment token passing (`#token=...`), protecting credentials from access logs.
- **Zero Fallback Policy Extraction Agent**: Extracts real entities (Rohan, Neha, Kabir, Ananya, Vikram, Sneha, Amit, Sarah) and explicit deadlines directly from dialogue without generic mock placeholders.
- **Human in the Loop (HITL) Review Portal**: Provides an approval interface with 1 click decision and task verification, inline editing, and meeting session deletion.
- **Dual Store Persistence Architecture**: Syncs verified items to PostgreSQL for structured metadata and audit logs, and Qdrant Cloud for 384 dimensional vector embeddings.
- **Precision RAG Memory Agent**: Serves natural language executive queries using hybrid vector and keyword scoring ($0.6 \cdot S_{\text{vector}} + 0.4 \cdot S_{\text{keyword}}$), entity pre-filtering, and meeting citations.
- **Automated Google Drive Sync**: Background polling worker and 1 click Drive sync button to automatically ingest transcript files (`.txt`, `.docx`, Google Docs) from shared Google Drive folders.
- **Pipeline Level Deduplication**: Prevents duplicate ingestion when files are re-scanned or re-submitted.
- **Cloud Ready Containerization**: Production Dockerfile included for 24/7 deployment on Google Cloud Run, Render, or AWS.

---

## 5 Layer System Architecture

```
[Layer 1: Ingestion Engine]
   |  Manual Transcript Submission
   |  Google Drive Folder Polling Worker (drive_sync_worker.py)
   |  GCP Pub/Sub Push Webhook (/api/v1/ingest/pubsub)
   v
[Layer 2: Extraction & Processing]
   |  Lyzr Extraction Agent
   |  Rule Based Dialogue Parser (_extract_from_text_directly)
   |  Zero Fallback Entity & Deadline Formatter
   v
[Layer 3: Security & RBAC Enforcement]
   |  Google OAuth 2.0 Login (/api/v1/auth/login/google)
   |  JWT Token Issuance & Signature Verification
   |  Role Gatekeeper (General Access vs Leadership Only)
   v
[Layer 4: Storage & HITL Governance]
   |  HITL Review Portal (1 Click Approve / Edit / Delete)
   |  Dual Store PostgreSQL (Relational DB) + Qdrant Cloud (Vector DB)
   |  Correction Audit Loop (/api/v1/review/edit/{point_id})
   v
[Layer 5: RAG Intelligence Interface]
   |  Conversational Memory RAG Agent
   |  Entity Precision Filter (Person & Item Type Scoping)
   |  Meeting Citation & Similarity Score Renderer
```

---

## Quick Start Guide

### Prerequisites
- Python 3.12+
- Node.js 18+ and npm
- Qdrant Cloud Cluster (`cloud.qdrant.io`)
- Google Cloud OAuth 2.0 Credentials & Service Account JSON

### 1. Installation
Clone the repository and install dependencies:

```bash
# Install Python backend dependencies
pip install -r requirements.txt

# Install React frontend dependencies
cd frontend
npm install
cd ..
```

### 2. Environment Configuration
Create a `.env` file in the root directory:

```env
# Lyzr SDK Keys
LYZR_AGENT_API_KEY="sk-default-xxxx"
LYZR_EXTRACTION_AGENT_ID="6a5f492111fc9a484e9584bb"
LYZR_RAG_AGENT_ID="6a5f4bfe7976aaac9b9a5f2b"

# Qdrant Vector Cloud
QDRANT_URL=https://your-cluster.aws.cloud.qdrant.io
QDRANT_API_KEY="your-qdrant-api-key"
QDRANT_COLLECTION_NAME=org_memory

# Google OAuth 2.0 & Cloud Drive Integration
GOOGLE_CLIENT_ID="your-google-client-id.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET="your-google-client-secret"
GOOGLE_APPLICATION_CREDENTIALS="credentials/service-account.json"
GOOGLE_DRIVE_FOLDER_ID="your-google-drive-folder-id"
GOOGLE_PUBSUB_PROJECT_ID="your-gcp-project-id"
```

### 3. Launch Server Components

#### Terminal 1: FastAPI Backend API (Port 8000)
```bash
python -m uvicorn backend.main:app --reload --port 8000
```

#### Terminal 2: React Vite Frontend (Port 3000)
```bash
cd frontend
npm run dev
```

#### Terminal 3: (Optional) Google Drive Background Polling Worker
```bash
python -m backend.agents.drive_sync_worker
```

Open your browser at `http://localhost:3000` to access the application.

---

## API Reference Overview

| HTTP Method | Endpoint Path | Description | Access Control |
|---|---|---|---|
| `GET` | `/api/v1/auth/login/google` | Redirect to Google OAuth consent screen | Public |
| `GET` | `/api/v1/auth/callback` | OAuth code exchange and JWT issuance | Public |
| `POST` | `/api/v1/auth/login/demo` | Development mode demo login | Public (Dev) |
| `POST` | `/api/v1/ingest/transcript` | Ingest raw transcript dialogue text | Authenticated |
| `POST` | `/api/v1/ingest/drive-sync` | Trigger manual scan of Google Drive folder | Authenticated |
| `GET` | `/api/v1/review/pending-sessions` | Fetch active meeting ingestion sessions | Authenticated |
| `POST` | `/api/v1/review/approve/decision/{id}` | Approve decision and commit to vector memory | Authenticated |
| `POST` | `/api/v1/review/approve/task/{id}` | Approve task and commit to vector memory | Authenticated |
| `DELETE` | `/api/v1/review/session/{id}` | Delete meeting session from active memory | Authenticated |
| `POST` | `/api/v1/query/` | Query organizational memory via RAG Agent | Authenticated (RBAC Scoped) |

---

## Verification & Production Build

The production build has been verified cleanly:

- **Frontend Compilation**: `npm run build` executed with 0 errors (Vite 6.4.3 bundle size 480 kB).
- **Backend Core**: Verified Python 3.12 routes, Pydantic v2 validation, and database connections.
- **Drive Ingestion & Deduplication**: Verified Google Drive API sync and pipeline deduplication checks.

---
## Report

Saved in the report Folder.

---
## License & System Status

Designed for corporate executive automation and decision tracking. Built with Python FastAPI, React Vite, PostgreSQL, Qdrant Cloud, and Lyzr Agentic SDK.
