from typing import Dict, List, Any
import os
import openai
from .base import BaseAgent, AgentState, Message, MessageType
from ..utils.logging_utils import setup_logger

logger = setup_logger("language_expert")

class LanguageExpertState(AgentState):
    """State of the language expert."""
    language: str = ""
    reviewed_files: List[str] = []
    reviews: Dict[str, Dict[str, Any]] = {}

    class Config:
        arbitrary_types_allowed = True

class LanguageExpert(BaseAgent):
    """Expert agent for reviewing code in a specific language."""
    
    def __init__(self, language_extension: str):
        """Initialize language expert."""
        super().__init__()
        language = self._get_language_name(language_extension)
        self.state = LanguageExpertState(
            agent_id=f'language_expert_{language_extension}',
            language=language
        )
        
        logger.info(f"Initializing language expert for {self.state.language}")
        
        # Initialize OpenAI client
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        openai.api_key = openai_api_key
        
        logger.info(f"Language expert initialized for {self.state.language}")
    
    def process_message(self, message: Message) -> Message:
        """Process incoming messages."""
        if message.type == MessageType.REVIEW_REQUEST:
            file_path = message.content.get('file_path')
            file_content = message.content.get('file_content')
            pr_number = message.content.get('pr_number')
            
            if not file_path or not file_content:
                logger.error("Missing file path or content in review request")
                return Message(
                    type=MessageType.ERROR,
                    content={'error': 'Missing file path or content'},
                    source=self.state.agent_id
                )
            
            logger.info(f"Reviewing file: {file_path}")
            try:
                review = self._review_code(file_path, file_content)
                self.state.reviewed_files.append(file_path)
                self.state.reviews[file_path] = review
                
                return Message(
                    type=MessageType.REVIEW,
                    content={
                        'file_path': file_path,
                        'review': review,
                        'pr_number': pr_number
                    },
                    source=self.state.agent_id
                )
            except Exception as e:
                logger.error(f"Error reviewing {file_path}: {str(e)}")
                return Message(
                    type=MessageType.ERROR,
                    content={'error': str(e)},
                    source=self.state.agent_id
                )
        
        return Message(
            type=MessageType.ERROR,
            content={'error': f'Unsupported message type: {message.type}'},
            source=self.state.agent_id
        )
    
    def _review_code(self, file_path: str, code: str) -> Dict:
        """Review code using OpenAI."""
        logger.info(f"Starting comprehensive review of {file_path}")
        
        # Extract just the filename without full path for OpenAI prompt
        filename = file_path.split('/')[-1]
        
        system_prompt = f"""You are a senior {self.state.language} developer reviewing code.
Provide a thorough code review focusing on:
1. Code quality and best practices
2. Potential bugs or issues
3. Performance considerations
4. Security concerns
5. Improvement suggestions

Format your review in a clear, constructive manner."""

        user_prompt = f"""Review this {self.state.language} code from {filename}:

{code}"""

        try:
            logger.info("Requesting code review from OpenAI")
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            review = response.choices[0].message.content
            logger.info("Received code review from OpenAI")
            
            # Check best practices
            logger.info("Checking best practices")
            violations = self._check_best_practices(code)
            
            # Generate suggestions
            logger.info("Generating improvement suggestions")
            suggestions = self._generate_suggestions(code)
            
            return {
                'review': review,
                'best_practices_violations': violations,
                'suggestions': suggestions
            }
            
        except Exception as e:
            logger.error(f"Error during code review: {str(e)}")
            raise
    
    @staticmethod
    def _get_language_name(ext: str) -> str:
        """Map file extension to programming language."""
        language_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.tsx': 'TypeScript React',
            '.jsx': 'JavaScript React',
            '.java': 'Java',
            '.cpp': 'C++',
            '.go': 'Go',
            '.rs': 'Rust',
            '.rb': 'Ruby',
            '.php': 'PHP',
            '.cs': 'C#'
        }
        return language_map.get(ext, 'Unknown')
    
    @staticmethod
    def _load_best_practices(language: str) -> List[str]:
        """Load language-specific best practices."""
        practices = {
            'Python': [
                'Use type hints',
                'Follow PEP 8',
                'Use meaningful variable names',
                'Write docstrings',
                'Handle exceptions properly'
            ],
            'JavaScript': [
                'Use const/let instead of var',
                'Use === instead of ==',
                'Handle promises properly',
                'Use meaningful variable names',
                'Add proper error handling'
            ],
            'TypeScript': [
                'Use proper type annotations',
                'Avoid any type',
                'Use interfaces for object shapes',
                'Use enums for constants',
                'Follow naming conventions',
                'Handle null and undefined properly',
                'Use async/await for asynchronous code',
                'Implement proper error handling'
            ],
            'TypeScript React': [
                'Use proper type annotations',
                'Define prop types using interfaces',
                'Use functional components with hooks',
                'Implement proper error boundaries',
                'Use proper event handling',
                'Follow React best practices',
                'Use proper state management',
                'Handle side effects properly',
                'Implement proper accessibility',
                'Use proper component composition'
            ]
        }
        return practices.get(language, [])
    
    def _check_best_practices(self, content: str) -> List[str]:
        """Check code against language-specific best practices."""
        logger.info(f"Checking best practices for {self.state.language}")
        system_prompt = f"""You are a {self.state.language} best practices analyzer. 
Check if the code follows these best practices:
{chr(10).join(f'- {p}' for p in self._load_best_practices(self.state.language))}
List only the violations found, be specific."""

        user_prompt = f"Code to analyze:\n```{self.state.language}\n{content}\n```"

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            violations = [v.strip() for v in response.choices[0].message.content.split('\n') if v.strip()]
            logger.info(f"Found {len(violations)} best practice violations")
            return violations
        except Exception as e:
            logger.error(f"Error checking best practices: {str(e)}", exc_info=True)
            raise
    
    def _generate_suggestions(self, content: str) -> List[str]:
        """Generate improvement suggestions for the code."""
        logger.info("Generating improvement suggestions")
        system_prompt = f"""You are a {self.state.language} code improvement expert. 
Suggest specific improvements to make the code better. 
Focus on maintainability, performance, and readability. 
Be concise and actionable."""

        user_prompt = f"Code to improve:\n```{self.state.language}\n{content}\n```"

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            suggestions = [s.strip() for s in response.choices[0].message.content.split('\n') if s.strip()]
            logger.info(f"Generated {len(suggestions)} improvement suggestions")
            return suggestions
        except Exception as e:
            logger.error(f"Error generating suggestions: {str(e)}", exc_info=True)
            raise
