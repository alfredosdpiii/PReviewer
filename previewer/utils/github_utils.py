from typing import List, Tuple, Optional
import re
import logging
from github import Github, GithubException
from github.PullRequest import PullRequest

logger = logging.getLogger(__name__)

def extract_repo_info(pr_url: str) -> Tuple[str, str, int]:
    """
    Extract repository owner, name and PR number from GitHub PR URL.
    
    Args:
        pr_url: GitHub pull request URL
        
    Returns:
        Tuple of (owner, repo_name, pr_number)
        
    Example:
        >>> extract_repo_info("https://github.com/owner/repo/pull/123")
        ('owner', 'repo', 123)
    """
    pattern = r"github\.com/([^/]+)/([^/]+)/pull/(\d+)"
    match = re.search(pattern, pr_url)
    
    if not match:
        raise ValueError("Invalid GitHub PR URL")
        
    owner = match.group(1)
    repo = match.group(2)
    pr_number = int(match.group(3))
    
    return owner, repo, pr_number

def get_pr_files(pr: PullRequest) -> List[str]:
    """
    Get list of files modified in the pull request.
    
    Args:
        pr: GitHub PullRequest object
        
    Returns:
        List of file paths
    """
    return [f.filename for f in pr.get_files()]

def post_pr_comment(github_client: Github, repo_name: str, pr_number: int, comment: str) -> Optional[str]:
    """Post a comment to a PR. Returns comment URL if successful, None if posting not possible."""
    try:
        logger.info(f"Posting comment to PR #{pr_number} in {repo_name}")
        repo = github_client.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        comment = pr.create_issue_comment(comment)
        return comment.html_url
    except GithubException as e:
        if e.status == 403:
            # This is expected for external repos where we only have read access
            logger.info(f"Cannot post comment to PR #{pr_number} in {repo_name} - repository is read-only (403)")
            return None
        else:
            # Log other GitHub errors as actual errors
            logger.error(f"Failed to post comment: {e.status} {e.data}")
            raise
    except Exception as e:
        logger.error(f"Failed to post comment: {str(e)}")
        raise

def get_pr_file_content(github_client: Github, repo_name: str, pr_number: int, file_path: str) -> Optional[str]:
    """Get the content of a file from a PR."""
    try:
        repo = github_client.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        
        # Get the file from PR files
        pr_file = next((f for f in pr.get_files() if f.filename == file_path), None)
        if not pr_file:
            logger.error(f"File {file_path} not found in PR #{pr_number}")
            return None
            
        # Get the file content from the PR
        contents = repo.get_contents(file_path, ref=pr.head.sha)
        if isinstance(contents, list):
            logger.error(f"File {file_path} is a directory")
            return None
            
        return contents.decoded_content.decode('utf-8')
        
    except Exception as e:
        logger.error(f"Failed to get file content: {str(e)}")
        return None
