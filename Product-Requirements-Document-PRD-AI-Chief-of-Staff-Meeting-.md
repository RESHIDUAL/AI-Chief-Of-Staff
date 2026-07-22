# Product Requirements Document (PRD): AI Chief of Staff & Meeting Command Center

## 1. Executive Summary
The **AI Chief of Staff** is a production-grade, multi-agent organizational memory system designed to capture, categorize, and retrieve meeting intelligence. Unlike standard summarization tools, this system treats **Decisions** and **Tasks** as distinct data entities. Built on the Google ADK, Lyzr SDK, and Qdrant, it features a self-improving "Correction Feedback Loop" where human oversight directly updates the system's semantic memory, ensuring long-term accuracy and trust.

## 2. Problem Statement
Organizations suffer from "organizational amnesia" where critical decisions are lost within lengthy meeting transcripts. Existing tools often collapse action items and decisions into generic summaries, leading to unclear ownership and lost context. Furthermore, most AI meeting assistants are one-shot pipelines; they do not learn from human corrections, meaning errors persist in the organizational memory indefinitely.

## 3. Goals & Objectives
*   **Capture Decisions:** Extract decisions as first-class, separately-typed artifacts.
*   **Self-Improving Memory:** Implement a feedback loop where human corrections re-trigger vector embeddings.
*   **Enterprise-Grade Security:** Ensure sensitive data is only accessible to authorized users via Role-Based Access Control (RBAC).
*   **Reliable Retrieval:** Use a hybrid storage approach (Vector + Relational) to balance semantic search with strict metadata filtering.

## 4. Target Users / Stakeholders
*   **Executive Leadership:** To track high-level decisions across departments.
*   **Project Managers:** To manage verified action items, owners, and deadlines.
*   **Chiefs of Staff:** To oversee organizational alignment and verify AI extractions.
*   **Context:** Built for **mid-to-large enterprises** running frequent recurring meetings where knowledge compounding is critical.

## 5. Functional Requirements
| ID | Requirement | Acceptance criteria |
|---|---|---|
| FR-01 | Ingest transcripts from manual paste, Drive, or authenticated Pub/Sub. | A transcript creates one deduplicated meeting pipeline; unauthenticated direct ingestion is rejected. |
| FR-02 | Extract decisions and tasks as distinct typed streams. | Valid output conforms to the defined JSON schema; non-committal dialogue returns empty arrays. |
| FR-03 | Require Human-in-the-Loop review before memory commitment. | No extracted item is embedded or queryable until an authorized manager approves it. |
| FR-04 | Re-embed approved items after a human correction. | The same Qdrant point ID is upserted with a changed embedding and an audit entry is created. |
| FR-05 | Provide conversational retrieval over approved organizational memory. | Every answer is grounded only in retrieved, approved items and includes source citations. |
| FR-06 | Enforce RBAC and group access at retrieval time. | A user cannot receive content whose access level or allowed groups exclude them, including fallback scans. |
| FR-07 | Record operational traces for agent and pipeline calls. | Each extraction/RAG call records latency, token estimates, model, and prompt fingerprint. |

## 6. Non-Functional Requirements
| ID | Requirement | Acceptance criteria |
|---|---|---|
| NFR-01 | Latency | Transcript-to-review output completes in under 60 seconds at the p95 target. |
| NFR-02 | Retrieval performance | Approved-memory retrieval completes in under 3 seconds at the p95 target. |
| NFR-03 | Scalability | The service supports 50+ meetings per organization per day with deduplication. |
| NFR-04 | Integrity | PostgreSQL and Qdrant identifiers are reconciled and corrections are auditable. |
| NFR-05 | Security | TLS 1.3 in transit, AES-256 encryption at rest, authenticated ingress, rate limiting, input validation, and least-privilege access are enforced by deployment and application controls. |
| NFR-06 | Observability | OpenTelemetry spans are exported to an OTLP-compatible collector; console export is development-only. |

