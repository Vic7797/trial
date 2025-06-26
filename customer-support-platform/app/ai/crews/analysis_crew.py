"""
Analysis Crew for performing root cause analysis and process improvement.
"""
from typing import Dict, Any
import logging

from crewai import Agent, Task, Crew, Process
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

from app.config import settings
from app.ai.prompts.analysis import (
    ROOT_CAUSE_ANALYST_PROMPT,
    IMPROVEMENT_ANALYST_PROMPT,
    ROOT_CAUSE_ANALYSIS_TASK,
    IMPROVEMENT_ANALYSIS_TASK
)

logger = logging.getLogger(__name__)

class TicketAnalysis(BaseModel):
    """Model for ticket analysis results."""
    ticket_id: str
    root_cause: str
    improvement_recommendations: List[str]
    knowledge_gaps: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AnalysisCrew:
    """Crew for analyzing closed tickets and generating insights."""
    
    def __init__(self):
        # LiteLLM configuration
        llm_config = {
            "model": f"{settings.LLM_PROVIDER}/{settings.LLM_MODEL}",
            "temperature": settings.DEFAULT_TEMPERATURE,
            "api_key": settings.OPENAI_API_KEY,
            "max_tokens": 2000
        }
        
        self.root_cause_agent = Agent(
            role="Root Cause Analyst",
            goal="Identify underlying causes of support issues",
            backstory=ROOT_CAUSE_ANALYST_PROMPT,
            verbose=settings.VERBOSE,
            llm=llm_config,
            allow_delegation=False
        )
        
        self.improvement_agent = Agent(
            role="Process Improvement Specialist",
            goal="Recommend improvements to support processes",
            backstory=IMPROVEMENT_ANALYST_PROMPT,
            verbose=settings.VERBOSE,
            llm=llm_config,
            allow_delegation=False
        )
    
    def analyze_ticket(
        self,
        ticket_id: str,
        ticket_title: str,
        ticket_description: str,
        ticket_category: str,
        ticket_resolution: str,
        resolution_time_hours: float,
        customer_satisfaction_rating: Optional[int] = None
    ) -> TicketAnalysis:
        """
        Analyze a closed support ticket for insights and improvements.
        
        Args:
            ticket_id: Unique identifier for the ticket
            ticket_title: Title of the ticket
            ticket_description: Full description of the ticket
            ticket_category: Category of the ticket
            ticket_resolution: How the ticket was resolved
            resolution_time_hours: Time taken to resolve in hours
            customer_satisfaction_rating: Optional rating from 1-5
            
        Returns:
            TicketAnalysis object with analysis results
        """
        # Create root cause analysis task
        root_cause_task = Task(
            description=ROOT_CAUSE_ANALYSIS_TASK.format(
                ticket_title=ticket_title,
                ticket_description=ticket_description,
                ticket_category=ticket_category,
                ticket_resolution=ticket_resolution,
                resolution_time_hours=resolution_time_hours,
                customer_satisfaction_rating=customer_satisfaction_rating or "Not rated"
            ),
            agent=self.root_cause_agent,
            expected_output="Detailed root cause analysis"
        )
        
        # Create improvement task (depends on root cause analysis)
        improvement_task = Task(
            description=IMPROVEMENT_ANALYSIS_TASK.format(
                root_cause_analysis="{root_cause_analysis}",
                ticket_category=ticket_category,
                resolution_time_hours=resolution_time_hours
            ),
            agent=self.improvement_agent,
            context=[root_cause_task],
            expected_output="Actionable recommendations for improvement"
        )
        
        # Run the crew
        crew = Crew(
            agents=[self.root_cause_agent, self.improvement_agent],
            tasks=[root_cause_task, improvement_task],
            verbose=settings.VERBOSE,
            process=Process.sequential
        )
        
        # Get the analysis results
        analysis = crew.kickoff()
        
        # Parse the analysis (in a real implementation, you'd parse this properly)
        try:
            # This is a simplified example - in practice, you'd parse the output properly
            parts = analysis.split("\n\n")
            root_cause = parts[0] if len(parts) > 0 else "Root cause not determined"
            improvements = [s.strip() for s in parts[1].split("\n") if s.strip()] if len(parts) > 1 else []
            
            return TicketAnalysis(
                ticket_id=ticket_id,
                root_cause=root_cause,
                improvement_recommendations=improvements
            )
        except Exception as e:
            logger.error(f"Error parsing analysis results: {e}")
            return TicketAnalysis(
                ticket_id=ticket_id,
                root_cause="Analysis failed",
                improvement_recommendations=["Failed to analyze ticket"]
            )
    
    def batch_analyze(self, tickets: List[Dict[str, Any]]) -> List[TicketAnalysis]:
        """
        Analyze multiple tickets in a batch.
        
        Args:
            tickets: List of ticket dictionaries with analysis data
            
        Returns:
            List of TicketAnalysis objects
        """
        analyses = []
        for ticket in tickets:
            try:
                analysis = self.analyze_ticket(**ticket)
                analyses.append(analysis)
            except Exception as e:
                logger.error(f"Error analyzing ticket {ticket.get('ticket_id', 'unknown')}: {e}")
                analyses.append(
                    TicketAnalysis(
                        ticket_id=ticket.get('ticket_id', 'unknown'),
                        root_cause=f"Analysis error: {str(e)}",
                        improvement_recommendations=[]
                    )
                )
        
        return analyses
