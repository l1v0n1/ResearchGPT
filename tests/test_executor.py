import unittest
from unittest.mock import patch, MagicMock
import json
import re
from pathlib import Path

from agent.executor import Executor
from agent.planner import ActionStep, Plan

class TestExecutor(unittest.TestCase):
    
    def setUp(self):
        # Create an executor instance for testing
        self.executor = Executor()
        
        # Mock the components to avoid making actual external calls
        self.executor.model = MagicMock()
        self.executor.memory = MagicMock()
        self.executor.web_tool = MagicMock()
        self.executor.doc_tool = MagicMock()
    
    def test_execute_step_search_web(self):
        # Create a search_web step
        step = ActionStep(
            action="search_web",
            parameters={"query": "test query"},
            reasoning="Test search"
        )
        
        # Mock search_google to return some results
        mock_results = [{"title": "Test", "url": "https://example.com"}]
        self.executor.web_tool.search_google.return_value = mock_results
        
        # Execute the step
        result = self.executor._execute_step(step)
        
        # Verify the correct method was called with the right parameters
        self.executor.web_tool.search_google.assert_called_once_with("test query")
        self.assertEqual(result, mock_results)
    
    def test_execute_step_analyze_webpage_web_url(self):
        # Create an analyze_webpage step for a web URL
        step = ActionStep(
            action="analyze_webpage",
            parameters={"url": "https://example.com/article"},
            reasoning="Analyze article content"
        )
        
        # Mock is_local_file_reference to return False (indicating web URL)
        self.executor._is_local_file_reference = MagicMock(return_value=False)
        
        # Mock analyze_webpage to return sample data
        mock_result = {
            "url": "https://example.com/article",
            "title": "Test Article",
            "success": True,
            "main_content": "Article content",
            "structure": {
                "headings": [{"level": 1, "text": "Article Title"}],
                "lists": [],
                "tables": []
            }
        }
        self.executor.web_tool.analyze_webpage.return_value = mock_result
        
        # Execute the step
        result = self.executor._execute_step(step)
        
        # Verify the correct method was called with the right parameters
        self.executor.web_tool.analyze_webpage.assert_called_once_with("https://example.com/article")
        self.assertEqual(result, mock_result)
    
    def test_execute_step_analyze_webpage_local_file(self):
        # Create an analyze_webpage step for a local file
        step = ActionStep(
            action="analyze_webpage",
            parameters={"url": "documents/test.md"},
            reasoning="Analyze local file"
        )
        
        # Mock is_local_file_reference to return True
        self.executor._is_local_file_reference = MagicMock(return_value=True)
        
        # Mock extract_file_path
        self.executor._extract_file_path = MagicMock(return_value="documents/test.md")
        
        # Mock _get_document_as_webpage
        mock_doc = {
            "url": "file:///documents/test.md",
            "title": "test.md",
            "content": "# Test Document\n\nThis is test content.",
            "html": None,
            "timestamp": "Wed Apr 19 12:34:56 2023",
            "metadata": {"size_bytes": 100}
        }
        self.executor._get_document_as_webpage = MagicMock(return_value=mock_doc)
        
        # Execute the step
        result = self.executor._execute_step(step)
        
        # Verify the correct methods were called
        self.executor._is_local_file_reference.assert_called_once_with("documents/test.md")
        self.executor._extract_file_path.assert_called_once_with("documents/test.md")
        self.executor._get_document_as_webpage.assert_called_once_with("documents/test.md")
        
        # Check that the result contains structured data
        self.assertTrue(result["success"])
        self.assertEqual(result["url"], "file:///documents/test.md")
        self.assertEqual(result["title"], "test.md")
        self.assertEqual(result["main_content"], "# Test Document\n\nThis is test content.")
        self.assertIn("structure", result)
        self.assertIn("headings", result["structure"])
        
        # Check that heading extraction worked
        self.assertEqual(len(result["structure"]["headings"]), 1)
        self.assertEqual(result["structure"]["headings"][0]["level"], 1)
        self.assertEqual(result["structure"]["headings"][0]["text"], "Test Document")
    
    def test_execute_plan(self):
        # Create a simple plan
        plan = Plan(
            query="What is the latest news about AI?",
            steps=[
                ActionStep(
                    action="search_web",
                    parameters={"query": "latest AI news"},
                    reasoning="Find recent AI news"
                ),
                ActionStep(
                    action="analyze_webpage",
                    parameters={"url": "https://example.com/ai-news"},
                    reasoning="Extract key information from the news article"
                )
            ]
        )
        
        # Mock _execute_step method to return test results
        search_result = [{"title": "AI News", "url": "https://example.com/ai-news"}]
        analyze_result = {
            "url": "https://example.com/ai-news",
            "title": "Latest AI Developments",
            "success": True,
            "main_content": "New breakthrough in AI research",
            "structure": {"headings": [{"level": 1, "text": "AI News"}]}
        }
        
        # Set up the mock to return different values for different calls
        self.executor._execute_step = MagicMock()
        self.executor._execute_step.side_effect = [search_result, analyze_result]
        
        # Mock _generate_summary
        summary = "AI has seen significant breakthroughs recently."
        self.executor._generate_summary = MagicMock(return_value=summary)
        
        # Execute the plan
        result_summary, context = self.executor.execute_plan(plan)
        
        # Verify the methods were called correctly
        self.assertEqual(self.executor._execute_step.call_count, 2)
        self.executor._generate_summary.assert_called_once()
        
        # Check the results
        self.assertEqual(result_summary, summary)
        self.assertEqual(context["original_query"], "What is the latest news about AI?")
        self.assertEqual(context["result_search_web_0"], search_result)
        self.assertEqual(context["result_analyze_webpage_1"], analyze_result)

if __name__ == '__main__':
    unittest.main() 