## 7. System Architecture Overview
The system is organized into five distinct layers:
1.  **Ingestion Layer:** Google ADK Trigger (Pub/Sub) monitors for new transcripts.
2.  **Agentic Orchestration Layer:** Four specialized agents (Ingestion, Extraction, Memory, RAG Chat) coordinated via Lyzr SDK and LangGraph.
3.  **Persistence & Memory Layer:** Dual-store strategy using Qdrant (Semantic Memory) and PostgreSQL (Structured Metadata).
4.  **Human-in-the-Loop Review Layer:** React-based portal for data verification and feedback loop triggering.
5.  **User Interface Layer:** Dashboard and Chat UI for organizational memory interaction.

### Access Control (RBAC)
The system implements role-based filtering on retrieval to ensure data privacy. This works via Qdrant payload metadata filtering enforced at the **RAG Chat Agent's** query layer. This ensures that sensitive organizational decisions (e.g., HR or leadership-only context) are excluded from general-access queries by matching user role tags against vector payload metadata.

## 8. Tech Stack
*   **Orchestration:** Google ADK, Lyzr SDK, LangGraph, Python.
*   **AI Models:** OpenAI GPT-4o (Extraction/Reasoning), Sentence-Transformers (Embeddings).
*   **Databases:** Qdrant (Vector DB with HNSW indexing/gRPC), PostgreSQL (Relational DB).
*   **Frontend:** React, Tailwind CSS, Lucide React, Framer Motion, LangGraph SDK.
*   **Infrastructure:** Google Workspace SDK, Cloud Pub/Sub.

## 9. Data Requirements
*   **Decisions Schema:** Content, Meeting ID, Timestamp, Participants, Access Tags.
*   **Tasks Schema:** Task Description, Owner, Deadline, Status, Meeting ID.
*   **Vector Payload:** Every point in Qdrant must include `allowed_groups` or `access_level` for RBAC filtering.

## 10. API Specifications
*   **Ingestion API:** Receives Pub/Sub events from Google Workspace.
*   **Review API:** Serves raw extractions to the HITL portal and receives verified corrections.
*   **Query API:** Handles natural language queries, injecting user session/role data into the RAG Chat Agent.

## 11. Security Requirements
*   **Authentication:** Integration with Google Workspace OAuth; a signed JWT is required for user-facing APIs. Pub/Sub push requests must supply a gateway-managed secret (or verified OIDC identity in the production gateway).
*   **Authorization:** Role-Based Access Control (RBAC) mapped to organizational groups. Governance mutations require manager role or higher.
*   **Gateway:** An API gateway/Cloud Load Balancer is the sole public ingress. It terminates TLS 1.3, applies WAF/OWASP protections, per-client throttling, request-size limits, and forwards only approved routes to the backend.
*   **Data Protection:** AES-256 encryption at rest is required for PostgreSQL and Qdrant managed storage; TLS 1.3 is required for all external and service-to-service connections. Secrets are injected from a secret manager and never committed to source control.
*   **Application Controls:** Pydantic validates request shapes and size limits; the API applies rate limits, secure response headers, request correlation IDs, and Qdrant metadata filters.

## 12. Deployment & Infrastructure
*   **Cloud:** Google Cloud Platform (GCP).
*   **Containerization:** Dockerized agent services.
*   **CI/CD:** Automated testing for extraction accuracy and RBAC filter validation.

## 13. Success Metrics
*   **Target:** Reduce manual meeting-notes preparation and follow-up time by ~70%.
*   **Target:** Achieve a 95%+ accuracy rate for "Verified Tasks" after the first 30 days of feedback loop training.
*   **Target:** Maintain a retrieval latency of under 3 seconds for natural language queries against organizational memory.

## 14. Timeline & Milestones
*   **Phase 1:** Ingestion and Extraction Agent development (Decisions vs. Tasks).
*   **Phase 2:** Persistence Layer setup (Qdrant + PostgreSQL) and RBAC implementation.
*   **Phase 3:** HITL Review Portal and Correction Feedback Loop integration.
*   **Phase 4:** RAG Chat Interface and User Dashboard launch.
*   **Phase 5:** Advanced noise reduction and "Cleaning Agent" implementation for low-quality audio transcripts.

