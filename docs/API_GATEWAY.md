# API Gateway Security Baseline

The backend must not be exposed directly in production. Place Google Cloud API Gateway, Cloud Armor + HTTPS Load Balancer, or an equivalent gateway in front of it.

Required gateway policy:

1. Terminate TLS 1.3 using a managed certificate and redirect HTTP to HTTPS.
2. Restrict backend ingress to the gateway identity/network; do not publish port 8000.
3. Apply WAF/OWASP managed rules, a 100 KB request-body limit, and a rate limit appropriate to the tenant (the application retains a second 120 requests/minute safety limit).
4. Require JWT authentication for `/api/v1/ingest/*`, `/api/v1/review/*`, and `/api/v1/query/*`; preserve the bearer token for backend verification.
5. For `/api/v1/ingest/pubsub`, attach the `X-Pubsub-Token` secret from the gateway/subscription. Configure the same value as `PUBSUB_WEBHOOK_TOKEN` through Secret Manager.
6. Configure Cloud SQL and Qdrant storage with provider-managed AES-256 encryption at rest, private networking, and TLS 1.3 connections.
7. Configure `OTEL_EXPORTER_OTLP_ENDPOINT` through Secret Manager and allow egress only to the approved collector.

The gateway is responsible for TLS and network boundaries; the application remains responsible for JWT validation, role checks, payload validation, RBAC retrieval filters, and audit logging.
