"""
AI module for customer support platform.

This module provides factory functions to create and manage different AI crews
for ticket processing and analysis.
"""
from typing import Dict, Any, TypeVar

from app.ai.crews.analysis_crew import AnalysisCrew
from app.ai.crews.assessment_crew import AssessmentCrew
from app.ai.crews.enhancement_crew import EnhancementCrew
from app.ai.crews.solution_crew import SolutionCrew


TCrew = TypeVar('TCrew', AssessmentCrew, SolutionCrew, EnhancementCrew, AnalysisCrew)

class CrewFactory:
    """Factory class for creating and managing AI crews."""
    
    _crews = {
        'assessment': AssessmentCrew,
        'solution': SolutionCrew,
        'enhancement': EnhancementCrew,
        'analysis': AnalysisCrew
    }
    
    @classmethod
    def create_crew(cls, crew_type: str, **kwargs) -> TCrew:
        """Create a new crew instance.
        
        Args:
            crew_type: Type of crew to create (assessment, solution, enhancement, analysis)
            **kwargs: Additional arguments to pass to the crew constructor
            
        Returns:
            An instance of the requested crew
            
        Raises:
            ValueError: If the crew type is not supported
        """
        crew_class = cls._crews.get(crew_type.lower())
        if not crew_class:
            raise ValueError(f"Unknown crew type: {crew_type}. "
                           f"Available types: {', '.join(cls._crews.keys())}")
        return crew_class(**kwargs)
    
    @classmethod
    def assess_ticket(
        cls, 
        ticket_title: str, 
        ticket_description: str, 
        organization_id: str
    ) -> Dict[str, str]:
        """Assess a ticket using the assessment crew.
        
        Args:
            ticket_title: Title of the ticket
            ticket_description: Description of the ticket
            organization_id: ID of the organization
            
        Returns:
            Dict containing category and criticality
        """
        crew = cls.create_crew('assessment')
        return crew.assess_ticket(ticket_title, ticket_description, organization_id)
    
    @classmethod
    def generate_solution(
        cls,
        ticket_title: str,
        ticket_description: str,
        ticket_category: str,
        ticket_criticality: str,
        num_variants: int = 1
    ) -> Dict[str, Any]:
        """Generate a solution using the solution crew.
        
        Args:
            ticket_title: Title of the ticket
            ticket_description: Description of the ticket
            ticket_category: Category of the ticket
            ticket_criticality: Criticality level (LOW or HIGH)
            num_variants: Number of solution variants to generate
            
        Returns:
            Dict containing the solution(s) and metadata
        """
        crew = cls.create_crew('solution')
        return crew.generate_solution(
            ticket_title,
            ticket_description,
            ticket_category,
            ticket_criticality,
            num_variants
        )
    
    @classmethod
    def enhance_response(
        cls,
        response: str,
        enhancement_type: str = 'grammar'
    ) -> str:
        """Enhance a response using the enhancement crew.
        
        Args:
            response: The response text to enhance
            enhancement_type: Type of enhancement (grammar, tone, etc.)
            
        Returns:
            Enhanced response text
        """
        crew = cls.create_crew('enhancement')
        return crew.enhance(response, enhancement_type)
    
    @classmethod
    def analyze_ticket(
        cls,
        ticket_title: str,
        ticket_description: str,
        ticket_category: str,
        ticket_resolution: str,
        resolution_time_hours: float,
        customer_satisfaction_rating: int
    ) -> str:
        """Analyze a ticket using the analysis crew.
        
        Args:
            ticket_title: Title of the ticket
            ticket_description: Description of the ticket
            ticket_category: Category of the ticket
            ticket_resolution: How the ticket was resolved
            resolution_time_hours: Time taken to resolve in hours
            customer_satisfaction_rating: Rating from 1-5
            
        Returns:
            Analysis text with insights and recommendations
        """
        crew = cls.create_crew('analysis')
        return crew.analyze(
            ticket_title=ticket_title,
            ticket_description=ticket_description,
            ticket_category=ticket_category,
            ticket_resolution=ticket_resolution,
            resolution_time_hours=resolution_time_hours,
            customer_satisfaction_rating=customer_satisfaction_rating
        )

# Export all crew classes and the factory
__all__ = [
    'AnalysisCrew',
    'AssessmentCrew',
    'EnhancementCrew',
    'SolutionCrew',
    'CrewFactory'
]