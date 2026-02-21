"""
Direct Tools for Gort
GitHub, Vercel ve Filesystem işlemleri (MCP olmadan)
"""

import os
from typing import Optional, Dict, Any
from github import Github
import httpx
from pathlib import Path

# GitHub setup
def get_github_client():
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return None
    return Github(token)

def get_vercel_token():
    return os.getenv("VERCEL_API_KEY")

# Tool definitions for DeepSeek API
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "create_github_repo",
            "description": "GitHub'da yeni bir PRIVATE repository oluştur (Ümit'in izni ile public yapılabilir)",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_name": {
                        "type": "string",
                        "description": "Repository adı (example: modular-login-system)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Repository açıklaması"
                    }
                },
                "required": ["repo_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_github_repos",
            "description": "Kullanıcının tüm GitHub repository'lerini listele",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "deploy_to_vercel",
            "description": "Vercel'e yeni bir project deploy et",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_name": {
                        "type": "string",
                        "description": "Vercel project adı"
                    },
                    "git_repo_url": {
                        "type": "string",
                        "description": "GitHub repository URL"
                    }
                },
                "required": ["project_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_vercel_projects",
            "description": "Vercel'deki tüm projeleri listele",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_vercel_env",
            "description": "Vercel projesine environment variable ekle",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "Vercel project ID"
                    },
                    "key": {
                        "type": "string",
                        "description": "Environment variable adı"
                    },
                    "value": {
                        "type": "string",
                        "description": "Environment variable değeri"
                    }
                },
                "required": ["project_id", "key", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": "Local dosya sisteminde yeni dosya oluştur",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Dosya yolu (örn: /Users/umitduman/modular-login-system/src/App.tsx)"
                    },
                    "content": {
                        "type": "string",
                        "description": "Dosya içeriği"
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Local dosya sisteminde var olan dosyayı düzenle/üzerine yaz",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Dosya yolu"
                    },
                    "content": {
                        "type": "string",
                        "description": "Dosya içeriği (tamamı)"
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_directory",
            "description": "Local dosya sisteminde yeni klasör oluştur",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Klasör yolu (örn: /Users/umitduman/abcdef)"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Local dosya sisteminden dosya oku",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Dosya yolu"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "Local dosya sisteminde dizin içeriğini listele",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Dizin yolu"
                    }
                },
                "required": ["path"]
            }
        }
    }
]


def create_github_repo(repo_name: str, description: str = "") -> str:
    """GitHub'da yeni repository oluştur (PRIVATE olarak, güvenlik için)"""
    g = get_github_client()
    if not g:
        return "❌ GITHUB_TOKEN ayarlanmamış. .env dosyasında GITHUB_TOKEN ekleyin"
    
    try:
        user = g.get_user()
        
        repo = user.create_repo(
            name=repo_name,
            description=description or f"Repository: {repo_name}",
            private=True,
            auto_init=True
        )
        
        return f"✅ Repository oluşturuldu\n🔗 URL: {repo.html_url}\n📋 Clone: {repo.clone_url}"
    except Exception as e:
        return f"❌ Repository oluşturulurken hata: {e}"


def list_github_repos() -> str:
    """GitHub repository'lerini listele"""
    g = get_github_client()
    if not g:
        return "❌ GITHUB_TOKEN ayarlanmamış"
    
    try:
        user = g.get_user()
        repos = user.get_repos()
        
        result = "📦 GitHub Repositories:\n"
        count = 0
        for repo in repos:
            result += f"- {repo.name}\n  {repo.html_url}\n"
            count += 1
            if count >= 10:
                break
        
        return result if count > 0 else "Hiç repository yok"
    except Exception as e:
        return f"❌ Repository listesi hatası: {e}"


