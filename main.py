#!/usr/bin/env python3
import sys
from dotenv import load_dotenv
from previewer import PRReviewOrchestrator

def main():
    # Load environment variables from .env
    load_dotenv()
    
    if len(sys.argv) != 2:
        print("Usage: python main.py <github-pr-url>")
        print("Example: python main.py https://github.com/owner/repo/pull/123")
        sys.exit(1)
    
    pr_url = sys.argv[1]
    reviewer = PRReviewOrchestrator()
    reviewer.review_pr(pr_url)

if __name__ == "__main__":
    main()
