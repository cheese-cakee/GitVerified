"""
GitHub Repository Fetcher

Fetches repository metadata and code content via GitHub API.
Designed for lightweight operation with rate limit awareness.
"""

import os
import re
import time
import json
import hashlib
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

import requests
import structlog

logger = structlog.get_logger(__name__)

# Simple file-based cache directory
CACHE_DIR = Path(__file__).parent.parent / "data" / "github_cache"
CACHE_TTL_SECONDS = 3600  # 1 hour


@dataclass
class RepoMetadata:
    """GitHub repository metadata."""
    owner: str
    name: str
    full_name: str
    description: str
    stars: int
    forks: int
    watchers: int
    language: str
    languages: dict[str, int]
    created_at: str
    updated_at: str
    pushed_at: str
    default_branch: str
    open_issues: int
    topics: list[str]
    is_fork: bool
    license: Optional[str]


@dataclass
class RepoContent:
    """Repository content analysis."""
    readme: str
    main_files: dict[str, str]  # filename -> content
    file_tree: list[str]  # list of file paths
    total_files: int
    languages_breakdown: dict[str, float]  # language -> percentage


@dataclass
class GitHubAnalysis:
    """Complete GitHub repository analysis."""
    url: str
    metadata: Optional[RepoMetadata]
    content: Optional[RepoContent]
    error: Optional[str] = None
    cached: bool = False


