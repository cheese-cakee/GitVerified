"""
Uniqueness Agent - Detects tutorial clones vs original work.

Analyzes GitHub repositories to determine if a project is:
- Original, innovative work
- A tutorial clone (todo app, weather app, etc.)
- A fork with minimal changes
- Plagiarized content
"""

import json
import sys
import re
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)

# Common tutorial/clone project patterns
TUTORIAL_PATTERNS = {
    "todo": "To-Do list app (very common tutorial)",
    "weather": "Weather app (common tutorial)",
    "calculator": "Calculator (basic tutorial)",
    "timer": "Timer/Clock app (common tutorial)",
    "clock": "Clock app (common tutorial)",
    "netflix-clone": "Netflix clone (popular tutorial)",
    "spotify-clone": "Spotify clone (popular tutorial)",
    "youtube-clone": "Youtube clone (popular tutorial)",
    "instagram-clone": "Instagram clone (popular tutorial)",
    "twitter-clone": "Twitter clone (popular tutorial)",
    "facebook-clone": "Facebook clone (popular tutorial)",
    "amazon-clone": "Amazon clone (popular tutorial)",
    "e-commerce": "Generic e-commerce (common tutorial)",
    "chat-app": "Chat application (common tutorial)",
    "blog": "Blog platform (common tutorial)",
    "portfolio": "Portfolio website (acceptable but common)",
    "landing-page": "Landing page (very basic)",
}

# Patterns suggesting original work
ORIGINAL_PATTERNS = {
    "kernel": "Low-level systems work",
    "compiler": "Language/compiler work",
    "interpreter": "Language implementation",
    "operating-system": "OS development",
    "framework": "Created a framework",
    "engine": "Game/render engine",
    "algorithm": "Algorithm implementation",
    "protocol": "Protocol implementation",
    "library": "Reusable library",
    "sdk": "SDK development",
    "driver": "Driver/hardware work",
    "emulator": "Emulator development",
    "neural": "ML/Neural network work",
    "distributed": "Distributed systems",
}


def analyze_readme_originality(readme: str) -> tuple[float, list[str]]:
    """
    Analyze README content for originality signals.
    
    Returns:
        Tuple of (score_delta, findings)
    """
    findings = []
    delta = 0.0
    
    readme_lower = readme.lower()
    
    # Negative signals
    if "following tutorial" in readme_lower or "followed tutorial" in readme_lower:
        delta -= 2.0
        findings.append("README mentions following a tutorial")
    
    if "course project" in readme_lower or "bootcamp" in readme_lower:
        delta -= 1.5
        findings.append("README mentions course/bootcamp project")
    
    if "copy" in readme_lower and "paste" in readme_lower:
        delta -= 1.0
        findings.append("README mentions copy-paste")
    
    if "learning" in readme_lower and "project" in readme_lower:
        delta -= 0.5
        findings.append("Described as learning project")
    
    # Positive signals
    if "unique" in readme_lower or "novel" in readme_lower or "innovative" in readme_lower:
        delta += 1.0
        findings.append("README claims originality")
    
    if "research" in readme_lower or "paper" in readme_lower or "published" in readme_lower:
        delta += 1.5
        findings.append("Research/academic work mentioned")
    
    if "patent" in readme_lower:
        delta += 2.0
        findings.append("Patent mentioned")
    
    # Check for detailed technical sections
    if "## Architecture" in readme or "## Design" in readme:
        delta += 0.5
        findings.append("Has architecture documentation")
    
    if "## API" in readme or "## Endpoints" in readme:
        delta += 0.3
        findings.append("Has API documentation")
    
    if len(readme) > 2000:
        delta += 0.5
        findings.append("Comprehensive documentation")
    
    return delta, findings


def analyze_file_structure(file_tree: list[str]) -> tuple[float, list[str]]:
    """
    Analyze file structure for originality signals.
    
    Returns:
        Tuple of (score_delta, findings)
    """
    findings = []
    delta = 0.0
    
    file_count = len(file_tree)
    
    # Very small projects are suspicious
    if file_count < 5:
        delta -= 1.0
        findings.append(f"Very small project ({file_count} files)")
    elif file_count > 50:
        delta += 1.0
        findings.append(f"Substantial codebase ({file_count} files)")
    elif file_count > 100:
        delta += 1.5
        findings.append(f"Large codebase ({file_count} files)")
    
    # Check for test files (indicates maturity)
    test_files = [f for f in file_tree if "test" in f.lower() or "spec" in f.lower()]
    if test_files:
        delta += 0.5
        findings.append(f"Has test suite ({len(test_files)} test files)")
    
    # Check for CI/CD
    ci_files = [f for f in file_tree if any(ci in f.lower() for ci in [".github/workflows", "jenkinsfile", ".gitlab-ci"])]
    if ci_files:
        delta += 0.5
        findings.append("Has CI/CD configuration")
    
    # Check for Docker (production-readiness)
    docker_files = [f for f in file_tree if "dockerfile" in f.lower() or "docker-compose" in f.lower()]
    if docker_files:
        delta += 0.3
        findings.append("Has Docker configuration")
    
    # Check for documentation
    doc_dirs = [f for f in file_tree if f.startswith("docs/") or f.startswith("documentation/")]
    if doc_dirs:
        delta += 0.5
        findings.append("Has documentation directory")
    
    return delta, findings


