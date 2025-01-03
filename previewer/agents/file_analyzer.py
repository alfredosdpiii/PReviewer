from typing import List, Set, Dict, Any
import os
from .base import BaseAgent, AgentState, Message, MessageType
from ..utils.logging_utils import setup_logger

logger = setup_logger("file_analyzer")

class FileAnalyzerState(AgentState):
    """State of the file analyzer."""
    excluded_extensions: Set[str] = {
        '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', 
        '.ttf', '.woff', '.woff2', '.eot', '.pdf',
        '.mp3', '.mp4', '.wav', '.avi', '.mov',
        '.zip', '.tar', '.gz', '.rar',
        '.pyc', '.pyo', '.pyd',
        '.map', '.min.js', '.min.css'
    }
    
    excluded_directories: Set[str] = {
        'node_modules', 'dist', 'build', 'assets',
        'static', 'public', 'vendor', '.git'
    }
    
    processed_files: List[str] = []
    related_files_map: Dict[str, Set[str]] = {}
    analyzed_files: List[str] = []
    files_by_language: Dict[str, List[str]] = {}

    class Config:
        arbitrary_types_allowed = True

class FileAnalyzer(BaseAgent):
    """Agent for analyzing files in a PR."""
    
    def __init__(self):
        """Initialize file analyzer."""
        super().__init__()
        self.state = FileAnalyzerState(agent_id='file_analyzer')
        logger.info("Initializing file analyzer")
        logger.info("File analyzer initialized")
    
    def process_message(self, message: Message) -> List[Message]:
        """Process incoming messages."""
        if message.type == MessageType.FILE_ANALYSIS:
            files = message.content.get('files', [])
            pr_number = message.content.get('pr_number')
            
            if not files:
                logger.warning("No files to analyze")
                return [Message(
                    type=MessageType.ERROR,
                    content={'error': 'No files to analyze'},
                    source=self.state.agent_id
                )]
            
            logger.info(f"Analyzing {len(files)} files")
            
            # Filter relevant files
            logger.info("Filtering relevant files")
            relevant_files = []
            for file in files:
                logger.info(f"Processing file: {file}")
                if self._is_relevant_file(file):
                    logger.info(f"File is relevant: {file}")
                    relevant_files.append(file)
                    
            logger.info(f"Filtered {len(relevant_files)} relevant files")
            if not relevant_files:
                logger.warning("No relevant files found")
                return [Message(
                    type=MessageType.ERROR,
                    content={'error': 'No relevant files found'},
                    source=self.state.agent_id
                )]
                
            # Categorize files by language
            files_by_language = {}
            for file in relevant_files:
                ext = self._get_file_extension(file)
                if ext not in files_by_language:
                    files_by_language[ext] = []
                files_by_language[ext].append(file)
                logger.info(f"Categorized {file} as {ext}")
                
            logger.info(f"Files categorized by language: {files_by_language}")
            
            return [Message(
                type=MessageType.FILE_ANALYSIS,
                content={
                    'files_by_language': files_by_language,
                    'pr_number': pr_number
                },
                source=self.state.agent_id
            )]
        
        return [Message(
            type=MessageType.ERROR,
            content={'error': f'Unsupported message type: {message.type}'},
            source=self.state.agent_id
        )]
    
    def _is_relevant_file(self, file_path: str) -> bool:
        """Check if a file is relevant for code review."""
        logger.info(f"Checking if file is relevant: {file_path}")
        # Check file extension
        ext = os.path.splitext(file_path)[1].lower()
        if ext in self.state.excluded_extensions:
            logger.info(f"File excluded due to extension: {ext}")
            return False
            
        # Check directory path
        path_parts = file_path.split(os.path.sep)
        for part in path_parts:
            if part.lower() in self.state.excluded_directories:
                logger.info(f"File excluded due to directory: {part}")
                return False
                
        logger.info(f"File is relevant: {file_path}")
        return True
    
    def _get_file_extension(self, file_path: str) -> str:
        """Get the file extension from a file path."""
        return os.path.splitext(file_path)[1].lower()
