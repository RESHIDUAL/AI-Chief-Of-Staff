"""Regression test for the mandatory human-review memory policy."""

import unittest
from unittest.mock import patch

from backend.agents.pipeline_graph import run_agentic_pipeline


class TestHITLPolicy(unittest.TestCase):
    @patch("backend.agents.pipeline_graph.extract_from_transcript")
    def test_extractions_are_not_auto_embedded(self, extract):
        extract.return_value = {
            "decisions": [{"content": "Use Qdrant", "confidence_score": 0.99}],
            "tasks": [{"description": "Configure Qdrant", "owner": "Rohan", "confidence_score": 0.99}],
        }

        state = run_agentic_pipeline("m-1", "Review policy", "Rohan agreed to configure Qdrant.")

        self.assertEqual(state["status"], "reviewing")
        self.assertEqual(state["auto_approved_decisions"], [])
        self.assertEqual(state["auto_approved_tasks"], [])
        self.assertEqual(len(state["pending_review_decisions"]), 1)
        self.assertEqual(len(state["pending_review_tasks"]), 1)


if __name__ == "__main__":
    unittest.main()
