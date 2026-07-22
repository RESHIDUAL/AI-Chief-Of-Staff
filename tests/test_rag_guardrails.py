"""Unit test verifying RAG Chat Agent Enforcement Guardrails for Entity-Specific Precision."""

import unittest
from backend.agents.rag_chat_agent import answer_query, _extract_person_name_from_query


class TestRAGGuardrails(unittest.TestCase):

    def test_extract_person_name(self):
        """Verify person name extraction from queries."""
        self.assertEqual(_extract_person_name_from_query("What tasks are assigned to Vikram?"), "Vikram")
        self.assertEqual(_extract_person_name_from_query("Show decisions for Amit"), "Amit")
        self.assertEqual(_extract_person_name_from_query("What is Sneha's task?"), "Sneha")
        self.assertIsNone(_extract_person_name_from_query("Who was assigned to Coordinate with the external verification vendor?"))

    def test_entity_specific_precision_filtering(self):
        """Context with multiple people must filter out unmatching team members when a specific person is asked about."""
        multitarget_context = (
            "- (Standup) [task] Task: Vikram will finalize the contract paperwork by Thursday.\n"
            "- (Standup) [task] Task: Sarah will setup PostgreSQL schema by Friday.\n"
            "- (Standup) [decision] We decided to award interior fit-out to Vertex Solutions."
        )

        answer = answer_query("What tasks are assigned to Vikram?", context=multitarget_context)

        # Must include Vikram's task
        self.assertIn("Vikram", answer)

        # Must NOT dump Sarah's task
        self.assertNotIn("Sarah", answer)


if __name__ == "__main__":
    unittest.main()
