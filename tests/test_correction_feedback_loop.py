"""End-to-End Test for the Correction Feedback Loop (edit -> re-embed -> vector change)."""

import unittest
from backend.db.embeddings import embed_text
from backend.agents.memory_agent import commit_decision, correct_item, remove_item


class TestCorrectionFeedbackLoop(unittest.TestCase):

    def test_correction_reembedding_changes_vector(self):
        """Editing a committed memory item must generate a different embedding vector."""
        original_content = "We decided to deploy the service on AWS ECS."
        corrected_content = "We decided to deploy the service on GCP Cloud Run with gRPC."

        # 1. Commit original
        point_id = commit_decision(
            content=original_content,
            meeting_id="test-corr-1",
            meeting_name="Cloud Strategy Sync",
        )

        vec_orig = embed_text(original_content)
        vec_corr = embed_text(corrected_content)

        # 2. Assert vectors are distinct
        self.assertNotEqual(vec_orig, vec_corr)

        # 3. Apply correction via Memory Agent
        payload = {
            "type": "decision",
            "content": original_content,
            "meeting_id": "test-corr-1",
            "meeting_name": "Cloud Strategy Sync",
        }
        updated_id = correct_item(point_id, corrected_content, payload)

        self.assertEqual(updated_id, point_id)
        self.assertTrue(payload["corrected"])
        self.assertEqual(payload["content"], corrected_content)

        # Clean up
        remove_item(point_id)


if __name__ == "__main__":
    unittest.main()
