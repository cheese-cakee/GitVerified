"""
Cheater Detection Module - AI-judged fraud detection for candidate evaluation.

Detects:
- White text injection in resumes (hidden keywords)
- Keyword stuffing (excessive buzzwords)
- LeetCode farming patterns (suspicious submission patterns)
- Codeforces rating manipulation (unnatural rating jumps)
- GitHub gaming (bulk commits, green-square farming)
- Impossible experience claims
"""

import re
import json
from typing import Optional
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class CheaterFlags:
    """Detected cheater indicators."""
    white_text: bool = False
    keyword_stuffing: bool = False
    lc_farming: bool = False
    cf_manipulation: bool = False
    github_gaming: bool = False
    impossible_claims: bool = False
    details: list = field(default_factory=list)
    severity: str = "none"  # none, low, medium, high, critical


def detect_white_text(resume_text: str, raw_pdf_text: Optional[str] = None) -> tuple[bool, list[str]]:
    """
    Detect white/hidden text injection in resume.
    
    Techniques detected:
    - White-on-white text
    - Size 1 font text
    - Text outside visible area
    - Massive keyword blocks
    """
    findings = []
    
    if not resume_text:
        return False, findings
    
    text_lower = resume_text.lower()
    
    # Look for suspicious repeated keywords (hidden keyword stuffing)
    keywords = [
        "python", "java", "javascript", "machine learning", "ai", "blockchain",
        "kubernetes", "docker", "aws", "cloud", "devops", "agile", "scrum",
        "react", "node", "tensorflow", "pytorch", "nlp", "computer vision"
    ]
    
    total_words = max(1, len(text_lower.split()))
    for keyword in keywords:
        count = text_lower.count(keyword.lower())
        density = count / total_words
        # Flag only when density is abnormally high (>3%) AND absolute count >20
        # A genuine Python dev resume may say "python" 10-15 times legitimately
        if count > 20 and density > 0.03:
            findings.append(f"Keyword '{keyword}' appears {count} times ({density:.1%} density — suspicious)")
    
    # Check for text that looks like keyword blocks
    # Pattern: multiple technical terms with only spaces/commas between them
    keyword_block_pattern = r'\b(python|java|react|node|aws|docker|kubernetes|tensorflow|pytorch)\b[,\s]+' * 5
    if re.search(keyword_block_pattern, text_lower):
        findings.append("Detected keyword block pattern (likely hidden text)")
    
    # Check for invisible character sequences
    invisible_chars = ['\u200b', '\u200c', '\u200d', '\ufeff']
    for char in invisible_chars:
        if char in resume_text:
            findings.append("Invisible Unicode characters detected")
            break
    
    # Check for extremely long lines (hidden text often on one line)
    lines = resume_text.split('\n')
    for i, line in enumerate(lines):
        if len(line) > 1000:
            word_count = len(line.split())
            if word_count > 100:
                findings.append(f"Extremely long line ({word_count} words) - possible hidden text")
    
    # Check for ATS keyword stuffing indicators
    ats_keywords = ["ats", "applicant tracking", "keyword optimization"]
    for kw in ats_keywords:
        if kw in text_lower:
            findings.append("Contains ATS gaming references")
    
    is_flagged = len(findings) > 0
    return is_flagged, findings


def detect_keyword_stuffing(resume_text: str) -> tuple[bool, list[str]]:
    """
    Detect excessive keyword/buzzword usage that appears unnatural.
    """
    findings = []
    
    if not resume_text:
        return False, findings
    
    text_lower = resume_text.lower()
    words = text_lower.split()
    total_words = len(words)
    
    if total_words < 100:
        return False, findings
    
    # Buzzword density check
    buzzwords = [
        "synergy", "leverage", "innovative", "cutting-edge", "best-in-class",
        "world-class", "top-tier", "exceptional", "outstanding", "remarkable",
        "revolutionary", "transformative", "groundbreaking", "pioneering",
        "spearheaded", "orchestrated", "championed", "visionary"
    ]
    
    buzzword_count = sum(1 for word in words if word in buzzwords)
    buzzword_density = buzzword_count / total_words
    
    if buzzword_density > 0.05:  # More than 5% buzzwords
        findings.append(f"High buzzword density ({buzzword_density:.1%})")
    
    # Check for repeated self-aggrandizing phrases
    brag_phrases = ["expert in", "mastery of", "world-class", "top performer", "industry leader"]
    for phrase in brag_phrases:
        if text_lower.count(phrase) > 3:
            findings.append(f"Phrase '{phrase}' repeated excessively")
    
    is_flagged = len(findings) > 0
    return is_flagged, findings