def analyze_project_uniqueness(
    github_url: Optional[str] = None,
    github_analysis: Optional[dict] = None
) -> dict:
    """
    Analyze project for originality vs tutorial clones.
    
    Args:
        github_url: GitHub repository URL
        github_analysis: Pre-fetched GitHubAnalysis dict
        
    Returns:
        Uniqueness analysis result
    """
    logger.info("Starting uniqueness analysis", url=github_url)
    
    # Base score
    score = 6.0
    findings = []
    tutorial_flags = []
    original_flags = []
    
    metadata = {}
    content = {}
    repo_name = "Unknown"
    
    # Get GitHub data
    if github_analysis:
        metadata = github_analysis.get("metadata", {})
        content = github_analysis.get("content", {})
        repo_name = metadata.get("name", "Unknown")
    elif github_url:
        try:
            from agents.github_fetcher import analyze_github_repo
            analysis = analyze_github_repo(github_url)
            
            if analysis.error:
                return {
                    "agent": "uniqueness",
                    "score": 5.0,
                    "error": f"GitHub fetch failed: {analysis.error}",
                    "reasoning": "Using neutral score due to fetch failure",
                    "backend_used": "heuristics"
                }
            
            metadata = analysis.metadata.__dict__ if analysis.metadata else {}
            content = analysis.content.__dict__ if analysis.content else {}
            repo_name = metadata.get("name", "Unknown")
            
        except ImportError:
            # Fallback to URL-based analysis
            match = re.search(r'github\.com/([^/]+)/([^/\s]+)', github_url or "")
            if match:
                repo_name = match.group(2).replace(".git", "")
    
    repo_name_lower = repo_name.lower()
    
    # Check for tutorial patterns
    for pattern, description in TUTORIAL_PATTERNS.items():
        if pattern in repo_name_lower:
            score -= 2.0
            tutorial_flags.append(description)
            findings.append(f"Name matches tutorial pattern: {pattern}")
    
    # Check for original work patterns
    for pattern, description in ORIGINAL_PATTERNS.items():
        if pattern in repo_name_lower:
            score += 2.0
            original_flags.append(description)
            findings.append(f"Name suggests original work: {pattern}")
    
    # Analyze metadata if available
    if metadata:
        # Check if it's a fork
        if metadata.get("is_fork", False):
            score -= 1.5
            findings.append("Repository is a fork")
        
        # Stars indicate community validation (ordered high → low so correct tier fires)
        stars = metadata.get("stars", 0)
        if stars > 1000:
            score += 2.0
            findings.append(f"Very popular project ({stars} stars)")
        elif stars > 500:
            score += 1.5
            findings.append(f"Popular project ({stars} stars)")
        elif stars > 100:
            score += 1.0
            findings.append(f"Well-received project ({stars} stars)")
        
        # Topics can indicate originality
        topics = metadata.get("topics", [])
        if topics:
            tutorial_topics = ["tutorial", "learning", "course", "bootcamp", "beginner"]
            if any(t in topics for t in tutorial_topics):
                score -= 1.0
                findings.append("Tagged as tutorial/learning project")
            else:
                score += 0.3
                findings.append(f"Has topic tags: {', '.join(topics[:5])}")
    
    # Analyze content if available
    if content:
        # README analysis
        readme = content.get("readme", "")
        if readme:
            readme_delta, readme_findings = analyze_readme_originality(readme)
            score += readme_delta
            findings.extend(readme_findings)
        
        # File structure analysis
        file_tree = content.get("file_tree", [])
        if file_tree:
            struct_delta, struct_findings = analyze_file_structure(file_tree)
            score += struct_delta
            findings.extend(struct_findings)
    
    # Clamp score
    score = max(0.0, min(10.0, score))
    
    # Determine verdict
    if score >= 8.0:
        verdict = "HIGHLY_ORIGINAL"
    elif score >= 6.0:
        verdict = "LIKELY_ORIGINAL"
    elif score >= 4.0:
        verdict = "UNCERTAIN"
    else:
        verdict = "LIKELY_CLONE"
    
    result = {
        "agent": "uniqueness",
        "score": round(score, 1),
        "verdict": verdict,
        "reasoning": "; ".join(findings) if findings else "Analysis complete",
        "tutorial_flags": tutorial_flags,
        "original_flags": original_flags,
        "repo_name": repo_name,
        "backend_used": "github_api" if (github_analysis or github_url) else "heuristics"
    }
    
    logger.info(
        "Uniqueness analysis complete",
        score=score,
        verdict=verdict,
        repo=repo_name
    )
    
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        test_url = "https://github.com/torvalds/linux"
        print(f"Testing with: {test_url}")
        result = analyze_project_uniqueness(github_url=test_url)
    else:
        result = analyze_project_uniqueness(github_url=sys.argv[1])
    
    print(json.dumps(result, indent=2))