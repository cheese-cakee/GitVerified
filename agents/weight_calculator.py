"""
Dynamic Weight Calculator - AI determines agent weights based on job description.

Analyzes the job description to determine relative importance of each evaluation dimension:
- Code Quality
- Uniqueness  
- Relevance
- Integrity
- Competitive Programming

Returns weights that sum to 1.0.
"""

import re
from typing import Optional
from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class AgentWeights:
    """Weights for each evaluation agent."""
    integrity: float = 0.15
    code_quality: float = 0.30
    uniqueness: float = 0.20
    relevance: float = 0.25
    cp: float = 0.10
    
    def as_dict(self) -> dict:
        return {
            "integrity": self.integrity,
            "code_quality": self.code_quality,
            "uniqueness": self.uniqueness,
            "relevance": self.relevance,
            "cp": self.cp
        }
    
    def normalize(self):
        """Ensure weights sum to 1.0"""
        total = self.integrity + self.code_quality + self.uniqueness + self.relevance + self.cp
        if total > 0:
            self.integrity /= total
            self.code_quality /= total
            self.uniqueness /= total
            self.relevance /= total
            self.cp /= total


# Job type patterns and their associated weight profiles
JOB_PROFILES = {
    "algorithm_engineer": {
        "patterns": ["algorithm", "data structure", "optimization", "leetcode", "competitive", "dsa"],
        "weights": AgentWeights(integrity=0.10, code_quality=0.20, uniqueness=0.15, relevance=0.15, cp=0.40)
    },
    "backend_engineer": {
        "patterns": ["backend", "api", "server", "database", "microservice", "rest", "graphql"],
        "weights": AgentWeights(integrity=0.15, code_quality=0.35, uniqueness=0.20, relevance=0.20, cp=0.10)
    },
    "frontend_engineer": {
        "patterns": ["frontend", "react", "vue", "angular", "ui", "ux", "css", "javascript"],
        "weights": AgentWeights(integrity=0.15, code_quality=0.30, uniqueness=0.25, relevance=0.25, cp=0.05)
    },
    "fullstack_engineer": {
        "patterns": ["full stack", "fullstack", "full-stack", "mern", "mean", "next.js"],
        "weights": AgentWeights(integrity=0.15, code_quality=0.30, uniqueness=0.20, relevance=0.30, cp=0.05)
    },
    "ml_engineer": {
        "patterns": ["machine learning", "ml engineer", "deep learning", "neural", "ai engineer", "nlp", "computer vision"],
        "weights": AgentWeights(integrity=0.15, code_quality=0.25, uniqueness=0.30, relevance=0.20, cp=0.10)
    },
    "data_engineer": {
        "patterns": ["data engineer", "etl", "pipeline", "spark", "hadoop", "airflow", "data warehouse"],
        "weights": AgentWeights(integrity=0.15, code_quality=0.35, uniqueness=0.15, relevance=0.25, cp=0.10)
    },
    "devops_engineer": {
        "patterns": ["devops", "sre", "infrastructure", "kubernetes", "docker", "ci/cd", "terraform"],
        "weights": AgentWeights(integrity=0.20, code_quality=0.30, uniqueness=0.15, relevance=0.30, cp=0.05)
    },
    "systems_engineer": {
        "patterns": ["systems", "kernel", "embedded", "low-level", "c programming", "operating system", "firmware"],
        "weights": AgentWeights(integrity=0.15, code_quality=0.35, uniqueness=0.25, relevance=0.15, cp=0.10)
    },
    "security_engineer": {
        "patterns": ["security", "penetration", "vulnerability", "cybersecurity", "cryptography", "infosec"],
        "weights": AgentWeights(integrity=0.25, code_quality=0.30, uniqueness=0.20, relevance=0.20, cp=0.05)
    },
    "quant_developer": {
        "patterns": ["quant", "trading", "finance", "hedge fund", "algorithmic trading", "hft"],
        "weights": AgentWeights(integrity=0.15, code_quality=0.25, uniqueness=0.15, relevance=0.15, cp=0.30)
    },
}

# Default weights when no specific job type matches
DEFAULT_WEIGHTS = AgentWeights(
    integrity=0.15,
    code_quality=0.30,
    uniqueness=0.20,
    relevance=0.25,
    cp=0.10
)


def detect_job_type(job_description: str) -> tuple[str, float]:
    """
    Detect job type from description.
    
    Returns:
        Tuple of (job_type, confidence)
    """
    if not job_description:
        return "general", 0.0
    
    jd_lower = job_description.lower()
    
    best_match = "general"
    best_score = 0
    
    for job_type, profile in JOB_PROFILES.items():
        score = 0
        for pattern in profile["patterns"]:
            if pattern in jd_lower:
                score += 1
        
        if score > best_score:
            best_score = score
            best_match = job_type
    
    # Calculate confidence (0-1)
    confidence = min(1.0, best_score / 3)  # 3+ matches = 100% confidence
    
    return best_match, confidence


def calculate_weights(job_description: Optional[str] = None) -> dict:
    """
    Calculate agent weights based on job description.
    
    Args:
        job_description: The job posting text
        
    Returns:
        Dictionary with weights and metadata
    """
    logger.info("Calculating dynamic weights")
    
    if not job_description or len(job_description.strip()) < 20:
        return {
            "weights": DEFAULT_WEIGHTS.as_dict(),
            "job_type": "general",
            "confidence": 0.0,
            "reasoning": "No job description provided, using default weights"
        }
    
    job_type, confidence = detect_job_type(job_description)
    
    if job_type == "general" or confidence < 0.3:
        weights = DEFAULT_WEIGHTS
        reasoning = "Job type unclear, using balanced default weights"
    else:
        weights = JOB_PROFILES[job_type]["weights"]
        reasoning = f"Detected {job_type.replace('_', ' ').title()} role with {confidence:.0%} confidence"
    
    logger.info(
        "Weights calculated",
        job_type=job_type,
        confidence=confidence
    )
    
    return {
        "weights": weights.as_dict(),
        "job_type": job_type,
        "confidence": round(confidence, 2),
        "reasoning": reasoning
    }


def apply_weights(
    agent_scores: dict,
    weights: dict
) -> float:
    """
    Apply weights to agent scores to calculate final score.
    
    Args:
        agent_scores: Dict of agent_name -> score (0-10 scale)
        weights: Dict of agent_name -> weight (should sum to 1.0)
        
    Returns:
        Weighted final score (0-10)
    """
    total_score = 0.0
    total_weight = 0.0
    
    for agent, weight in weights.items():
        score = agent_scores.get(agent, 0)
        
        # Handle code_quality which is often on 0-100 scale
        if agent == "code_quality" and score > 10:
            score = score / 10
        
        total_score += score * weight
        total_weight += weight
    
    if total_weight > 0:
        return round(total_score, 1)
    return 0.0


if __name__ == "__main__":
    # Test with different job descriptions
    test_cases = [
        "Looking for a Backend Engineer with experience in Python, FastAPI, and PostgreSQL.",
        "Algorithm Engineer needed for optimization problems. Strong DSA and LeetCode required.",
        "Full Stack Developer with React and Node.js experience for our startup.",
        "ML Engineer to work on NLP and computer vision models using PyTorch.",
        "",  # Empty case
    ]
    
    for jd in test_cases:
        result = calculate_weights(jd)
        print(f"\nJD: {jd[:60]}...")
        print(f"Type: {result['job_type']}, Confidence: {result['confidence']}")
        print(f"Weights: {result['weights']}")
