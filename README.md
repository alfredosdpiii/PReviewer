# PReviewer - Agentic Pull Request Reviewer

An intelligent PR review system that uses multiple specialized agents to provide comprehensive code reviews.

## Features

- Automated PR analysis and review
- Multi-agent architecture for specialized review tasks
- Language-specific best practices review
- GitHub integration for automated comments
- Support for multiple programming languages

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your GitHub token:
   ```
   GITHUB_TOKEN=your_token_here
   OPENAI_API_KEY=your_openai_key_here
   ```

## Usage

```python
from previewer.orchestrator import PRReviewOrchestrator

reviewer = PRReviewOrchestrator()
reviewer.review_pr("https://github.com/owner/repo/pull/123")
```

## Architecture

1. **Orchestrator Agent**: Coordinates the review process
2. **File Analyzer**: Identifies relevant files and their relationships
3. **Language Experts**: Specialized agents for different programming languages
4. **Report Analyzer**: Summarizes findings and generates final review