class GitHubFetcher:
    """
    Lightweight GitHub API client with caching and rate limit handling.
    
    Rate limits:
    - Unauthenticated: 60 requests/hour
    - Authenticated: 5000 requests/hour
    
    Uses file-based caching to minimize API calls.
    """
    
    BASE_URL = "https://api.github.com"
    
    # File patterns to fetch for code analysis
    IMPORTANT_FILES = [
        "README.md", "readme.md", "README", 
        "main.py", "app.py", "index.py", "server.py",
        "main.js", "index.js", "app.js", "server.js",
        "main.ts", "index.ts", "app.ts", "server.ts",
        "main.go", "main.rs", "main.cpp", "main.c",
        "package.json", "requirements.txt", "Cargo.toml", "go.mod",
        "Dockerfile", "docker-compose.yml",
    ]
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize the GitHub fetcher.
        
        Args:
            token: Optional GitHub PAT for higher rate limits
        """
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitVerified/1.0"
        })
        if token:
            self.session.headers["Authorization"] = f"token {token}"
        
        # Ensure cache directory exists
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        self._rate_limit_remaining = 60
        self._rate_limit_reset = 0
    
    def parse_github_url(self, url: str) -> tuple[Optional[str], Optional[str], bool]:
        """
        Extract owner and repo name from various GitHub URL formats.
        
        Supports:
        - https://github.com/owner/repo (repo URL)
        - https://github.com/owner (profile URL)
        - github.com/owner/repo
        - git@github.com:owner/repo.git
        
        Returns:
            Tuple of (owner, repo, is_profile) 
            - For repos: (owner, repo, False)
            - For profiles: (username, None, True)
            - Invalid: (None, None, False)
        """
        if not url:
            return None, None, False
        
        url = url.strip().rstrip('/')
        
        # Pattern for HTTPS URLs with repo
        repo_pattern = r"(?:https?://)?github\.com/([^/]+)/([^/\s\.]+)"
        match = re.match(repo_pattern, url)
        if match:
            return match.group(1), match.group(2).replace(".git", ""), False
        
        # Pattern for profile URLs (just username)
        profile_pattern = r"(?:https?://)?github\.com/([^/\s]+)/?$"
        match = re.match(profile_pattern, url)
        if match:
            username = match.group(1)
            # Exclude special GitHub paths
            if username not in ['settings', 'notifications', 'explore', 'trending', 'collections']:
                return username, None, True
        
        # Pattern for SSH URLs
        ssh_pattern = r"git@github\.com:([^/]+)/([^/\s\.]+)"
        match = re.match(ssh_pattern, url)
        if match:
            return match.group(1), match.group(2).replace(".git", ""), False
        
        return None, None, False
    
    def fetch_user_repos(self, username: str, max_repos: int = 10) -> list[dict]:
        """
        Fetch a user's public repositories sorted by stars.
        
        Args:
            username: GitHub username
            max_repos: Maximum number of repos to return
            
        Returns:
            List of repo dictionaries with basic metadata
        """
        data, error = self._request(f"/users/{username}/repos?sort=stars&per_page={max_repos}")
        if error or not data:
            logger.warning("Failed to fetch user repos", username=username, error=error)
            return []
        
        repos = []
        for repo in data[:max_repos]:
            if not repo.get("fork", False):  # Skip forks
                repos.append({
                    "name": repo["name"],
                    "full_name": repo["full_name"],
                    "description": repo.get("description") or "",
                    "stars": repo.get("stargazers_count", 0),
                    "language": repo.get("language") or "Unknown",
                    "url": repo.get("html_url", "")
                })
        
        return repos
    
    def _get_cache_key(self, endpoint: str) -> str:
        """Generate cache key from endpoint."""
        return hashlib.md5(endpoint.encode()).hexdigest()
    
    def _get_cached(self, endpoint: str) -> Optional[dict]:
        """Get cached response if valid."""
        cache_key = self._get_cache_key(endpoint)
        cache_file = CACHE_DIR / f"{cache_key}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, "r") as f:
                cached = json.load(f)
            
            # Check TTL
            if time.time() - cached.get("timestamp", 0) > CACHE_TTL_SECONDS:
                cache_file.unlink()
                return None
            
            return cached.get("data")
        except (json.JSONDecodeError, IOError):
            return None
    
    def _set_cached(self, endpoint: str, data: dict) -> None:
        """Cache response data."""
        cache_key = self._get_cache_key(endpoint)
        cache_file = CACHE_DIR / f"{cache_key}.json"
        
        try:
            with open(cache_file, "w") as f:
                json.dump({"timestamp": time.time(), "data": data}, f)
        except IOError:
            pass  # Caching is optional, don't fail on errors
    
    def _request(self, endpoint: str, use_cache: bool = True) -> tuple[Optional[dict], Optional[str]]:
        """
        Make a GitHub API request with caching and rate limit handling.
        
        Returns:
            Tuple of (data, error_message)
        """
        # Check cache first
        if use_cache:
            cached = self._get_cached(endpoint)
            if cached is not None:
                return cached, None
        
        # Check rate limit
        if self._rate_limit_remaining <= 1 and time.time() < self._rate_limit_reset:
            wait_time = int(self._rate_limit_reset - time.time()) + 1
            return None, f"Rate limited. Reset in {wait_time} seconds."
        
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            response = self.session.get(url, timeout=10)
            
            # Update rate limit info
            self._rate_limit_remaining = int(response.headers.get("X-RateLimit-Remaining", 60))
            self._rate_limit_reset = int(response.headers.get("X-RateLimit-Reset", 0))
            
            if response.status_code == 404:
                return None, "Repository not found"
            
            if response.status_code == 403:
                return None, "Access forbidden (rate limited or private repo)"
            
            if response.status_code != 200:
                return None, f"GitHub API error: {response.status_code}"
            
            data = response.json()
            
            # Cache successful responses
            if use_cache:
                self._set_cached(endpoint, data)
            
            return data, None
            
        except requests.Timeout:
            return None, "Request timeout"
        except requests.RequestException as e:
            return None, f"Request failed: {str(e)}"
    
    def fetch_metadata(self, owner: str, repo: str) -> tuple[Optional[RepoMetadata], Optional[str]]:
        """
        Fetch repository metadata.
        
        Returns:
            Tuple of (RepoMetadata, error_message)
        """
        data, error = self._request(f"/repos/{owner}/{repo}")
        if error:
            return None, error
        
        # Fetch languages
        languages_data, _ = self._request(f"/repos/{owner}/{repo}/languages")
        languages = languages_data or {}
        
        try:
            metadata = RepoMetadata(
                owner=data["owner"]["login"],
                name=data["name"],
                full_name=data["full_name"],
                description=data.get("description") or "",
                stars=data.get("stargazers_count", 0),
                forks=data.get("forks_count", 0),
                watchers=data.get("watchers_count", 0),
                language=data.get("language") or "Unknown",
                languages=languages,
                created_at=data.get("created_at", ""),
                updated_at=data.get("updated_at", ""),
                pushed_at=data.get("pushed_at", ""),
                default_branch=data.get("default_branch", "main"),
                open_issues=data.get("open_issues_count", 0),
                topics=data.get("topics", []),
                is_fork=data.get("fork", False),
                license=data.get("license", {}).get("spdx_id") if data.get("license") else None,
            )
            return metadata, None
        except (KeyError, TypeError) as e:
            return None, f"Failed to parse metadata: {str(e)}"
    
    def fetch_file_content(self, owner: str, repo: str, path: str) -> Optional[str]:
        """
        Fetch raw file content from repository.
        
        Returns:
            File content as string, or None if not found
        """
        # Use raw.githubusercontent.com for file content (doesn't count against API rate limit)
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{path}"
        
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                return response.text[:10000]  # Limit to 10KB per file
            return None
        except requests.RequestException:
            return None
    
    def fetch_content(self, owner: str, repo: str) -> tuple[Optional[RepoContent], Optional[str]]:
        """
        Fetch repository content for analysis.
        
        Returns:
            Tuple of (RepoContent, error_message)
        """
        # Fetch README
        readme = None
        for readme_name in ["README.md", "readme.md", "README.rst", "README"]:
            content = self.fetch_file_content(owner, repo, readme_name)
            if content:
                readme = content
                break
        
        # Fetch tree to understand structure
        data, error = self._request(f"/repos/{owner}/{repo}/git/trees/HEAD?recursive=1")
        if error:
            # Try with default branch
            data, error = self._request(f"/repos/{owner}/{repo}/git/trees/main?recursive=1")
        
        file_tree = []
        if data and "tree" in data:
            file_tree = [item["path"] for item in data["tree"] if item["type"] == "blob"]
        
        
        main_files = {}
        for pattern in self.IMPORTANT_FILES:
            # Check root level
            if pattern in file_tree or pattern.lower() in [f.lower() for f in file_tree]:
                content = self.fetch_file_content(owner, repo, pattern)
                if content:
                    main_files[pattern] = content
            
            
            src_path = f"src/{pattern}"
            if src_path in file_tree:
                content = self.fetch_file_content(owner, repo, src_path)
                if content:
                    main_files[src_path] = content
        
        
        languages_breakdown = {}
        if file_tree:
            extensions = {}
            for f in file_tree:
                ext = Path(f).suffix.lower()
                if ext:
                    extensions[ext] = extensions.get(ext, 0) + 1
            
            total = sum(extensions.values())
            ext_to_lang = {
                ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
                ".go": "Go", ".rs": "Rust", ".java": "Java", ".cpp": "C++",
                ".c": "C", ".rb": "Ruby", ".php": "PHP", ".swift": "Swift",
                ".kt": "Kotlin", ".cs": "C#", ".html": "HTML", ".css": "CSS",
            }
            for ext, count in extensions.items():
                if ext in ext_to_lang:
                    lang = ext_to_lang[ext]
                    languages_breakdown[lang] = round(count / total * 100, 1)
        
        content = RepoContent(
            readme=readme or "",
            main_files=main_files,
            file_tree=file_tree[:100],  # Limit to first 100 files
            total_files=len(file_tree),
            languages_breakdown=languages_breakdown,
        )
        
        return content, None
    
    def analyze_profile(self, username: str) -> dict:
        """
        Analyze a user's GitHub profile by fetching their top repos.
        
        Returns:
            Dict with profile analysis including top repos
        """
        logger.info("Analyzing GitHub profile", username=username)
        
        repos = self.fetch_user_repos(username, max_repos=5)
        
        if not repos:
            return {
                "username": username,
                "error": "Could not fetch repositories",
                "repos": []
            }
        
        # Analyze the top repo in detail
        top_repo = repos[0] if repos else None
        top_repo_analysis = None
        
        if top_repo:
            metadata, _ = self.fetch_metadata(username, top_repo["name"])
            content, _ = self.fetch_content(username, top_repo["name"])
            if metadata:
                top_repo_analysis = {
                    "metadata": metadata,
                    "content": content
                }
        
        return {
            "username": username,
            "repos": repos,
            "top_repo_analysis": top_repo_analysis,
            "total_stars": sum(r.get("stars", 0) for r in repos),
            "languages": list(set(r.get("language", "") for r in repos if r.get("language")))
        }
    
    def analyze(self, github_url: str) -> GitHubAnalysis:
        """
        Complete analysis from URL - handles both repos and profiles.
        
        Args:
            github_url: GitHub repository or profile URL
            
        Returns:
            GitHubAnalysis with metadata and content
        """
        owner, repo, is_profile = self.parse_github_url(github_url)
        
        if not owner:
            return GitHubAnalysis(
                url=github_url,
                metadata=None,
                content=None,
                error="Invalid GitHub URL format"
            )
        
        # If it's a profile URL, fetch user's repos and analyze top one
        if is_profile:
            logger.info("Analyzing GitHub profile", username=owner)
            repos = self.fetch_user_repos(owner, max_repos=5)
            
            if not repos:
                return GitHubAnalysis(
                    url=github_url,
                    metadata=None,
                    content=None,
                    error=f"No public repositories found for user {owner}"
                )
            
            # Analyze the top repo
            top_repo = repos[0]
            repo = top_repo["name"]
            logger.info("Using top repo from profile", username=owner, repo=repo, stars=top_repo.get("stars", 0))
        
        logger.info("Analyzing GitHub repository", owner=owner, repo=repo)
        
        # Fetch metadata
        metadata, meta_error = self.fetch_metadata(owner, repo)
        if meta_error:
            return GitHubAnalysis(
                url=github_url,
                metadata=None,
                content=None,
                error=meta_error
            )
        
        # Fetch content
        content, content_error = self.fetch_content(owner, repo)
        
        return GitHubAnalysis(
            url=github_url,
            metadata=metadata,
            content=content,
            error=content_error,
            cached=False
        )
    
    def get_rate_limit_status(self) -> dict:
        """Get current rate limit status."""
        return {
            "remaining": self._rate_limit_remaining,
            "reset_at": self._rate_limit_reset,
            "reset_in": max(0, int(self._rate_limit_reset - time.time())),
        }


# Module-level singleton for convenience
_fetcher: Optional[GitHubFetcher] = None


def get_fetcher(token: Optional[str] = None) -> GitHubFetcher:
    """Get or create the GitHub fetcher singleton.

    Token resolution order:
    1. Explicit argument
    2. GITHUB_TOKEN environment variable
    3. Unauthenticated (60 req/hour — will fail fast on batch runs)

    The singleton is recreated when a token is supplied that differs from
    the current one, so adding a token at runtime takes effect.
    """
    global _fetcher
    resolved_token = token or os.environ.get("GITHUB_TOKEN")
    if _fetcher is None or (resolved_token and getattr(_fetcher, 'token', None) != resolved_token):
        _fetcher = GitHubFetcher(resolved_token)
        if resolved_token:
            logger.info("GitHub fetcher initialised with authenticated token")
        else:
            logger.warning(
                "No GITHUB_TOKEN found — unauthenticated requests limited to "
                "60/hour. Set GITHUB_TOKEN in your environment for batch use."
            )
    return _fetcher


def analyze_github_repo(url: str) -> GitHubAnalysis:
    """
    Convenience function to analyze a GitHub repository.
    
    Args:
        url: GitHub repository URL
        
    Returns:
        GitHubAnalysis with all available data
    """
    return get_fetcher().analyze(url)
