# AI Chief of Staff — Production Operational Runbook

## 1. System Overview & Architecture Layers

| Layer | Service | Deployment | Monitoring Health Endpoint |
|-------|---------|------------|----------------------------|
| Layer 1: Ingestion | Google ADK Trigger / Cloud Pub/Sub | GCP Cloud Pub/Sub Push | `POST /api/v1/ingest/pubsub` |
| Layer 2: Orchestration | Ingestion Orchestrator & LangGraph | GCP Cloud Run (`cos-backend`) | `GET /health` |
| Layer 3: Persistence | Qdrant Cloud (Vector) + PostgreSQL (SQL) | Qdrant Cloud + Cloud SQL | `GET /api/v1/review/stats` |
| Layer 4: HITL Review | React Review Portal | GCP Cloud Run (`cos-frontend`) | Port 3000 |
| Layer 5: User Interface | React Dashboard & RAG Memory Chat | GCP Cloud Run (`cos-frontend`) | Port 3000 |

---

## 2. Health Monitoring & Alerting

### Health Probes:
- **Backend Health Check**: `https://cos-backend.run.app/health` -> Expects `{"status": "ok"}`
- **Qdrant Health Check**: `https://<qdrant-cluster>.cloud.qdrant.io/healthz` -> Expects HTTP 200 OK

### Logging & Auditing:
- Logs are ingested into **GCP Cloud Logging** under `resource.type="cloud_run_revision"`.
- Application exceptions are reported via **GCP Error Reporting**.

---

## 3. Database Maintenance & Backup Strategy

### PostgreSQL (Cloud SQL):
- **Automated Backups**: Daily at 02:00 UTC with 7-day point-in-time recovery (PITR).
- **Manual Migration Run**: `alembic upgrade head`

### Qdrant Vector Collection:
- **Snapshots**: Trigger daily snapshots via Qdrant Cloud dashboard.
- **Reconciliation Scan**: Execute `GET /api/v1/review/stats` or call `reconcile_stores(db)` in python to detect and repair drift between PostgreSQL records and Qdrant points.

---

## 4. Emergency Procedures & Rollbacks

### Cloud Run Deployment Rollback:
```bash
gcloud run services update-traffic cos-backend --to-revisions=PREVIOUS_REVISION_NAME=100
```

### Clearing Dead Letter Queue:
If Pub/Sub push fails repeatedly:
```bash
curl -X DELETE https://cos-backend.run.app/api/v1/ingest/dlq
```
