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
*   **Automated Ingestion:** Monitor Google Drive/Meet for new transcripts via Google ADK.
*   **Dual-Stream Extraction:** Separate "Decisions Stream" (the 'why') from "Tasks Stream" (the 'who/what/when').
*   **Human-in-the-Loop (HITL) Review:** A portal for reviewing and editing extracted data before final commitment.
*   **Correction Feedback Loop:** Automatically re-embed and update Qdrant vector points when a human modifies a decision or task.
*   **Conversational RAG Interface:** A chat-based dashboard for querying historical meeting context.
*   **RBAC Enforcement:** Filter all retrieval results based on the querying user's permissions.

## 6. Non-Functional Requirements
*   **Latency:** The system targets an end-to-end processing time (from transcript upload to reviewable output) of **60 seconds**.
*   **Scalability:** Support for 50+ meetings per day per organization via asynchronous agent orchestration.
*   **Reliability:** 100% data integrity for task ownership and deadlines via PostgreSQL.
*   **Security:** Metadata-level payload filtering in the vector database.

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
*   **Authentication:** Integration with Google Workspace OAuth.
*   **Authorization:** Role-Based Access Control (RBAC) mapped to organizational groups.
*   **Data Protection:** Encryption at rest for PostgreSQL and Qdrant; gRPC for secure internal communication.

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