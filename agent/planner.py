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
            
        if step.action == "search_documents" and "query" not in step.parameters:
            logger.warning("Invalid step: search_documents requires 'query' parameter")
            return False
            
        if step.action == "get_document_summary" and "file_path" not in step.parameters:
            logger.warning("Invalid step: get_document_summary requires 'file_path' parameter")
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
            f"You are {config.AGENT_NAME}, a research assistant AI. "
            f"Your task is to generate a step-by-step plan to answer the user's query. "
            f"The plan should include research actions like searching the web, fetching relevant "
            f"pages, extracting information, and searching documents.\n\n"
            f"Available actions:\n"
            f"- search_web: Search the web for information (parameters: query)\n"
            f"- fetch_webpage: Fetch and read a webpage (parameters: url)\n"
            f"- extract_links: Extract links from a webpage (parameters: url)\n"
            f"- extract_text: Extract text using a CSS selector (parameters: url, selector)\n"
            f"- search_documents: Search local documents (parameters: query)\n"
            f"- get_document_summary: Get a summary of a document (parameters: file_path)\n"
            f"- generate_summary: Generate a summary of collected information (parameters: none)\n"
            f"- ask_user: Ask the user for clarification (parameters: question)\n\n"
            f"For each step, provide:\n"
            f"1. The action to take\n"
            f"2. Necessary parameters for the action\n"
            f"3. Your reasoning for this step\n\n"
            f"Return the plan as a JSON object with a 'steps' array where each step has "
            f"'action', 'parameters', and 'reasoning' fields."
        )
        
        # User prompt
        user_prompt = (
            f"Generate a step-by-step research plan to answer this query: '{query}'\n\n"
            f"Think carefully about what information is needed and the most efficient "
            f"way to collect it. Provide your response as a valid JSON object with a 'steps' array."
        )
        
        try:
            # Generate the plan as JSON
            plan_json = self.model.generate_json(
                prompt=user_prompt,
                system_message=system_prompt,
                temperature=0.7
            )
            
            if not plan_json or "steps" not in plan_json:
                logger.error("Failed to generate a valid plan")
                return None
            
            # Create the Plan object
            steps = []
            for step_data in plan_json["steps"]:
                step = ActionStep(
                    action=step_data.get("action", ""),
                    parameters=step_data.get("parameters", {}),
                    reasoning=step_data.get("reasoning", "")
                )
                steps.append(step)
            
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
                    new_step = ActionStep(
                        action="fetch_webpage",
                        parameters={"url": url},
                        reasoning=f"Fetching content from relevant search result: {url}"
                    )
                    updated_plan.steps.insert(step_index + 1 + i, new_step)
                    
                logger.info(f"Added {min(2, len(urls))} fetch_webpage steps based on search results")
        
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