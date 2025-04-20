"""
Planning module for the AI Research Agent.
"""
import json
from typing import Dict, List, Any, Optional, Union, Tuple
from pydantic import BaseModel, Field

from agent import config
from agent.model import ModelAPIWrapper
from agent.logger import AgentLogger

logger = AgentLogger(__name__)

class ActionStep(BaseModel):
    """Model for a single action step in a plan."""
    action: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    reasoning: str

class Plan(BaseModel):
    """Model for an execution plan."""
    query: str
    steps: List[ActionStep]
    context: Dict[str, Any] = Field(default_factory=dict)

class Planner:
    """
    A planner component that generates action plans using LLM-based reasoning.
    """
    
    def __init__(self):
        """Initialize the planner with a model API wrapper."""
        self.model = ModelAPIWrapper()
        logger.info("Initialized Planner")
    
    def _validate_step(self, step: ActionStep) -> bool:
        """
        Validate a single step in the plan to ensure it has proper structure.
        
        Args:
            step: The step to validate
            
        Returns:
            True if the step is valid, False otherwise
        """
        # Check that action is non-empty
        if not step.action:
            logger.warning("Invalid step: empty action")
            return False
        
        # Check if action is one of the allowed actions
        allowed_actions = [
            "search_web",
            "fetch_webpage",
            "extract_links",
            "extract_text",
            "search_documents",
            "analyze_webpage",  # New action to analyze webpage content
            "get_document_summary",
            "generate_summary",
            "ask_user"
        ]
        
        if step.action not in allowed_actions:
            logger.warning(f"Invalid step: unknown action '{step.action}'")
            return False
        
        # Check for required parameters
        if step.action == "search_web" and "query" not in step.parameters:
            logger.warning("Invalid step: search_web requires 'query' parameter")
            return False
            
        if step.action == "fetch_webpage" and "url" not in step.parameters:
            logger.warning("Invalid step: fetch_webpage requires 'url' parameter")
            return False
            
        if step.action == "extract_links" and "url" not in step.parameters:
            logger.warning("Invalid step: extract_links requires 'url' parameter")
            return False
            
        if step.action == "extract_text" and ("url" not in step.parameters or 
                                             "selector" not in step.parameters):
            logger.warning("Invalid step: extract_text requires 'url' and 'selector' parameters")
            return False
        
        if step.action == "analyze_webpage" and "url" not in step.parameters:
            logger.warning("Invalid step: analyze_webpage requires 'url' parameter")
            return False
            
        if step.action == "search_documents" and "query" not in step.parameters:
            logger.warning("Invalid step: search_documents requires 'query' parameter")
            return False
            
        if step.action == "get_document_summary" and "file_path" not in step.parameters:
            logger.warning("Invalid step: get_document_summary requires 'file_path' parameter")
            # Prevent incorrect usage with URLs
            if "file_path" in step.parameters and step.parameters["file_path"].startswith("http"):
                logger.warning("Invalid step: get_document_summary cannot be used with URLs")
                return False
            return False
        
        return True
    
    def _generate_plan(self, query: str) -> Optional[Plan]:
        """
        Generate a plan for the given query using the language model.
        
        Args:
            query: The user's query
            
        Returns:
            A Plan object or None if generation failed
        """
        # System prompt that guides the model to produce a well-structured plan
        system_prompt = (
            f"# Advanced Research Planning System\n\n"
            f"You are the planning component of {config.AGENT_NAME}, an advanced AI research assistant. "
            f"Your task is to generate a comprehensive, step-by-step research plan to thoroughly answer the user's query. "
            f"Think of yourself as a research strategist designing the optimal approach to collect, analyze, and synthesize information.\n\n"
            
            f"## Planning Principles\n"
            f"1. **Depth and Breadth**: Balance deep investigation with broad context gathering\n"
            f"2. **Multiple Perspectives**: Seek diverse viewpoints and sources\n"
            f"3. **Verification**: Cross-reference information across multiple reliable sources\n"
            f"4. **Structured Approach**: Break complex queries into logical components\n"
            f"5. **Adaptability**: Design plans that can evolve as new information emerges\n\n"
            
            f"## Available Research Actions\n"
            f"- search_web: Search the web for information (parameters: {{'query': 'your search query'}})\n"
            f"- fetch_webpage: Fetch and read a webpage (parameters: {{'url': 'https://example.com'}})\n"
            f"- extract_links: Extract links from a webpage (parameters: {{'url': 'https://example.com'}})\n"
            f"- extract_text: Extract specific text using a CSS selector (parameters: {{'url': 'https://example.com', 'selector': '.main-content'}})\n"
            f"- analyze_webpage: Analyze the content of a webpage to extract key information (parameters: {{'url': 'https://example.com'}})\n"
            f"- search_documents: Search local knowledge base documents (parameters: {{'query': 'your document search query'}})\n"
            f"- get_document_summary: Get a summary of a specific LOCAL document (parameters: {{'file_path': 'path/to/document'}})\n"
            f"- generate_summary: Generate a final comprehensive summary of collected information (parameters: {{}})\n"
            f"- ask_user: Ask for user clarification when needed (parameters: {{'question': 'What specific aspect are you interested in?'}})\n\n"
            
            f"## Planning Guide\n"
            f"1. **Analyze the Query**: Begin by understanding what information is needed\n"
            f"2. **Gather General Context**: Start with broad sources to establish foundational knowledge\n"
            f"3. **Explore Specific Details**: Use analyze_webpage to extract information from important articles\n"
            f"4. **Verify Information**: Cross-check important facts across multiple sources\n"
            f"5. **Synthesize**: Plan for a comprehensive summary that addresses all aspects\n\n"
            
            f"## IMPORTANT NOTES\n"
            f"- After fetching webpages or extracting links, ALWAYS follow up with analyze_webpage to extract the content\n"
            f"- The get_document_summary action is ONLY for local documents, NOT for web URLs\n"
            f"- Your plan should always analyze articles to extract information, not just fetch them\n\n"
            
            f"## Plan Structure Requirements\n"
            f"For each step in your plan provide:\n"
            f"1. The specific action to take (from the available actions list)\n"
            f"2. All necessary parameters for that action (as a valid JSON object, use an empty object {{}} if no parameters are needed)\n"
            f"3. Detailed reasoning explaining your strategic thinking for this step\n\n"
            
            f"Return the plan as a valid JSON object with the following structure:\n"
            f"```json\n"
            f"{{\n"
            f"  \"steps\": [\n"
            f"    {{\n"
            f"      \"action\": \"search_web\",\n"
            f"      \"parameters\": {{ \"query\": \"example search\" }},\n"
            f"      \"reasoning\": \"This search will provide initial information...\"\n"
            f"    }},\n"
            f"    {{\n"
            f"      \"action\": \"generate_summary\",\n"
            f"      \"parameters\": {{}},\n"
            f"      \"reasoning\": \"Final step to synthesize findings.\"\n"
            f"    }}\n"
            f"  ]\n"
            f"}}\n"
            f"```\n\n"
            f"WARNING: Ensure each step has all three fields properly formatted. Do not include any additional fields or trailing commas. The entire response must be a single valid JSON object."
        )
        
        # User prompt
        user_prompt = (
            f"Create a comprehensive research plan to thoroughly answer this query: '{query}'\n\n"
            f"Carefully analyze what information is needed and design the most effective approach to gather and synthesize it. "
            f"Consider what sources would be most authoritative for this topic and how to cross-verify information. "
            f"Break complex aspects into multiple research steps. "
            f"IMPORTANT: After fetching web content, always include an 'analyze_webpage' step to extract key information.\n\n"
            f"Your response MUST be a single valid JSON object with a 'steps' array. Each step MUST have exactly three fields: 'action', 'parameters', and 'reasoning'."
            f"Ensure parameters are always JSON objects, using {{}} for empty parameters. Do not include trailing commas."
        )
        
        try:
            # Generate the plan as JSON
            plan_json = self.model.generate_json(
                prompt=user_prompt,
                system_message=system_prompt,
                temperature=0.7
            )
            
            if not plan_json or "steps" not in plan_json:
                logger.error("Failed to generate a valid plan from LLM response")
                return None
            
            # Create the Plan object with validation and type correction
            steps = []
            for step_data in plan_json.get("steps", []):
                try:
                    # Basic validation of step_data structure
                    if not isinstance(step_data, dict) or "action" not in step_data:
                        logger.warning(f"Skipping invalid step data (not a dict or missing action): {step_data}")
                        continue
                    
                    action = step_data.get("action", "")
                    parameters = step_data.get("parameters", {})
                    reasoning = step_data.get("reasoning", "")

                    # Attempt to fix common parameter type errors (e.g., string instead of dict)
                    if action == "search_web" and isinstance(parameters, str):
                        logger.warning(f"Correcting parameters for search_web: converting string '{parameters}' to dict")
                        parameters = {"query": parameters}
                    elif not isinstance(parameters, dict):
                        logger.warning(f"Invalid parameter type for action '{action}': expected dict, got {type(parameters)}. Defaulting to empty dict.")
                        parameters = {}

                    # Create ActionStep with validated/corrected data
                    step = ActionStep(
                        action=action,
                        parameters=parameters,
                        reasoning=reasoning
                    )
                    steps.append(step)
                except Exception as validation_error:
                    logger.error(f"Error validating step data {step_data}: {validation_error}")
                    # Optionally skip this step or handle error differently
                    continue
            
            if not steps:
                logger.error("No valid steps could be parsed from the generated plan.")
                return None

            plan = Plan(
                query=query,
                steps=steps,
                context={"original_query": query}
            )
            
            logger.info(f"Generated plan with {len(steps)} steps")
            return plan
            
        except Exception as e:
            logger.error(f"Error generating plan: {str(e)}")
            return None
    
    def _refine_plan(self, plan: Plan) -> Plan:
        """
        Refine a plan by filtering out invalid steps.
        
        Args:
            plan: The original plan
            
        Returns:
            A refined plan with only valid steps
        """
        refined_steps = []
        
        for step in plan.steps:
            if self._validate_step(step):
                refined_steps.append(step)
            else:
                logger.warning(f"Removed invalid step: {step.action}")
        
        # If no valid steps remain, add a fallback step
        if not refined_steps:
            logger.warning("No valid steps in plan, adding fallback step")
            fallback_step = ActionStep(
                action="generate_summary",
                parameters={},
                reasoning="No valid research steps could be executed. Providing a direct response based on available knowledge."
            )
            refined_steps.append(fallback_step)
        
        # Update the plan with refined steps
        refined_plan = Plan(
            query=plan.query,
            steps=refined_steps,
            context=plan.context
        )
        
        logger.info(f"Refined plan now has {len(refined_steps)} steps")
        return refined_plan
    
    def create_plan(self, query: str) -> Optional[Plan]:
        """
        Create an execution plan for the given query.
        
        Args:
            query: The user's query
            
        Returns:
            A Plan object or None if planning failed
        """
        # Check if query exceeds maximum length
        if len(query) > config.MAX_QUERY_LENGTH:
            logger.warning(f"Query exceeds maximum length ({len(query)} > {config.MAX_QUERY_LENGTH})")
            query = query[:config.MAX_QUERY_LENGTH]
        
        # Generate the initial plan
        plan = self._generate_plan(query)
        
        if not plan:
            return None
        
        # Refine the plan
        refined_plan = self._refine_plan(plan)
        
        return refined_plan
    
    def update_plan_with_results(
        self, 
        plan: Plan, 
        step_index: int, 
        result: Any
    ) -> Plan:
        """
        Update a plan with the results of a completed step.
        
        Args:
            plan: The current plan
            step_index: The index of the completed step
            result: The result data from executing the step
            
        Returns:
            The updated plan
        """
        # Make a copy of the plan
        updated_plan = Plan(
            query=plan.query,
            steps=plan.steps.copy(),
            context=plan.context.copy()
        )
        
        # Add the result to the context
        step = updated_plan.steps[step_index]
        result_key = f"result_{step.action}_{step_index}"
        updated_plan.context[result_key] = result
        
        # If we're at the last step, we're done
        if step_index >= len(updated_plan.steps) - 1:
            return updated_plan
            
        # For certain actions, we might want to dynamically update next steps
        if step.action == "search_web" and result:
            # If we found relevant URLs from a web search, add steps to fetch them
            urls = self._extract_urls_from_search_results(result)
            
            # If there are URLs and the next step isn't already to fetch one of them
            if urls and (step_index + 1 >= len(updated_plan.steps) or 
                        updated_plan.steps[step_index + 1].action != "fetch_webpage"):
                # Insert new steps to fetch the top URLs
                for i, url in enumerate(urls[:2]):  # Limit to top 2 results
                    # Add fetch step
                    fetch_step = ActionStep(
                        action="fetch_webpage",
                        parameters={"url": url},
                        reasoning=f"Fetching content from relevant search result: {url}"
                    )
                    updated_plan.steps.insert(step_index + 1 + (i*2), fetch_step)
                    
                    # Add analyze step immediately after fetch
                    analyze_step = ActionStep(
                        action="analyze_webpage",
                        parameters={"url": url},
                        reasoning=f"Analyzing content from fetched webpage to extract key information: {url}"
                    )
                    updated_plan.steps.insert(step_index + 2 + (i*2), analyze_step)
                    
                logger.info(f"Added {min(2, len(urls))*2} steps (fetch+analyze) based on search results")
        
        # If we just fetched a webpage, ensure there's an analyze step
        elif step.action == "fetch_webpage" and result:
            url = step.parameters.get("url", "")
            # Check if the next step is not already to analyze this page
            if (step_index + 1 >= len(updated_plan.steps) or 
                updated_plan.steps[step_index + 1].action != "analyze_webpage" or
                updated_plan.steps[step_index + 1].parameters.get("url") != url):
                
                # Insert new analyze step
                analyze_step = ActionStep(
                    action="analyze_webpage",
                    parameters={"url": url},
                    reasoning=f"Analyzing content from fetched webpage to extract key information: {url}"
                )
                updated_plan.steps.insert(step_index + 1, analyze_step)
                logger.info(f"Added analyze_webpage step for {url}")
        
        return updated_plan
    
    def _extract_urls_from_search_results(self, search_results: Any) -> List[str]:
        """
        Extract URLs from search results.
        
        Args:
            search_results: The search results data
            
        Returns:
            List of URLs
        """
        urls = []
        
        if isinstance(search_results, list):
            for result in search_results:
                if isinstance(result, dict) and "url" in result:
                    urls.append(result["url"])
                    
        return urls 