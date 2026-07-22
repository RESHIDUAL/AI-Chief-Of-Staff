"""Performance & Latency Benchmark Tests.

Validates PRD Non-Functional Requirements:
  - Latency: End-to-end processing under 60 seconds.
  - Query Latency: Natural language RAG query retrieval under 3 seconds.
"""

import time
import unittest
from backend.db.embeddings import embed_text
from backend.agents.pipeline_graph import run_agentic_pipeline


class TestPerformanceBenchmarks(unittest.TestCase):

    def test_rag_query_embedding_latency(self):
        """Embedding a query text must complete in under 500 milliseconds."""
        start = time.time()
        vec = embed_text("What database was chosen for organizational memory?")
        elapsed = time.time() - start

        self.assertEqual(len(vec), 384)
        self.assertLess(elapsed, 0.5, f"Query embedding took too long: {elapsed:.2f}s")

    def test_pipeline_execution_latency(self):
        """Full agentic pipeline execution must finish well within 60 seconds NFR limit."""
        transcript = (
            "Eshwar: We committed to using sentence-transformers for vector embeddings. "
            "Sarah will manage Qdrant Cloud deployment by Wednesday."
        )
        start = time.time()
        state = run_agentic_pipeline(
            meeting_id="perf-m1",
            meeting_name="Performance Test Sync",
            transcript=transcript,
        )
        elapsed = time.time() - start

        self.assertIn(state["status"], ("extracted", "committed", "reviewing", "failed"))
        self.assertLess(elapsed, 60.0, f"Pipeline execution exceeded 60s NFR target: {elapsed:.2f}s")


if __name__ == "__main__":
    unittest.main()