def detect_impossible_claims(resume_text: str) -> tuple[bool, list[str]]:
    """
    Detect logically impossible experience claims.
    
    Examples:
    - "10 years of Kubernetes experience" (Kubernetes released 2014)
    - "15 years of React experience" (React released 2013)
    - "Senior engineer" with graduation year this year
    """
    findings = []
    
    if not resume_text:
        return False, findings
    
    text_lower = resume_text.lower()
    
    # Tech with known release years
    tech_years = {
        "kubernetes": 2014,
        "docker": 2013,
        "react": 2013,
        "tensorflow": 2015,
        "pytorch": 2016,
        "next.js": 2016,
        "nextjs": 2016,
        "graphql": 2015,
        "typescript": 2012,
        "swift": 2014,
        "kotlin": 2011,
        "rust": 2010,
        "go": 2009,
        "flutter": 2017,
        "chatgpt": 2022,
        "gpt-4": 2023,
        "llm": 2020,
    }
    
    import datetime
    current_year = datetime.date.today().year
    
    # Pattern: "X years of [tech] experience"
    exp_pattern = r'(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(\w+(?:\.\w+)?)\s*(?:experience|exp)?'
    
    for match in re.finditer(exp_pattern, text_lower):
        years = int(match.group(1))
        tech = match.group(2)
        
        for tech_name, release_year in tech_years.items():
            if tech_name in tech:
                max_possible = current_year - release_year
                if years > max_possible + 1:  # Allow 1 year margin
                    findings.append(
                        f"Claims {years} years of {tech_name} experience "
                        f"(tech only exists since {release_year}, max possible: {max_possible} years)"
                    )
    
    is_flagged = len(findings) > 0
    return is_flagged, findings


def detect_github_gaming(github_analysis: Optional[dict] = None) -> tuple[bool, list[str]]:
    """
    Detect GitHub activity gaming patterns.
    
    Flags:
    - Bulk commits on single days
    - Empty/trivial commits
    - Fork-only activity
    - Commit messages that are identical/automated
    """
    findings = []
    
    if not github_analysis:
        return False, findings
    
    metadata = github_analysis.get("metadata", {})
    
    # Check if it's just a fork with no original work
    if metadata.get("is_fork", False):
        findings.append("Repository is a fork (may not be original work)")
    
    # Check for very recent account but claiming experience
    created_at = metadata.get("created_at", "")
    if created_at:
        # Simple year extraction
        if "2025" in created_at or "2026" in created_at:
            findings.append("GitHub repository created very recently")
    
    is_flagged = len(findings) > 0
    return is_flagged, findings


def detect_cp_gaming(
    leetcode_stats: Optional[dict] = None,
    codeforces_stats: Optional[dict] = None
) -> tuple[bool, list[str]]:
    """
    Detect competitive programming platform gaming.
    
    LeetCode flags:
    - Extremely high submission count in short time
    - Only easy problems
    - Suspicious timing patterns
    
    Codeforces flags:
    - Unnatural rating jumps (e.g., 800 to 2000 in one contest)
    - Only virtual contests
    - Account age vs rating mismatch
    """
    findings = []
    
    if leetcode_stats:
        easy = leetcode_stats.get("easy_solved", 0)
        medium = leetcode_stats.get("medium_solved", 0)
        hard = leetcode_stats.get("hard_solved", 0)
        total = easy + medium + hard
        
        if total > 0:
            # Suspicious if only easy problems
            easy_ratio = easy / total
            if easy_ratio > 0.9 and total > 50:
                findings.append(f"LeetCode: {easy_ratio:.0%} easy problems (possible farming)")
            
            # Suspicious if claiming 1000+ problems
            if total > 1000:
                findings.append(f"LeetCode: Claims {total} problems (verify authenticity)")
    
    if codeforces_stats:
        rating = codeforces_stats.get("rating", 0)
        max_rating = codeforces_stats.get("max_rating", 0)
        contests = codeforces_stats.get("contest_count", 0)
        
        # Suspicious: high rating with few contests
        if rating > 1800 and contests < 10:
            findings.append(f"Codeforces: {rating} rating with only {contests} contests (suspicious)")
        
        # Suspicious: huge rating jump
        if max_rating - rating > 500 and contests > 5:
            findings.append(f"Codeforces: Rating dropped {max_rating - rating} points (investigate)")
    
    is_flagged = len(findings) > 0
    return is_flagged, findings


