"""
Executor module for the AI Research Agent.
"""
from typing import Dict, List, Any, Optional, Union, Tuple
import re
from pathlib import Path
import time

from agent import config
from agent.model import ModelAPIWrapper
from agent.memory import Memory
from agent.tools.web import WebScrapingTool
from agent.tools.documents import DocumentRetrievalTool
from agent.planner import Plan, ActionStep
from agent.logger import AgentLogger

logger = AgentLogger(__name__)

class Executor:
    """
    An executor component that executes action plans by calling the appropriate tools.
    """
    
    def __init__(self):
        """Initialize the executor with required tools and components."""
        # Initialize components
        self.model = ModelAPIWrapper()
        self.memory = Memory()
        self.web_tool = WebScrapingTool()
        self.doc_tool = DocumentRetrievalTool()
        
        logger.info("Initialized Executor with all tools")
    
    def execute_plan(self, plan: Plan, dry_run: bool = False) -> Tuple[str, Dict[str, Any]]:
        """
        Execute a plan step by step.
        
        Args:
            plan: The plan to execute
            dry_run: If True, only simulate execution without calling external tools
            
        Returns:
            A tuple containing (summary, execution_context)
        """
        # Store the original query in memory
        self.memory.write_memory("conversation", {
            "session_id": "default",
            "role": "user",
            "content": plan.query
        })
        
        # Context to store results from each step
        execution_context = {"original_query": plan.query}
        
        # Skip execution if dry run
        if dry_run:
            logger.info("Executing plan in dry-run mode (no actions will be performed)")
            
            # For each step, log but don't execute
            for i, step in enumerate(plan.steps):
                logger.info(f"Step {i+1}: {step.action} - {step.reasoning}")
                
                # Add placeholder results to context
                execution_context[f"result_{step.action}_{i}"] = "[Dry run - no execution]"
            
            # Generate a preview summary
            preview = self._generate_execution_preview(plan)
            
            return preview, execution_context
        
        # Execute each step
        for i, step in enumerate(plan.steps):
            logger.info(f"Executing step {i+1}/{len(plan.steps)}: {step.action}")
            
            try:
                # Execute the step
                result = self._execute_step(step)
                
                # Store the result in the execution context
                execution_context[f"result_{step.action}_{i}"] = result
                
                # Store the result in memory if needed
                if result and step.action in ["fetch_webpage", "search_documents"]:
                    self._store_in_memory(step.action, result)
                
                # Update the plan with this result if necessary
                # (This would be used if we wanted to dynamically modify the plan)
                # plan = self.planner.update_plan_with_results(plan, i, result)
                
            except Exception as e:
                logger.error(f"Error executing step {step.action}: {str(e)}")
                execution_context[f"error_{step.action}_{i}"] = str(e)
        
        # Generate final summary using the model
        summary = self._generate_summary(plan.query, execution_context)
        
        # Store the summary in memory
        self.memory.write_memory("conversation", {
            "session_id": "default",
            "role": "assistant",
            "content": summary
        })
        
        logger.info(f"Plan execution completed with {len(plan.steps)} steps")
        return summary, execution_context
    
    def _execute_step(self, step: ActionStep) -> Any:
        """
        Execute a single step in the plan using the appropriate tool.
        
        Args:
            step: The step to execute
            
        Returns:
            The result of executing the step
        """
        action = step.action
        params = step.parameters
        
        if action == "search_web":
            query = params.get("query", "")
            logger.info(f"Searching web for: {query}")
            return self.web_tool.search_google(query)
            
        elif action == "fetch_webpage":
            url = params.get("url", "")
            # Check if this is actually a local file reference
            if self._is_local_file_reference(url):
                file_path = self._extract_file_path(url)
                logger.info(f"Treating URL as local file: {file_path}")
                return self._get_document_as_webpage(file_path)
            else:
                logger.info(f"Fetching webpage: {url}")
                page = self.web_tool.fetch_page(url)
                return page.dict() if page else None
            
        elif action == "extract_links":
            url = params.get("url", "")
            logger.info(f"Extracting links from: {url}")
            return self.web_tool.extract_links(url)
            
        elif action == "extract_text":
            url = params.get("url", "")
            selector = params.get("selector", "")
            
            # Check if this is actually a local file reference
            if self._is_local_file_reference(url):
                file_path = self._extract_file_path(url)
                logger.info(f"Extracting text from local file: {file_path}")
                doc = self.doc_tool.get_document(file_path)
                if doc:
                    return doc.content
                else:
                    # Try indexing the file first if it's not already indexed
                    logger.info(f"File not indexed, attempting to index: {file_path}")
                    doc_id = self.doc_tool.index_document(file_path)
                    if doc_id:
                        doc = self.doc_tool.get_document(doc_id)
                        return doc.content if doc else None
                    return None
            else:
                logger.info(f"Extracting text from {url} with selector '{selector}'")
                return self.web_tool.extract_text_with_selector(url, selector)
            
        elif action == "analyze_webpage":
            url = params.get("url", "")
            logger.info(f"Analyzing webpage: {url}")
            
            # Check if this is actually a local file reference
            if self._is_local_file_reference(url):
                file_path = self._extract_file_path(url)
                logger.info(f"Analyzing local file as webpage: {file_path}")
                
                # Convert document to webpage format and return it
                doc_as_webpage = self._get_document_as_webpage(file_path)
                
                # Add structured analysis similar to webpage analysis
                structured_data = {
                    "url": doc_as_webpage.get("url", ""),
                    "title": doc_as_webpage.get("title", ""),
                    "success": True,
                    "main_content": doc_as_webpage.get("content", ""),
                    "metadata": doc_as_webpage.get("metadata", {}),
                    "structure": {
                        "headings": [],
                        "lists": [],
                        "tables": []
                    }
                }
                
                # Extract simple structure from the content
                content = doc_as_webpage.get("content", "")
                if content:
                    # Extract headings using regex (basic approach)
                    heading_pattern = re.compile(r'^(#+)\s+(.+)$', re.MULTILINE)
                    for match in heading_pattern.finditer(content):
                        level = len(match.group(1))
                        text = match.group(2).strip()
                        structured_data["structure"]["headings"].append({
                            "level": level,
                            "text": text
                        })
                
                return structured_data
            else:
                # Use web tool to analyze regular webpage
                return self.web_tool.analyze_webpage(url)
            
        elif action == "search_documents":
            query = params.get("query", "")
            logger.info(f"Searching documents for: {query}")
            results = self.doc_tool.search(query)
            return [chunk.dict() for chunk in results]
            
        elif action == "get_document_summary":
            file_path = params.get("file_path", "")
            logger.info(f"Getting summary of document: {file_path}")
            return self.doc_tool.get_document(file_path)
            
        elif action == "generate_summary":
            # This is handled separately at the end of plan execution
            logger.info("Generate summary action is a placeholder")
            return None
            
        elif action == "ask_user":
            # In a real implementation, this would wait for user input
            # For now, we'll just log it
            question = params.get("question", "")
            logger.info(f"Ask user: {question}")
            return f"[User would be asked: {question}]"
            
        else:
            logger.warning(f"Unknown action: {action}")
            return None
    
    def _is_local_file_reference(self, url: str) -> bool:
        """
        Check if a URL is likely a reference to a local file.
        
        Args:
            url: The URL to check
            
        Returns:
            True if URL appears to reference a local file
        """
        # Check for URL schemes that definitely indicate web resources
        if url.startswith(('http://', 'https://', 'ftp://')):
            # Check if the URL contains common file patterns despite having a web scheme
            file_patterns = [
                r'/([^/]+\.txt)$',
                r'/([^/]+\.pdf)$',
                r'/([^/]+\.md)$',
                r'/([^/]+\.json)$',
                r'/([^/]+\.csv)$',
                r'/([^/]+\.docx?)$'
            ]
            
            for pattern in file_patterns:
                match = re.search(pattern, url)
                if match:
                    filename = match.group(1)
                    # Check if this file exists locally in common directories
                    search_dirs = ['documents', 'data', 'test_data', '.']
                    for directory in search_dirs:
                        if Path(directory) / filename.lower() in list(Path(directory).glob('*')) or \
                           Path(directory) / filename in list(Path(directory).glob('*')):
                            return True
            
            # If no local file found, it's a web URL
            return False
        
        # If it's a local file path, treat it as a file
        return True
    
    def _extract_file_path(self, url: str) -> str:
        """
        Extract the file path from a URL or path string.
        
        Args:
            url: The URL or path to extract from
            
        Returns:
            The extracted file path
        """
        # If it's already a file path without URL scheme, return it
        if not url.startswith(('http://', 'https://', 'ftp://', 'file://')):
            # Check if it exists as is
            if Path(url).exists():
                return url
                
            # Check in known directories
            search_dirs = ['documents', 'data', 'test_data', '.']
            for directory in search_dirs:
                potential_path = Path(directory) / Path(url).name
                if potential_path.exists():
                    logger.info(f"Found file at: {potential_path}")
                    return str(potential_path)
            
            return url
            
        # Handle file:// URLs
        if url.startswith('file://'):
            # Remove the file:// prefix
            file_path = url[7:]
            
            # Check if it exists as is
            if Path(file_path).exists():
                return file_path
                
            # Extract filename
            filename = Path(file_path).name
            
            # Search in known directories
            search_dirs = ['documents', 'data', 'test_data', '.']
            for directory in search_dirs:
                for file_path in Path(directory).glob('*'):
                    if file_path.name.lower() == filename.lower() or file_path.name == filename:
                        logger.info(f"Found file at: {file_path}")
                        return str(file_path)
        
        # Handle web URLs that might reference local files
        file_match = re.search(r'/([^/]+\.\w+)$', url)
        if file_match:
            filename = file_match.group(1)
            # Search in common directories
            search_dirs = ['documents', 'data', 'test_data', '.', 'app']
            for directory in search_dirs:
                try:
                    # Try exact match
                    if Path(directory).exists():
                        for file_path in Path(directory).glob('*'):
                            if file_path.name.lower() == filename.lower() or file_path.name == filename:
                                logger.info(f"Found file at: {file_path}")
                                return str(file_path)
                        
                        # Try subdirectories
                        for subdirectory in Path(directory).glob('**'):
                            if subdirectory.is_dir():
                                for file_path in subdirectory.glob('*'):
                                    if file_path.name.lower() == filename.lower() or file_path.name == filename:
                                        logger.info(f"Found file at: {file_path}")
                                        return str(file_path)
                except Exception as e:
                    logger.error(f"Error searching directory {directory}: {str(e)}")
            
            # If we still haven't found it, try indexed documents
            for doc_id, doc_entry in self.doc_tool.document_index.items():
                if doc_entry.filename.lower() == filename.lower() or doc_entry.filename == filename:
                    logger.info(f"Found indexed file: {doc_entry.path}")
                    return doc_entry.path
            
            # If not found, return the filename as-is in case it's in the current directory
            return filename
        
        return url
        
    def _get_document_as_webpage(self, file_path: str) -> Dict[str, Any]:
        """
        Format a document as if it were a webpage for consistency.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Dictionary with document content formatted like a webpage
        """
        try:
            # Attempt to read the file directly
            path = Path(file_path)
            if path.exists():
                content = path.read_text(errors='replace')
                return {
                    "url": f"file://{path.absolute()}",
                    "title": path.name,
                    "content": content,
                    "html": None,
                    "timestamp": time.ctime(path.stat().st_mtime),
                    "metadata": {
                        "size_bytes": path.stat().st_size,
                        "last_modified": time.ctime(path.stat().st_mtime)
                    }
                }
            
            # If direct read fails, check if it's indexed and use that
            logger.info(f"File not found directly, checking indexed documents: {file_path}")
            doc = self.doc_tool.get_document(file_path)
            if doc:
                return {
                    "url": f"file://{doc.filename}",
                    "title": doc.filename,
                    "content": doc.content,
                    "html": None,
                    "timestamp": time.ctime(),
                    "metadata": doc.metadata
                }
            
            # If not indexed either, return empty result
            logger.warning(f"Document not found: {file_path}")
            return {
                "url": f"file://{file_path}",
                "title": Path(file_path).name,
                "content": f"[Document not found: {file_path}]",
                "html": None,
                "timestamp": time.ctime(),
                "metadata": {}
            }
        except Exception as e:
            logger.error(f"Error reading document {file_path}: {str(e)}")
            return {
                "url": f"file://{file_path}",
                "title": Path(file_path).name,
                "content": f"[Error reading document: {str(e)}]",
                "html": None,
                "timestamp": time.ctime(),
                "metadata": {}
            }
    
    def _store_in_memory(self, action: str, result: Any) -> None:
        """
        Store relevant results in memory.
        
        Args:
            action: The action that produced the result
            result: The result data
        """
        if action == "fetch_webpage" and result:
            # Store webpage content as a document
            self.memory.write_memory("document", {
                "title": result.get("title", "Untitled"),
                "content": result.get("content", ""),
                "url": result.get("url", ""),
                "timestamp": result.get("timestamp", "")
            })
            
        elif action == "search_documents" and result:
            # Extract facts from document search results
            for item in result:
                if isinstance(item, dict) and "text" in item:
                    # Store as a fact with source
                    metadata = item.get("metadata", {})
                    source = metadata.get("source", "")
                    
                    self.memory.write_memory("fact", {
                        "fact": item["text"],
                        "source": source,
                        "confidence": metadata.get("similarity", 0.5)
                    })
    
    def _generate_summary(self, query: str, execution_context: Dict[str, Any]) -> str:
        """
        Generate a research summary based on the execution context.
        
        Args:
            query: The original research query
            execution_context: Context containing results from all steps
            
        Returns:
            A formatted summary
        """
        # Extract relevant information from the execution context
        web_results = []
        document_results = []
        error_count = 0
        
        for key, value in execution_context.items():
            if key.startswith("result_search_web") and value:
                web_results.append(value)
            if key.startswith("result_fetch_webpage") and value:
                # Count failed fetches
                fetch_success = value.get("metadata", {}).get("fetch_success", True)
                fetch_failed = value.get("fetch_failed", False)
                if not fetch_success or fetch_failed:
                    error_count += 1
                web_results.append(value)
            if key.startswith("result_search_documents") and value:
                document_results.append(value)
            if key.startswith("result_analyze_webpage") and value:
                # Count failed analysis
                if value.get("success", True) == False:
                    error_count += 1
        
        # Format results for model consumption
        formatted_web_results = self._format_web_results(web_results)
        formatted_doc_results = self._format_doc_results(document_results)
        
        # Generate the summary using the model
        from datetime import datetime, timedelta
        
        # Apply date offset if available to get corrected current date
        current_date = datetime.now()
        if hasattr(AgentLogger, '_date_offset'):
            current_date = current_date - AgentLogger._date_offset
            
        current_date_str = current_date.strftime("%Y-%m-%d")
        
        # Build the prompt
        system_prompt = (
            f"You are {config.AGENT_NAME}, a research assistant AI. "
            f"Your task is to generate a comprehensive summary based on the "
            f"research results provided. Focus on answering the original question "
            f"and presenting the information clearly and concisely. "
            f"Cite sources where appropriate."
            f"\n\nIMPORTANT: Today's date is {current_date_str}. "
            f"Ensure ALL dates in your summary are accurate and not in the future. "
            f"If a source URL returns a 404 error or was inaccessible, note this fact "
            f"and do not treat it as a reliable source of information."
            f"\n\nCRITICAL: There were {error_count} failed source fetches or analyses. "
            f"DO NOT make up information for sources you couldn't access. "
            f"If you don't have sufficient reliable information to answer the query, "
            f"explicitly state this limitation. NEVER invent citations or facts."
        )
        
        user_prompt = f"""
        Based on the following information, create a comprehensive research summary for the query: "{query}".
        
        Web search results:
        {formatted_web_results}
        
        Document search results:
        {formatted_doc_results}
        
        Your task is to:
        1. Synthesize all the information into a coherent, well-structured summary
        2. Organize information by topics or themes
        3. Highlight key findings and insights
        4. Note any areas where information is limited or contradictory
        5. Include all relevant facts and perspectives
        6. Format the summary in a clean, readable way with headings and bullet points
        7. At the end, suggest follow-up questions or areas for further research
        8. Make sure all information is factual and derived from the sources provided
        
        IMPORTANT INSTRUCTIONS:
        - If sources failed to load or returned errors, acknowledge this limitation
        - DO NOT make up information for sources that couldn't be accessed
        - Only include facts that are verifiable from the successfully retrieved sources
        - If you don't have enough reliable information, clearly state this limitation
        - NEVER cite failed sources as if they contained information
        
        Please provide a detailed yet concise summary between 1500-3000 characters.
        """
        
        # Get summary from model
        summary = self.model.generate_text(
            prompt=user_prompt,
            system_message=system_prompt,
            temperature=0.5
        )
        
        logger.info(f"Generated summary: {len(summary)} chars")
        
        return summary
    
    def _generate_execution_preview(self, plan: Plan) -> str:
        """
        Generate a preview of what will happen when the plan is executed.
        
        Args:
            plan: The plan to preview
            
        Returns:
            A string preview of the execution
        """
        system_prompt = (
            f"You are {config.AGENT_NAME}, a research assistant AI. "
            f"Given a research plan, provide a preview of how the plan will be executed "
            f"and what kind of information will likely be gathered."
        )
        
        # Format the plan as a string
        plan_str = f"Query: {plan.query}\n\nExecution Plan:\n"
        for i, step in enumerate(plan.steps):
            plan_str += f"Step {i+1}: {step.action}\n"
            plan_str += f"Parameters: {step.parameters}\n"
            plan_str += f"Reasoning: {step.reasoning}\n\n"
            
        user_prompt = (
            f"Please preview the execution of the following research plan. "
            f"Explain what information will be gathered from each step and how "
            f"it will contribute to answering the original query.\n\n{plan_str}"
        )
        
        logger.info("Generating execution preview")
        preview = self.model.generate_text(
            prompt=user_prompt,
            system_message=system_prompt,
            temperature=0.7
        )
        
        logger.info(f"Generated execution preview: {len(preview)} chars")
        return preview

    def _format_web_results(self, results: List[Any]) -> str:
        """
        Format web search results for inclusion in the summary prompt.
        
        Args:
            results: List of web search results
            
        Returns:
            Formatted string representation of results
        """
        formatted = ""
        
        for result in results:
            if isinstance(result, list):
                # Handle search results list
                for item in result[:5]:  # Limit to first 5 results
                    if isinstance(item, dict):
                        title = item.get("title", "No title")
                        snippet = item.get("snippet", "No snippet")
                        url = item.get("url", "")
                        formatted += f"- {title}: {snippet} (Source: {url})\n\n"
            elif isinstance(result, dict):
                # Check if this was a failed fetch
                fetch_success = result.get("metadata", {}).get("fetch_success", True)
                fetch_failed = result.get("fetch_failed", False)
                
                if not fetch_success or fetch_failed:
                    # This was a failed fetch - mark it clearly
                    title = result.get("title", "Error")
                    url = result.get("url", "")
                    error = result.get("metadata", {}).get("error", "Unknown error")
                    if not error and "error" in result:
                        error = result["error"]
                        
                    formatted += f"[FAILED SOURCE] {title} (URL: {url})\n"
                    formatted += f"Error: {error}\n"
                    formatted += "WARNING: This source could not be accessed and should not be cited or used as a reference.\n\n"
                else:
                    # Handle webpage content
                    title = result.get("title", "Untitled")
                    content = result.get("content", "")
                    url = result.get("url", "")
                    
                    # Truncate content if too long
                    if len(content) > 1500:
                        content = content[:1500] + "..."
                        
                    formatted += f"Webpage: {title} (Source: {url})\n"
                    formatted += f"Content: {content}\n\n"
        
        return formatted or "No web results available."
        
    def _format_doc_results(self, results: List[Any]) -> str:
        """
        Format document search results for inclusion in the summary prompt.
        
        Args:
            results: List of document search results
            
        Returns:
            Formatted string representation of results
        """
        formatted = ""
        
        for result in results:
            if isinstance(result, list):
                for item in result[:5]:  # Limit to first 5 results
                    if isinstance(item, dict):
                        text = item.get("text", "")
                        metadata = item.get("metadata", {})
                        source = metadata.get("source", "Unknown")
                        
                        formatted += f"- {text} (Source: {source})\n\n"
        
        return formatted or "No document results available." 