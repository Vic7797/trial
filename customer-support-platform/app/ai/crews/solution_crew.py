"""
Solution Crew for generating and refining ticket solutions using RAG pipeline.
"""
import litellm
from typing import Dict, Any, List, Optional
from crewai import Agent, Task, Crew, Process

from app.ai.vector_db import VectorDBClient
from app.ai.prompts.solution import (
    SOLUTION_RESEARCH_AGENT_PROMPT,
    SOLUTION_RESEARCH_TASK,
    SOLUTION_WRITE_TASK,
    SOLUTION_WRITER_AGENT_PROMPT,
)
from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

litellm.api_key = settings.OPENAI_API_KEY

class SolutionCrew:
    """Crew for generating and refining ticket solutions using RAG."""

    def __init__(self):
        self.vector_db = VectorDBClient()

    def _make_agents(self, temperature: float) -> Dict[str, Agent]:
        """Initialize agents with given temperature for LLM."""
        llm_config = {
            "model": f"{settings.LLM_PROVIDER}/{settings.LLM_MODEL}",
            "temperature": temperature,
            "api_key": settings.OPENAI_API_KEY,
            "max_tokens": 1500,
        }

        research_agent = Agent(
            role="Solution Researcher",
            goal="Research and gather technical information for solutions",
            backstory=SOLUTION_RESEARCH_AGENT_PROMPT,
            verbose=settings.VERBOSE,
            llm=llm_config,
            allow_delegation=False,
        )

        writer_agent = Agent(
            role="Solution Writer",
            goal="Write detailed, context-aware ticket responses",
            backstory=SOLUTION_WRITER_AGENT_PROMPT,
            verbose=settings.VERBOSE,
            llm=llm_config,
            allow_delegation=False,
        )

        return {"research": research_agent, "writer": writer_agent}

    def _get_rag_context(self, query: str, category: Optional[str]) -> str:
        """Get RAG context from the vector database."""
        try:
            results = self.vector_db.search(
                query=query,
                category=category,
                n_results=settings.TOP_K_RESULTS
            )
            
            if not results:
                logger.warning(
                    "No relevant documents found for query: %s, category: %s",
                    query, category
                )
                return ""
            
            contexts = []
            for doc in results:
                context = f"Document: {doc.page_content}\n"
                if doc.metadata:
                    context += f"Metadata: {doc.metadata}\n"
                contexts.append(context)
            
            return "\n\n".join(contexts)
            
        except Exception as e:
            logger.error("Error getting RAG context: %s", str(e))
            return ""

    def _run_crew(
        self,
        ticket_title: str,
        ticket_description: str,
        ticket_category: str,
        ticket_criticality: str,
        context: str,
        temperature: float
    ) -> str:
        """Run CrewAI to generate a single solution variant."""
        agents = self._make_agents(temperature)

        research_task = Task(
            description=SOLUTION_RESEARCH_TASK.format(
                ticket_title=ticket_title,
                ticket_description=ticket_description,
                ticket_category=ticket_category,
                ticket_criticality=ticket_criticality,
                context=context
            ),
            agent=agents["research"],
            expected_output="Technical details and solution approaches"
        )

        writer_task = Task(
            description=SOLUTION_WRITE_TASK.format(
                ticket_title=ticket_title,
                ticket_criticality=ticket_criticality,
                research="{research_output}"
            ),
            agent=agents["writer"],
            context=[research_task],
            expected_output="A well-written solution to the ticket"
        )

        crew = Crew(
            agents=[agents["research"], agents["writer"]],
            tasks=[research_task, writer_task],
            verbose=settings.VERBOSE,
            process=Process.sequential
        )

        return crew.kickoff()

    def generate_solution(
        self,
        ticket_title: str,
        ticket_description: str,
        ticket_category: str,
        ticket_criticality: str,
        num_variants: int = 1
    ) -> Dict[str, Any]:
        """Generate refined solutions using RAG pipeline via CrewAI."""
        try:
            context = self._get_rag_context(
                query=f"{ticket_title}\n\n{ticket_description}",
                category=ticket_category
            )

            if ticket_criticality.upper() == "HIGH" and num_variants > 1:
                temps = [0.2, 0.5, 0.7]
                temps = temps[:num_variants]
                solutions = []

                for temp in temps:
                    result = self._run_crew(
                        ticket_title,
                        ticket_description,
                        ticket_category,
                        ticket_criticality,
                        context,
                        temp
                    )
                    solutions.append({
                        "solution": result,
                        "temperature": temp
                    })

                return {
                    "solutions": solutions,
                    "context_used": context
                }

            else:
                result = self._run_crew(
                    ticket_title,
                    ticket_description,
                    ticket_category,
                    ticket_criticality,
                    context,
                    temperature=settings.DEFAULT_TEMPERATURE
                )
                return {
                    "solution": result,
                    "context_used": context
                }

        except Exception as e:
            logger.error(f"Failed to generate solution: {e}", exc_info=True)
            return {
                "error": "Failed to generate solution.",
                "details": str(e)
            }
