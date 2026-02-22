#!/usr/bin/env python3
"""
GitHub MCP Server
Provides tools for GitHub repository management
"""

import os
from github import Github
from mcp.server.fastmcp import FastMCP

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

mcp = FastMCP("github")


def get_client():
    if not GITHUB_TOKEN:
        return None
    return Github(GITHUB_TOKEN)


@mcp.tool()
def list_github_repos() -> str:
    """List user's GitHub repositories (first 10)"""
    client = get_client()
    if not client:
        return "ERROR: GITHUB_TOKEN not set"
    
    try:
        user = client.get_user()
        repos = user.get_repos()
        result = "📦 GitHub Repositories:\n"
        count = 0
        for repo in repos:
            result += f"- {repo.name}\n  {repo.html_url}\n"
            count += 1
            if count >= 10:
                break
        return result if count > 0 else "No repositories found"
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def create_github_repo(repo_name: str, description: str = "") -> str:
    """Create a new PRIVATE GitHub repository"""
    client = get_client()
    if not client:
        return "ERROR: GITHUB_TOKEN not set"
    
    try:
        user = client.get_user()
        repo = user.create_repo(
            name=repo_name,
            description=description or f"Repository: {repo_name}",
            private=True,
            auto_init=True
        )
        return f"✅ Repository oluşturuldu\n🔗 URL: {repo.html_url}\n📋 Clone: {repo.clone_url}"
    except Exception as e:
        return f"ERROR: {e}"


if __name__ == "__main__":
    mcp.run()