def deploy_to_vercel(project_name: str, git_repo_url: str = "") -> str:
    """Vercel'e deploy et"""
    token = get_vercel_token()
    if not token:
        return "❌ VERCEL_API_KEY ayarlanmamış. .env dosyasında VERCEL_API_KEY ekleyin"
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        payload = {
            "name": project_name,
            "framework": "nextjs",
        }
        if git_repo_url:
            payload["gitRepository"] = {"repo": git_repo_url}
        
        response = httpx.post(
            "https://api.vercel.com/v13/projects",
            headers=headers,
            json=payload,
            timeout=10.0
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            url = data.get("url", "pending")
            return f"✅ Vercel deployment başlatıldı\n🔗 URL: {url}\n📋 Project: {project_name}"
        else:
            return f"❌ Vercel error: {response.text}"
    except Exception as e:
        return f"❌ Deployment hatası: {e}"


def list_vercel_projects() -> str:
    """Vercel projects'i listele"""
    token = get_vercel_token()
    if not token:
        return "❌ VERCEL_API_KEY ayarlanmamış"
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        response = httpx.get(
            "https://api.vercel.com/v9/projects",
            headers=headers,
            timeout=10.0
        )
        
        if response.status_code == 200:
            projects = response.json().get("projects", [])
            result = "📦 Vercel Projects:\n"
            for proj in projects[:10]:
                result += f"- {proj['name']} (ID: {proj['id']})\n"
            return result if projects else "Hiç project yok"
        else:
            return f"❌ Vercel error: {response.text}"
    except Exception as e:
        return f"❌ Project listesi hatası: {e}"


def set_vercel_env(project_id: str, key: str, value: str) -> str:
    """Vercel'e environment variable ekle"""
    token = get_vercel_token()
    if not token:
        return "❌ VERCEL_API_KEY ayarlanmamış"
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        payload = {
            "key": key,
            "value": value,
            "target": ["production", "preview", "development"]
        }
        
        response = httpx.post(
            f"https://api.vercel.com/v10/projects/{project_id}/env",
            headers=headers,
            json=payload,
            timeout=10.0
        )
        
        if response.status_code in [200, 201]:
            return f"✅ Environment variable eklendi: {key}={value[:20]}..."
        else:
            return f"❌ Vercel error: {response.text}"
    except Exception as e:
        return f"❌ Env variable hatası: {e}"


# Local Filesystem Operations
def create_file(path: str, content: str) -> str:
    """Local dosya sisteminde yeni dosya oluştur"""
    try:
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        if file_path.exists():
            return f"❌ Dosya zaten var: {path}"
        
        file_path.write_text(content, encoding='utf-8')
        return f"✅ Dosya oluşturuldu: {path}"
    except Exception as e:
        return f"❌ Dosya oluşturma hatası: {e}"


def write_file(path: str, content: str) -> str:
    """Local dosya sisteminde var olan dosyayı düzenle/üzerine yaz"""
    try:
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding='utf-8')
        return f"✅ Dosya yazıldı: {path}"
    except Exception as e:
        return f"❌ Dosya yazma hatası: {e}"


def read_file(path: str) -> str:
    """Local dosya sisteminden dosya oku"""
    try:
        file_path = Path(path)
        
        if not file_path.exists():
            return f"❌ Dosya bulunamadı: {path}"
        
        content = file_path.read_text(encoding='utf-8')
        return f"📄 {path}\n\n{content}"
    except Exception as e:
        return f"❌ Dosya okuma hatası: {e}"


def create_directory(path: str) -> str:
    """Local dosya sisteminde yeni klasör oluştur"""
    try:
        dir_path = Path(path)
        
        if dir_path.exists():
            return f"❌ Klasör zaten var: {path}"
        
        dir_path.mkdir(parents=True, exist_ok=True)
        return f"✅ Klasör oluşturuldu: {path}"
    except Exception as e:
        return f"❌ Klasör oluşturma hatası: {e}"


def list_directory(path: str) -> str:
    """Local dosya sisteminde dizin içeriğini listele"""
    try:
        dir_path = Path(path)
        
        if not dir_path.exists():
            return f"❌ Dizin bulunamadı: {path}"
        
        if not dir_path.is_dir():
            return f"❌ Yol bir dizin değil: {path}"
        
        result = f"📁 {path}\n\n"
        items = sorted(dir_path.iterdir())
        
        folders = [item for item in items if item.is_dir()]
        files = [item for item in items if item.is_file()]
        
        if folders:
            result += "📂 Dizinler:\n"
            for folder in folders[:20]:
                result += f"  - {folder.name}/\n"
        
        if files:
            result += "\n📄 Dosyalar:\n"
            for file in files[:20]:
                result += f"  - {file.name}\n"
        
        return result if items else "Dizin boş"
    except Exception as e:
        return f"❌ Dizin listeleme hatası: {e}"


# Tool execution dispatcher
async def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Execute a tool and return result"""
    
    if tool_name == "create_github_repo":
        return create_github_repo(
            repo_name=arguments.get("repo_name"),
            description=arguments.get("description", "")
        )
    
    elif tool_name == "list_github_repos":
        return list_github_repos()
    
    elif tool_name == "deploy_to_vercel":
        return deploy_to_vercel(
            project_name=arguments.get("project_name"),
            git_repo_url=arguments.get("git_repo_url", "")
        )
    
    elif tool_name == "list_vercel_projects":
        return list_vercel_projects()
    
    elif tool_name == "set_vercel_env":
        return set_vercel_env(
            project_id=arguments.get("project_id"),
            key=arguments.get("key"),
            value=arguments.get("value")
        )
    
    elif tool_name == "create_file":
        return create_file(
            path=arguments.get("path"),
            content=arguments.get("content")
        )
    
    elif tool_name == "write_file":
        return write_file(
            path=arguments.get("path"),
            content=arguments.get("content")
        )
    
    elif tool_name == "read_file":
        return read_file(
            path=arguments.get("path")
        )
    
    elif tool_name == "create_directory":
        return create_directory(
            path=arguments.get("path")
        )
    
    elif tool_name == "list_directory":
        return list_directory(
            path=arguments.get("path")
        )
    
    else:
        return f"❌ Bilinmeyen tool: {tool_name}"
