from typing import Dict, List, Optional
import os
import json
from github import Github
from pydantic import BaseModel

from .agents.language_expert import LanguageExpert
from .agents.file_analyzer import FileAnalyzer
from .agents.report_analyzer import ReportAnalyzer
from .agents.base import Message, MessageType
from .utils.logging_utils import setup_logger
from .utils.github_utils import post_pr_comment, get_pr_file_content

logger = setup_logger("orchestrator")

class PRReviewOrchestratorState(BaseModel):
    pr_url: Optional[str] = None
    repo_name: Optional[str] = None
    pr_number: Optional[int] = None
    github: Optional[Github] = None
    file_analyzer: Optional[FileAnalyzer] = None
    language_experts: Dict[str, LanguageExpert] = {}
    report_analyzer: Optional[ReportAnalyzer] = None
    status: str = "ready"

    class Config:
        arbitrary_types_allowed = True

class PRReviewOrchestrator(BaseModel):
    state: PRReviewOrchestratorState = PRReviewOrchestratorState()

    class Config:
        arbitrary_types_allowed = True

    def __init__(self):
        logger.info("Initializing PR Review Orchestrator")
        super().__init__()
        
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            logger.error("GITHUB_TOKEN not found in environment variables")
            raise ValueError("GITHUB_TOKEN not found in environment variables")
            
        logger.info("Initializing GitHub client")
        self.state.github = Github(github_token)
        
        logger.info("Initializing agents")
        self.state.file_analyzer = FileAnalyzer()
        self.state.report_analyzer = ReportAnalyzer()
        logger.info("Initialization complete")
    
    async def review_pr(self, pr_url: str):
        """Review a pull request and generate a comprehensive report."""
        logger.info(f"Starting review of PR: {pr_url}")
        self.state.pr_url = pr_url
        self.state.status = "reviewing"
        
        try:
            # Extract PR info
            logger.info("Initializing PR Review Orchestrator")
            yield "Initializing PR Review"
            
            # Initialize GitHub client
            logger.info("Initializing GitHub client")
            self._init_github()
            
            # Initialize agents
            logger.info("Initializing agents")
            self._init_agents()
            
            logger.info("Initialization complete")
            
            # Start PR review
            logger.info(f"Starting review of PR: {pr_url}")
            
            # Extract PR information from URL
            logger.info("Extracting PR information from URL")
            yield "Extracting PR information"
            self.state.repo_name = self._extract_repo_name(pr_url)
            self.state.pr_number = int(pr_url.split('/')[-1])
            logger.info(f"Extracted PR info - Repo: {self.state.repo_name}, PR: {self.state.pr_number}")
            
            # Fetch PR from GitHub
            logger.info("Fetching PR from GitHub")
            yield "Fetching PR from GitHub"
            repo = self.state.github.get_repo(self.state.repo_name)
            pr = repo.get_pull(self.state.pr_number)
            logger.info(f"Found PR: {pr.title}")
            
            # Get files from PR
            logger.info("Fetching PR files from GitHub")
            yield "Fetching PR files"
            files = [f.filename for f in pr.get_files()]
            logger.info(f"Found {len(files)} files to analyze")
            
            # Send files to FileAnalyzer
            logger.info("Sending files to FileAnalyzer")
            if not files:
                logger.warning("No files found in PR")
                yield "No files found to analyze"
                return
                
            response = self.state.file_analyzer.process_message(Message(
                type=MessageType.FILE_ANALYSIS,
                content={
                    'files': files,
                    'pr_number': self.state.pr_number
                },
                source='orchestrator'
            ))
            
            # Process file analyzer responses
            for response in response:
                logger.info(f"Received response of type: {response.type}")
                if response.type == MessageType.FILE_ANALYSIS:
                    logger.info("Received file analysis results")
                    yield "Processing file analysis results"
                    async for progress in self._handle_file_analysis(response, pr):
                        yield progress
                elif response.type == MessageType.ERROR:
                    error_msg = response.content.get('error', 'Unknown error')
                    logger.error(f"Error from FileAnalyzer: {error_msg}")
                    yield f"Error during file analysis: {error_msg}"
            
            if not response:
                logger.warning("No responses received from FileAnalyzer")
                yield "No files to analyze"
            
            self.state.status = "done"
            logger.info("PR review completed successfully")
            yield "Review completed successfully"
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error during PR review: {error_msg}", exc_info=True)
            yield f"Error during PR review: {error_msg}"
            raise
    
    async def _handle_file_analysis(self, message: Message, pr) -> None:
        """Handle file analysis results and initiate code reviews."""
        logger.info("Handling file analysis results")
        
        files_by_language = message.content.get('files_by_language', {})
        if not files_by_language:
            logger.warning("No files to process in analysis results")
            return

        for extension, files in files_by_language.items():
            logger.info(f"Processing {len(files)} {extension} files")
            yield f"Processing {len(files)} {extension} files"

            # Create new language expert
            logger.info(f"Creating new {extension} expert")
            expert = LanguageExpert(extension)
            
            # Process each file
            for file_path in files:
                logger.info(f"Processing {file_path}")
                
                # Fetch file content
                logger.info(f"Fetching content for {file_path}")
                try:
                    content = get_pr_file_content(self.state.github, self.state.repo_name, self.state.pr_number, file_path)
                    if not content:
                        logger.error(f"Failed to fetch content for {file_path}")
                        continue
                        
                    # Request review
                    logger.info(f"Requesting review from {extension} expert for {file_path}")
                    yield f"Analyzing {file_path}"
                    
                    response = expert.process_message(Message(
                        type=MessageType.REVIEW_REQUEST,
                        content={
                            'file_path': file_path,
                            'file_content': content,
                            'pr_number': self.state.pr_number
                        },
                        source='orchestrator'
                    ))
                    
                    # Process expert response
                    if response.type == MessageType.REVIEW:
                        logger.info(f"Received review for {file_path}")
                        if self.state.report_analyzer:
                            report_responses = self.state.report_analyzer.process_message(response)
                            
                            # Process report responses
                            for report_response in report_responses:
                                if report_response.type == MessageType.REPORT:
                                    logger.info("Generated final report")
                                    report = report_response.content.get('report', '')
                                    logger.info(f"Report content: {report}")
                                    
                                    # Send the full review in one message
                                    review_message = json.dumps({
                                        "type": "review",
                                        "message": report
                                    })
                                    logger.info(f"Sending review message: {review_message}")
                                    yield review_message
                                    
                                elif report_response.type == MessageType.ERROR:
                                    error_msg = report_response.content.get('error', 'Unknown error')
                                    logger.error(f"Error from ReportAnalyzer: {error_msg}")
                                    yield f"Error generating report: {error_msg}"
                    
                    elif response.type == MessageType.ERROR:
                        error_msg = response.content.get('error', 'Unknown error')
                        logger.error(f"Error from {extension} expert: {error_msg}")
                        yield f"Error analyzing {file_path}: {error_msg}"
                    
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {str(e)}", exc_info=True)
                    yield f"Error processing {file_path}: {str(e)}"
    
    def _init_github(self):
        """Initialize GitHub client."""
        try:
            if not self.state.github:
                github_token = os.getenv('GITHUB_TOKEN')
                if not github_token:
                    raise ValueError("GITHUB_TOKEN environment variable not set")
                self.state.github = Github(github_token)
                logger.info("GitHub client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize GitHub client: {str(e)}")
            raise

    def _init_agents(self):
        """Initialize review agents."""
        try:
            # Initialize file analyzer if not already initialized
            if not self.state.file_analyzer:
                logger.info("Initializing file analyzer")
                self.state.file_analyzer = FileAnalyzer()
                
            # Initialize report analyzer if not already initialized
            if not self.state.report_analyzer:
                logger.info("Initializing report analyzer")
                self.state.report_analyzer = ReportAnalyzer()
                
            logger.info("Agents initialized")
        except Exception as e:
            logger.error(f"Failed to initialize agents: {str(e)}")
            raise
    
    @staticmethod
    def _extract_repo_name(pr_url: str) -> str:
        """Extract repository name from PR URL."""
        parts = pr_url.split('/')
        return f"{parts[3]}/{parts[4]}"
    
    @staticmethod
    def _extract_pr_number(pr_url: str) -> int:
        """Extract PR number from PR URL."""
        return int(pr_url.split('/')[-1])
