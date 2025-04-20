import unittest
from unittest.mock import patch, MagicMock
import json
import os
from pathlib import Path
from bs4 import BeautifulSoup

from agent.tools.web import WebScrapingTool, WebPage

class TestWebScrapingTool(unittest.TestCase):
    
    def setUp(self):
        # Create a tool instance for testing
        self.web_tool = WebScrapingTool(cache_dir=None)  # Disable caching for tests
        
        # Mock _validate_url to always return True for testing
        self.web_tool._validate_url = MagicMock(return_value=True)
    
    @patch('agent.tools.web.requests.get')
    def test_fetch_page(self, mock_get):
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Test Content</h1>
                <p>This is a paragraph.</p>
            </body>
        </html>
        """
        mock_get.return_value = mock_response
        
        # Test fetch_page
        result = self.web_tool.fetch_page("https://example.com")
        
        # Verify that the request was made with the right parameters
        mock_get.assert_called_once()
        
        # Check that the result is a WebPage with expected content
        self.assertIsInstance(result, WebPage)
        self.assertEqual(result.url, "https://example.com")
        self.assertEqual(result.title, "Test Page")
        self.assertIn("Test Content", result.content)
        self.assertIn("This is a paragraph", result.content)
    
    @patch('agent.tools.web.requests.get')
    def test_analyze_webpage(self, mock_get):
        # Mock response with structured content
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <head><title>Analysis Test Page</title></head>
            <body>
                <article>
                    <h1>Main Article Title</h1>
                    <h2>First Section</h2>
                    <p>This is the first paragraph of content.</p>
                    <ul>
                        <li>List item 1</li>
                        <li>List item 2</li>
                        <li>List item 3</li>
                    </ul>
                    <h2>Second Section</h2>
                    <p>This paragraph mentions a date: January 15, 2024</p>
                    <table>
                        <thead>
                            <tr>
                                <th>Header 1</th>
                                <th>Header 2</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>Data 1</td>
                                <td>Data 2</td>
                            </tr>
                        </tbody>
                    </table>
                </article>
            </body>
        </html>
        """
        mock_get.return_value = mock_response
        
        # Test analyze_webpage
        result = self.web_tool.analyze_webpage("https://example.com/article")
        
        # Basic validation
        self.assertTrue(result["success"])
        self.assertEqual(result["url"], "https://example.com/article")
        self.assertEqual(result["title"], "Analysis Test Page")
        
        # Check structure extraction
        self.assertEqual(len(result["structure"]["headings"]), 3)  # H1, H2, H2
        self.assertEqual(result["structure"]["headings"][0]["level"], 1)
        self.assertEqual(result["structure"]["headings"][0]["text"], "Main Article Title")
        
        # Check list extraction
        self.assertEqual(len(result["structure"]["lists"]), 1)
        self.assertEqual(len(result["structure"]["lists"][0]["items"]), 3)
        self.assertEqual(result["structure"]["lists"][0]["items"][0], "List item 1")
        
        # Check table extraction
        self.assertEqual(len(result["structure"]["tables"]), 1)
        self.assertIn("Header 1", result["structure"]["tables"][0]["headers"])
        
        # Check date extraction
        self.assertIn("January 15, 2024", result["extracted_dates"])
        
        # Verify main content was extracted
        self.assertIn("Main Article Title", result["main_content"])
    
    @patch('agent.tools.web.requests.get')
    def test_analyze_webpage_error_handling(self, mock_get):
        # Test case where fetch fails
        mock_get.side_effect = Exception("Connection error")
        
        result = self.web_tool.analyze_webpage("https://example.com/not-found")
        
        # Check error handling
        self.assertFalse(result["success"])
        self.assertIn("error", result)
        self.assertEqual(result["url"], "https://example.com/not-found")

if __name__ == '__main__':
    unittest.main() 