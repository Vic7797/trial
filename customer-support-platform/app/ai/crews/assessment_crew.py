"""Assessment Crew for categorizing and prioritizing support tickets."""
import litellm
from crewai import Agent, Task, Crew, Process

from app.ai.prompts.assessment import (
    ASSESSMENT_CATEGORY_AGENT_PROMPT,
    ASSESSMENT_CRITICALITY_AGENT_PROMPT,
    CATEGORY_TASK_PROMPT,
    CRITICALITY_TASK_PROMPT,
)
from app.config import settings
from app.crud.categories import category as category_crud
from app.db.session import SessionLocal
from app.core.logging import get_logger

logger = get_logger(__name__)

# Configure LiteLLM
litellm.api_key = settings.OPENAI_API_KEY


class AssessmentCrew:
    """Crew for assessing ticket category and criticality."""

    def __init__(self):
        # LiteLLM configuration
        llm_config = {
            "model": f"{settings.LLM_PROVIDER}/{settings.LLM_MODEL}",
            "temperature": settings.DEFAULT_TEMPERATURE,
            "api_key": settings.OPENAI_API_KEY,
            "max_tokens": 1000,
        }

        self.category_agent = Agent(
            role="Category Specialist",
            goal="Accurately categorize support tickets",
            backstory=ASSESSMENT_CATEGORY_AGENT_PROMPT,
            verbose=settings.VERBOSE,
            llm=llm_config,
            allow_delegation=False,
        )

        self.criticality_agent = Agent(
            role="Criticality Analyst",
            goal=(
                "Determine the urgency and impact "
                "of support tickets"
            ),
            backstory=ASSESSMENT_CRITICALITY_AGENT_PROMPT,
            verbose=settings.VERBOSE,
            llm=llm_config,
            allow_delegation=False,
        )

    def assess_ticket(self, ticket_title: str, ticket_description: str, organization_id: str):
        """Assess a ticket and return category and criticality.

        Args:
            ticket_title: Title of the ticket
            ticket_description: Description of the ticket
            organization_id: ID of the organization

        Returns:
            Dict containing category and criticality
        """
        # Get available categories from the database
        db = SessionLocal()
        try:
            categories = category_crud.get_by_organization(
                db, organization_id=organization_id
            )
            category_names = [cat.name for cat in categories]
        finally:
            db.close()

        if not category_names:
            logger.warning(
                "No categories found for organization %s", organization_id
            )
            return {
                "category": None,
                "criticality": "medium",  # Default to medium if unsure
                "estimated_time": 24  # Default 24 hours
            }
        
        # Create tasks for category and criticality assessment
        category_task = Task(
            description=CATEGORY_TASK_PROMPT.format(
                ticket_title=ticket_title,
                ticket_description=ticket_description,
                available_categories=", ".join(category_names)
            ),
            agent=self.category_agent,
            expected_output="Most appropriate category for the ticket"
        )

        criticality_task = Task(
            description=CRITICALITY_TASK_PROMPT.format(
                ticket_title=ticket_title,
                ticket_description=ticket_description,
                # Category will be filled from category task output
                category="{category_output}"
            ),
            agent=self.criticality_agent,
            context=[category_task],
            expected_output="Ticket criticality assessment"
        )

        # Create and run crew
        crew = Crew(
            agents=[self.category_agent, self.criticality_agent],
            tasks=[category_task, criticality_task],
            verbose=settings.VERBOSE,
            process=Process.sequential
        )

        result = crew.kickoff()

        # Parse results
        try:
            category = next(
                cat for cat in categories
                if cat.name.lower() == result["category"].lower()
            )
            
            return {
                "category_id": category.id,
                "criticality": result["criticality"].lower(),
                "estimated_time": result.get("estimated_time", 24)
            }
            
        except (KeyError, StopIteration) as e:
            logger.error("Error parsing crew results: %s", str(e))
            return {
                "category": None,
                "criticality": "medium",
                "estimated_time": 24
            }
