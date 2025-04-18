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
        Generate a summary of the research results.
        
        Args:
            query: The original query
            execution_context: The context with results from all steps
            
        Returns:
            A summary of findings
        """
        # Prepare a prompt that includes the query and results
        system_prompt = (
            f"You are {config.AGENT_NAME}, a research assistant AI. "
            f"Your task is to generate a comprehensive summary based on the "
            f"research results provided. Focus on answering the original question "
            f"and presenting the information clearly and concisely. "
            f"Cite sources where appropriate."
            f"\n\nIMPORTANT: Today's date is {time.strftime('%B %d, %Y')}. "
            f"Ensure ALL dates in your summary are accurate and not in the future. "
            f"Use the current year ({time.strftime('%Y')}) for recent events. "
            f"If a source URL returns a 404 error or was inaccessible, note this fact "
            f"and do not treat it as a reliable source of information."
        )
        
        # Build the user prompt with all the results
        user_prompt = f"Please provide a comprehensive answer to the following query:\n\n{query}\n\n"
        user_prompt += "Research results:\n\n"
        
        # Add web search results
        web_results = []
        for key, value in execution_context.items():
            if key.startswith("result_search_web_") and value:
                user_prompt += "Web Search Results:\n"
                if isinstance(value, list):
                    for item in value[:5]:  # Limit to first 5 results
                        if isinstance(item, dict):
                            title = item.get("title", "No title")
                            snippet = item.get("snippet", "No snippet")
                            url = item.get("url", "")
                            user_prompt += f"- {title}: {snippet} (Source: {url})\n\n"
                web_results.extend(value if isinstance(value, list) else [])
                
        # Add webpage contents
        for key, value in execution_context.items():
            if key.startswith("result_fetch_webpage_") and value:
                if isinstance(value, dict):
                    title = value.get("title", "Untitled")
                    content = value.get("content", "")
                    url = value.get("url", "")
                    
                    # Truncate content if too long
                    if len(content) > 1500:
                        content = content[:1500] + "..."
                        
                    user_prompt += f"Webpage: {title} (Source: {url})\n"
                    user_prompt += f"Content: {content}\n\n"
        
        # Add document search results
        for key, value in execution_context.items():
            if key.startswith("result_search_documents_") and value:
                user_prompt += "Document Search Results:\n"
                if isinstance(value, list):
                    for item in value[:5]:  # Limit to first 5 results
                        if isinstance(item, dict):
                            text = item.get("text", "")
                            metadata = item.get("metadata", {})
                            source = metadata.get("source", "Unknown")
                            
                            user_prompt += f"- {text} (Source: {source})\n\n"
        
        # Generate summary
        logger.info("Generating research summary")
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