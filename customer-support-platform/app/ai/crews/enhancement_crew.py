"""Enhancement Crew for improving the quality of support responses."""
import litellm
from crewai import Agent, Task, Crew, Process

from app.ai.prompts.enhancement import (
    GRAMMAR_ENHANCEMENT_AGENT_PROMPT,
    GRAMMAR_ENHANCEMENT_TASK,
    TONE_ENHANCEMENT_AGENT_PROMPT,
    TONE_ENHANCEMENT_TASK,
)
from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Configure LiteLLM
litellm.api_key = settings.OPENAI_API_KEY


class EnhancementCrew:
    """Crew for enhancing the quality of support responses."""
    
    def __init__(self):
        # LiteLLM configuration
        llm_config = {
            "model": f"{settings.LLM_PROVIDER}/{settings.LLM_MODEL}",
            "temperature": settings.DEFAULT_TEMPERATURE,
            "api_key": settings.OPENAI_API_KEY,
            "max_tokens": 2000,
        }

        self.grammar_agent = Agent(
            role="Grammar and Style Expert",
            goal=("Improve grammar, spelling, and clarity of responses"),
            backstory=GRAMMAR_ENHANCEMENT_AGENT_PROMPT,
            verbose=settings.VERBOSE,
            llm=llm_config,
            allow_delegation=False,
        )

        self.tone_agent = Agent(
            role="Tone and Empathy Specialist",
            goal=("Enhance the tone and empathy of responses"),
            backstory=TONE_ENHANCEMENT_AGENT_PROMPT,
            verbose=settings.VERBOSE,
            llm=llm_config,
            allow_delegation=False,
        )
    
    def enhance_response(self, response: str) -> Dict[str, str]:
        """
        Enhance a support response for grammar, clarity, and tone.
        
        Args:
            response: The original response text
            
        Returns:
            Dict containing the enhanced response and enhancement details
        """
        # Create grammar enhancement task
        grammar_task = Task(
            description=GRAMMAR_ENHANCEMENT_TASK.format(response=response),
            agent=self.grammar_agent,
            expected_output="Improved version of the response with better grammar"
        )
        
        # Create tone enhancement task (depends on grammar task)
        tone_task = Task(
            description=TONE_ENHANCEMENT_TASK.format(
                response="{grammar_enhanced_response}"
            ),
            agent=self.tone_agent,
            context=[grammar_task],
            expected_output="Final enhanced response with improved tone"
        )
        
        # Run the crew
        crew = Crew(
            agents=[self.grammar_agent, self.tone_agent],
            tasks=[grammar_task, tone_task],
            verbose=settings.VERBOSE,
            process=Process.sequential
        )
        
        enhanced_response = crew.kickoff()
        
        return {
            "enhanced_response": enhanced_response,
            "original_response": response,
            "enhancement_applied": "grammar_check,tone_improvement"
        }
    
    def batch_enhance(self, responses: List[str]) -> List[Dict[str, str]]:
        """
        Enhance multiple responses in a batch.
        
        Args:
            responses: List of response texts to enhance
            
        Returns:
            List of enhanced responses with metadata
        """
        enhanced_responses = []
        for response in responses:
            try:
                enhanced = self.enhance_response(response)
                enhanced_responses.append(enhanced)
            except Exception as e:
                logger.error(f"Error enhancing response: {e}")
                enhanced_responses.append({
                    "enhanced_response": response,
                    "original_response": response,
                    "error": str(e),
                    "enhancement_applied": "none"
                })
        
        return enhanced_responses