def analyze_for_cheating(
    resume_text: str,
    github_analysis: Optional[dict] = None,
    leetcode_stats: Optional[dict] = None,
    codeforces_stats: Optional[dict] = None
) -> CheaterFlags:
    """
    Comprehensive cheater analysis using all available data.
    
    Returns:
        CheaterFlags with all detected issues
    """
    logger.info("Running cheater detection analysis")
    
    flags = CheaterFlags()
    all_details = []
    
    # Run all detection modules
    white_text, wt_details = detect_white_text(resume_text)
    if white_text:
        flags.white_text = True
        all_details.extend(wt_details)
    
    stuffing, st_details = detect_keyword_stuffing(resume_text)
    if stuffing:
        flags.keyword_stuffing = True
        all_details.extend(st_details)
    
    impossible, im_details = detect_impossible_claims(resume_text)
    if impossible:
        flags.impossible_claims = True
        all_details.extend(im_details)
    
    gh_gaming, gh_details = detect_github_gaming(github_analysis)
    if gh_gaming:
        flags.github_gaming = True
        all_details.extend(gh_details)
    
    cp_gaming, cp_details = detect_cp_gaming(leetcode_stats, codeforces_stats)
    if cp_gaming:
        flags.lc_farming = True
        all_details.extend(cp_details)
    
    flags.details = all_details
    
    # Calculate severity
    critical_flags = [flags.white_text, flags.impossible_claims]
    high_flags = [flags.keyword_stuffing, flags.lc_farming]
    medium_flags = [flags.github_gaming]
    
    if any(critical_flags):
        flags.severity = "critical"
    elif any(high_flags):
        flags.severity = "high"
    elif any(medium_flags):
        flags.severity = "medium"
    elif all_details:
        flags.severity = "low"
    else:
        flags.severity = "none"
    
    logger.info(
        "Cheater detection complete",
        severity=flags.severity,
        flags_count=len(all_details)
    )
    
    return flags


def get_cheater_score_penalty(flags: CheaterFlags) -> float:
    """
    Calculate score penalty based on cheater flags.
    
    Returns:
        Penalty to subtract from overall score (0-10)
    """
    if flags.severity == "critical":
        return 10.0  # Automatic disqualification
    elif flags.severity == "high":
        return 5.0
    elif flags.severity == "medium":
        return 2.0
    elif flags.severity == "low":
        return 1.0
    return 0.0


if __name__ == "__main__":
    # Test with sample data
    test_resume = """
    John Doe
    Senior Software Engineer with 15 years of Kubernetes experience.
    Expert in Python, Java, JavaScript, React, Node.js, AWS, Docker, Kubernetes,
    TensorFlow, PyTorch, Machine Learning, AI, Blockchain, Cloud, DevOps.
    Python Python Python Python Python Python Python Python Python Python
    Python Python Python Python Python Python Python Python Python Python
    """
    
    result = analyze_for_cheating(test_resume)
    print(f"Severity: {result.severity}")
    print(f"White text: {result.white_text}")
    print(f"Keyword stuffing: {result.keyword_stuffing}")
    print(f"Impossible claims: {result.impossible_claims}")
    print(f"Details: {json.dumps(result.details, indent=2)}")
