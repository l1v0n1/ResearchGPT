"""
Integration tests for the AI Research Agent.
"""
import os
import unittest
from unittest.mock import patch, MagicMock

from agent.planner import Planner
from agent.executor import Executor
from agent.model import ModelAPIWrapper
from agent.tools.web import WebScrapingTool
from agent.tools.documents import DocumentRetrievalTool

class TestIntegration(unittest.TestCase):
    """Integration tests for the agent system."""
    
    @patch("agent.tools.web.WebScrapingTool.search_google")
    @patch("agent.tools.web.WebScrapingTool.fetch_page")
    def test_basic_research_workflow(self, mock_fetch_page, mock_search_google):
        """Test the basic research workflow from planning to execution."""
        # Set up test environment
        os.environ["OPENAI_API_KEY"] = "test_key"
        
        # Set up mocks
        mock_search_google.return_value = [
            {
                "title": "Test Result",
                "url": "https://example.com/test",
                "snippet": "This is a test result"
            }
        ]
        
        mock_page = MagicMock()
        mock_page.dict.return_value = {
            "title": "Test Page",
            "content": "This is a test page with some content about quantum computing.",
            "url": "https://example.com/test"
        }
        mock_fetch_page.return_value = mock_page
        
        # Create test instances
        planner = Planner()
        executor = Executor()
        
        # Test query
        query = "What is quantum computing?"
        
        # Generate plan
        with patch.object(ModelAPIWrapper, 'generate_json') as mock_generate_json:
            # Mock the plan generation
            mock_generate_json.return_value = {
                "steps": [
                    {
                        "action": "search_web",
                        "parameters": {"query": "quantum computing definition and basics"},
                        "reasoning": "To find general information about quantum computing"
                    },
                    {
                        "action": "fetch_webpage",
                        "parameters": {"url": "https://example.com/test"},
                        "reasoning": "To get detailed information about quantum computing"
                    },
                    {
                        "action": "generate_summary",
                        "parameters": {},
                        "reasoning": "To create a comprehensive answer for the user"
                    }
                ]
            }
            
            plan = planner.create_plan(query)
            
            # Check that plan creation was called
            mock_generate_json.assert_called_once()
            
            # Check that plan has expected steps
            self.assertIsNotNone(plan)
            self.assertEqual(len(plan.steps), 3)
            self.assertEqual(plan.steps[0].action, "search_web")
            self.assertEqual(plan.steps[1].action, "fetch_webpage")
            self.assertEqual(plan.steps[2].action, "generate_summary")
        
        # Execute plan
        with patch.object(ModelAPIWrapper, 'generate_text') as mock_generate_text:
            # Mock the summary generation
            mock_generate_text.return_value = "Quantum computing is a type of computing that uses quantum phenomena."
            
            # Run with dry_run=False to test actual execution logic
            summary, context = executor.execute_plan(plan, dry_run=False)
            
            # Check that API was called for summary generation
            mock_generate_text.assert_called_once()
            
            # Check that tool methods were called
            mock_search_google.assert_called_once()
            mock_fetch_page.assert_called_once()
            
            # Check that we got a summary
            self.assertIsNotNone(summary)
            self.assertTrue(len(summary) > 0)
            
            # Check that context has results
            self.assertIn("result_search_web_0", context)
            self.assertIn("result_fetch_webpage_1", context)

if __name__ == "__main__":
    unittest.main() 