## 15. Reliability & Scale
*   **Extraction Accuracy:** To prevent the HITL portal from becoming a bottleneck, the Extraction Agent assigns a confidence score to each item. High-confidence items can be flagged for "Auto-Approve" in future iterations, while low-confidence items are highlighted for manual review.
*   **System Latency:** The target latency from transcript upload to reviewable output is **60 seconds**, accounting for multi-agent reasoning and embedding generation.
*   **Scaling Strategy:** If an organization exceeds 50 meetings a day, the system utilizes LangGraph's state management to queue reviews. The HITL portal supports "Batch Approval" to prevent the Chief of Staff from becoming a bottleneck.

## 16. Open Questions & Risks
*   **Transcript Quality:** Highly noisy transcripts may lead to poor extraction. 
    *   *Mitigation:* A "Cleaning Agent" is proposed as a **Phase 5 / Future Enhancement** to preprocess transcripts before they reach the Extraction Agent.
*   **Feedback Loop Latency:** Re-embedding large volumes of corrected data.
    *   *Mitigation:* Use Qdrant's asynchronous upsert capabilities to ensure the UI remains responsive.

## 17. Prompt Engineering Specification (CRISPE)

Both Lyzr agents use version-controlled CRISPE prompts in the application source.

| Agent | Capacity and insight | Response constraints | Examples and evaluation |
|---|---|---|---|
| Extraction Agent | Organizational-intelligence analyst processing only the supplied transcript. | JSON-only output; separate `decisions` and `tasks`; no placeholders; unknown fields are empty; confidence below 0.50 is omitted. | Few-shot examples calibrate explicit decisions, tasks, owners, deadlines, access level, and conservative extraction. |
| RAG Chat Agent | Executive memory assistant using only retrieved approved context. | No hallucinations; entity-specific filtering; distinguish tasks from decisions; cite meeting names. | Fallback synthesis applies the same entity guardrails when the external model is unavailable. |

Prompt fingerprints, rather than raw prompts or transcript data, are attached to observability spans to detect deployed prompt-version changes without exposing meeting content.

## 18. LLM Observability and Tracing

The orchestration layer emits OpenTelemetry spans for extraction, RAG synthesis, and every pipeline node. Each span includes `meeting_id` or `session_id`, model identifier, latency, estimated prompt/completion token counts, and prompt fingerprint. Production sets `OTEL_EXPORTER_OTLP_ENDPOINT` to an OTLP collector (such as Arize Phoenix, Grafana Tempo, or Jaeger); development may use console export. Alerts should track p95 latency, extraction failures, empty-result rate, token volume, and unexpected prompt fingerprints.

## 19. Requirement Traceability Matrix

| Requirement | Architecture component | Primary implementation / verification |
|---|---|---|
| FR-01 | API Gateway, Ingestion Layer | authenticated ingest/Pub/Sub routes; deduplication tests |
| FR-02 | Extraction Agent | CRISPE schema and extraction tests |
| FR-03 | HITL Review Layer, Memory Agent | review approval route and no-auto-embed pipeline test |
| FR-04 | Memory Agent, PostgreSQL, Qdrant | correction feedback-loop test |
| FR-05 | RAG Chat Agent, Qdrant | query route and citation response test |
| FR-06 | Auth/RBAC middleware, Qdrant | RBAC filtering tests |
| FR-07 / NFR-06 | Observability layer | OpenTelemetry span/export configuration |
| NFR-01 / NFR-02 | Agentic Orchestration and RAG | latency benchmark tests |
| NFR-04 | Persistence Layer | reconciliation operation and audit trail |
| NFR-05 | API Gateway, Security middleware | gateway configuration and security integration tests |

## 20. Canonical Data Flow

`API Gateway → Ingestion Orchestrator → Extraction Agent → HITL Review Portal → Memory Agent → PostgreSQL + Qdrant → RAG Chat Agent`

The Ingestion Orchestrator has no direct Qdrant write path. The Memory Agent is the only component permitted to create, update, or delete vector embeddings.
