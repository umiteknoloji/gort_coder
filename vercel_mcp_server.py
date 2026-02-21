#!/usr/bin/env python3
"""
Vercel MCP Server
Provides tools for Vercel deployment management
"""

import os
import sys
from typing import Optional
import httpx

from mcp.server.fastmcp import FastMCP

# Vercel API client
VERCEL_API_KEY = os.getenv("VERCEL_API_KEY", "")
VERCEL_API_BASE = "https://api.vercel.com"

mcp = FastMCP("vercel")


def get_auth_header():
    """Get authorization header for Vercel API"""
    return {"Authorization": f"Bearer {VERCEL_API_KEY}"}


@mcp.tool()
def list_projects() -> str:
    """List all Vercel projects"""
    if not VERCEL_API_KEY:
        return "ERROR: VERCEL_API_KEY not set"
    
    try:
        response = httpx.get(
            f"{VERCEL_API_BASE}/v9/projects",
            headers=get_auth_header()
        )
        response.raise_for_status()
        
        projects = response.json().get("projects", [])
        if not projects:
            return "No projects found"
        
        result = "📦 Vercel Projects:\n"
        for proj in projects:
            result += f"- {proj['name']} ({proj.get('id', 'N/A')})\n"
        return result
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def get_project_info(project_id: str) -> str:
    """Get detailed info about a Vercel project"""
    if not VERCEL_API_KEY:
        return "ERROR: VERCEL_API_KEY not set"
    
    try:
        response = httpx.get(
            f"{VERCEL_API_BASE}/v9/projects/{project_id}",
            headers=get_auth_header()
        )
        response.raise_for_status()
        
        project = response.json()
        result = f"📋 Project: {project['name']}\n"
        result += f"ID: {project['id']}\n"
        result += f"Status: {project.get('status', 'unknown')}\n"
        result += f"Created: {project.get('createdAt', 'N/A')}\n"
        result += f"Framework: {project.get('framework', 'None')}\n"
        return result
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def create_deployment(project_id: str, git_commit: str) -> str:
    """Trigger a deployment for a project"""
    if not VERCEL_API_KEY:
        return "ERROR: VERCEL_API_KEY not set"
    
    try:
        payload = {
            "gitCommitSha": git_commit,
        }
        response = httpx.post(
            f"{VERCEL_API_BASE}/v13/deployments",
            headers=get_auth_header(),
            json=payload
        )
        response.raise_for_status()
        
        deploy = response.json()
        result = f"🚀 Deployment created\n"
        result += f"ID: {deploy.get('id', 'N/A')}\n"
        result += f"URL: {deploy.get('url', 'N/A')}\n"
        result += f"Status: {deploy.get('state', 'queued')}\n"
        return result
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def set_env_variable(project_id: str, name: str, value: str) -> str:
    """Set an environment variable for a Vercel project"""
    if not VERCEL_API_KEY:
        return "ERROR: VERCEL_API_KEY not set"
    
    try:
        payload = {
            "key": name,
            "value": value,
            "target": ["production", "preview", "development"]
        }
        response = httpx.post(
            f"{VERCEL_API_BASE}/v10/projects/{project_id}/env",
            headers=get_auth_header(),
            json=payload
        )
        response.raise_for_status()
        
        result = f"✅ Environment variable set\n"
        result += f"Name: {name}\n"
        result += f"Project: {project_id}\n"
        return result
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def check_deployment_status(deployment_id: str) -> str:
    """Check the status of a deployment"""
    if not VERCEL_API_KEY:
        return "ERROR: VERCEL_API_KEY not set"
    
    try:
        response = httpx.get(
            f"{VERCEL_API_BASE}/v13/deployments/{deployment_id}",
            headers=get_auth_header()
        )
        response.raise_for_status()
        
        deploy = response.json()
        result = f"📊 Deployment Status\n"
        result += f"ID: {deploy.get('id', 'N/A')}\n"
        result += f"Status: {deploy.get('state', 'unknown')}\n"
        result += f"URL: {deploy.get('url', 'N/A')}\n"
        result += f"Created: {deploy.get('createdAt', 'N/A')}\n"
        result += f"Ready: {deploy.get('ready', False)}\n"
        return result
    except Exception as e:
        return f"ERROR: {e}"


if __name__ == "__main__":
    mcp.run()
