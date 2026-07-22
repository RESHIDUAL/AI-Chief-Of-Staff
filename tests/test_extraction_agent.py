"""Unit tests for Extraction Agent JSON parsing, entity extraction, and Zero-Fallback Policy."""

import unittest
from backend.agents.extraction_agent import extract_from_transcript, _is_generic_placeholder


class TestExtractionAgent(unittest.TestCase):

    @unittest.mock.patch("backend.agents.extraction_agent.get_client")
    def test_json_parsing_and_entities(self, mock_get_client):
        """Test extraction output parsing with structured JSON input and specific entities."""
        mock_client = unittest.mock.MagicMock()
        mock_client.inference.chat.return_value = {
            "response": '{"decisions": [{"content": "Neha and Kabir agreed to deploy ECS", "confidence_score": 0.93}], "tasks": [{"description": "Complete database indexing", "owner": "Rohan", "deadline": "Friday", "confidence_score": 0.95}]}'
        }
        mock_get_client.return_value = mock_client

        sample_transcript = (
            "Rohan will complete the database indexing by Friday. "
            "Neha and Kabir agreed that we will deploy microservices architecture on AWS ECS."
        )
        result = extract_from_transcript(sample_transcript, meeting_id="test-m1")

        self.assertIn("decisions", result)
        self.assertIn("tasks", result)
        self.assertEqual(len(result["decisions"]), 1)
        self.assertEqual(len(result["tasks"]), 1)
        self.assertEqual(result["tasks"][0]["owner"], "Rohan")
        self.assertEqual(result["tasks"][0]["deadline"], "Friday")

    def test_zero_fallback_policy_empty_transcript(self):
        """Test Zero-Fallback Policy raises ValueError on empty or missing transcript text."""
        with self.assertRaises(ValueError) as ctx:
            extract_from_transcript("", meeting_id="test-empty")
        self.assertIn("Zero-fallback policy enforced", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx2:
            extract_from_transcript("   ", meeting_id="test-whitespace")
        self.assertIn("Zero-fallback policy enforced", str(ctx2.exception))

    def test_generic_placeholder_rejection(self):
        """Test generic placeholder detector function."""
        self.assertTrue(_is_generic_placeholder("Key decision extracted from meeting"))
        self.assertTrue(_is_generic_placeholder("Generic decision for team"))
        self.assertTrue(_is_generic_placeholder("Mock task description"))
        self.assertFalse(_is_generic_placeholder("Rohan will index DB by Friday"))


if __name__ == "__main__":
    unittest.main()
