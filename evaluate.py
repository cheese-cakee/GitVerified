#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitVerified - Local AI-Powered Candidate Evaluation
Main CLI entry point for evaluating candidates
"""

import sys
import json
import os
import argparse
from pathlib import Path
import io

# Fix Windows console encoding for emoji support
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

class CandidateEvaluator:
    """Main evaluation coordinator"""
    
    def __init__(self, use_local_llm=True):
        self.use_local_llm = use_local_llm
        self.results = {}
    
    def evaluate_candidate(self, resume_path, job_description, github_url=None, leetcode_username=None):
        """Run complete evaluation of a candidate"""
        print("🚀 Starting GitVerified Evaluation...")
        print(f"📄 Resume: {resume_path}")
        print(f"💼 Job: {job_description}")
        
        # Initialize results structure
        self.results = {
            "candidate": {
                "resume_path": str(resume_path),
                "job_description": str(job_description),
                "github_url": github_url,
                "leetcode_username": leetcode_username
            },
            "agents": {},
            "final": {}
        }
        
        # 1. Integrity Scan (Resume Analysis)
        print("\n🔍 Step 1: Resume Integrity Scan...")
        try:
            integrity_result = self._scan_resume_integrity(resume_path)
            self.results["agents"]["integrity"] = integrity_result
            print(f"   ✅ Integrity Score: {integrity_result.get('score', 'N/A')}/10")
        except Exception as e:
            print(f"   ❌ Integrity scan failed: {e}")
            self.results["agents"]["integrity"] = {"error": str(e), "score": 0}
        
        # 2. Code Quality Analysis (if code provided or GitHub available)
        if github_url:
            print("\n🛡️  Step 2: Code Quality Analysis...")
            try:
                # Pass GitHub URL directly - code_quality agent fetches code itself
                quality_result = self._scan_code_quality(github_url)
                self.results["agents"]["code_quality"] = quality_result
                print(f"   ✅ Code Quality Score: {quality_result.get('score', 'N/A')}/100")
            except Exception as e:
                print(f"   ❌ Code quality analysis failed: {e}")
                self.results["agents"]["code_quality"] = {"error": str(e), "score": 50}
        
        # 3. Project Uniqueness Analysis
        if github_url:
            print("\n🎨 Step 3: Project Uniqueness Analysis...")
            try:
                uniqueness_result = self._analyze_project_uniqueness(github_url)
                self.results["agents"]["uniqueness"] = uniqueness_result
                print(f"   ✅ Uniqueness Score: {uniqueness_result.get('score', 'N/A')}/10")
            except Exception as e:
                print(f"   ❌ Uniqueness analysis failed: {e}")
                self.results["agents"]["uniqueness"] = {"error": str(e), "score": 5}
        
        # 4. Skills Analysis (LeetCode if available)
        if leetcode_username:
            print("\n💪 Step 4: Technical Skills Analysis...")
            try:
                skills_result = self._analyze_algorithm_skills(leetcode_username)
                self.results["agents"]["skills"] = skills_result
                print(f"   ✅ Skills Score: {skills_result.get('score', 'N/A')}/10")
            except Exception as e:
                print(f"   ❌ Skills analysis failed: {e}")
                self.results["agents"]["skills"] = {"error": str(e), "score": 5}
        
        # 5. Job Relevance Analysis
        print("\n🎯 Step 5: Job Relevance Analysis...")
        try:
            # Extract resume text for relevance matching
            resume_text = self._extract_resume_text(resume_path)
            relevance_result = self._evaluate_job_relevance(resume_text, str(job_description))
            self.results["agents"]["relevance"] = relevance_result
            print(f"   ✅ Relevance Score: {relevance_result.get('score', 'N/A')}/10")
        except Exception as e:
            print(f"   ❌ Relevance analysis failed: {e}")
            self.results["agents"]["relevance"] = {"error": str(e), "score": 5}
        
        # 6. Final Synthesis
        print("\n🤖 Step 6: Final Synthesis...")
        self._synthesize_results()
        
        return self.results
    
    def _scan_resume_integrity(self, resume_path):
        """Resume integrity scan using actual agent"""
        from agents.integrity import scan_resume_integrity
        
        resume_text = self._extract_resume_text(resume_path)
        return scan_resume_integrity(resume_text=resume_text)
    
    def _scan_code_quality(self, github_url):
        """Code quality scan using actual agent"""
        from agents.code_quality import scan_code_quality
        
        return scan_code_quality(github_url=github_url)
    
    def _analyze_project_uniqueness(self, github_url):
        """Project uniqueness analysis using actual agent"""
        from agents.uniqueness import analyze_project_uniqueness
        
        return analyze_project_uniqueness(github_url)
    
    def _analyze_algorithm_skills(self, username):
        """Technical skills analysis using actual agent"""
        from agents.problem_solving import evaluate_cp_profile
        
        return evaluate_cp_profile(username)
    
    def _evaluate_job_relevance(self, resume_text, job_description):
        """Job relevance evaluation using actual agent"""
        from agents.relevance import evaluate_job_relevance
        
        return evaluate_job_relevance(resume_text, job_description)
    
    def _extract_resume_text(self, resume_path):
        """Extract text from resume PDF or text file"""
        from agents.integrity import extract_pdf_text
        
        try:
            # Check if it's a text file first
            path_obj = Path(resume_path)
            if path_obj.suffix.lower() in ['.txt', '.md', '.text']:
                with open(resume_path, 'r', encoding='utf-8') as f:
                    return f.read()[:5000]
            
            # Otherwise try PDF extraction
            text, error = extract_pdf_text(resume_path)
            if error:
                print(f"   ⚠️  PDF extraction failed: {error}")
                return "Resume text extraction failed. Using empty text."
            return text
        except Exception as e:
            print(f"   ⚠️  Resume extraction failed: {e}")
            return "Resume text extraction failed. Using empty text."
    
    def _synthesize_results(self):
        """Synthesize all agent results into final evaluation"""
        agents = self.results["agents"]
        
        # Extract scores with defaults
        integrity_score = agents.get("integrity", {}).get("score", 0)
        quality_score = agents.get("code_quality", {}).get("score", 50) / 10  # Convert to 0-10 scale
        uniqueness_score = agents.get("uniqueness", {}).get("score", 5)
        skills_score = agents.get("skills", {}).get("score", 5)
        relevance_score = agents.get("relevance", {}).get("score", 5)
        
        # Calculate weighted average
        weights = {
            "integrity": 0.20,
            "quality": 0.30, 
            "uniqueness": 0.30,
            "skills": 0.10,
            "relevance": 0.10
        }
        
        overall_score = (
            integrity_score * weights["integrity"] +
            quality_score * weights["quality"] +
            uniqueness_score * weights["uniqueness"] +
            skills_score * weights["skills"] +
            relevance_score * weights["relevance"]
        )
        
        # Generate recommendation
        if overall_score >= 7.0 and integrity_score >= 6.0:
            recommendation = "PASS"
            reasoning = f"Strong candidate with overall score of {overall_score:.1f}/10"
        elif overall_score >= 5.0 and integrity_score >= 4.0:
            recommendation = "WAITLIST"
            reasoning = f"Potential candidate with overall score of {overall_score:.1f}/10"
        else:
            recommendation = "REJECT"
            reasoning = f"Does not meet standards with overall score of {overall_score:.1f}/10"
        
        self.results["final"] = {
            "overall_score": round(overall_score, 1),
            "recommendation": recommendation,
            "reasoning": reasoning,
            "score_breakdown": {
                "integrity": integrity_score,
                "code_quality": quality_score,
                "uniqueness": uniqueness_score,
                "skills": skills_score,
                "relevance": relevance_score
            }
        }
    
    def print_results(self):
        """Print formatted results"""
        final = self.results["final"]
        
        print("\n" + "="*60)
        print("🎯 FINAL EVALUATION RESULTS")
        print("="*60)
        print(f"📊 Overall Score: {final['overall_score']}/10")
        print(f"🏆 Recommendation: {final['recommendation']}")
        print(f"💭 Reasoning: {final['reasoning']}")
        
        print("\n📈 Score Breakdown:")
        breakdown = final["score_breakdown"]
        print(f"   🛡️  Integrity: {breakdown['integrity']}/10")
        print(f"   💻 Code Quality: {breakdown['code_quality']}/10")
        print(f"   🎨 Uniqueness: {breakdown['uniqueness']}/10")
        print(f"   💪 Skills: {breakdown['skills']}/10")
        print(f"   🎯 Relevance: {breakdown['relevance']}/10")
        
        print("\n" + "="*60)

def main():
    parser = argparse.ArgumentParser(description="GitVerified - Local AI-Powered Candidate Evaluation")
    parser.add_argument("resume", help="Path to resume PDF file")
    parser.add_argument("job_desc", help="Path to job description text file or job description string")
    parser.add_argument("--github", help="GitHub repository URL")
    parser.add_argument("--leetcode", help="LeetCode username")
    parser.add_argument("--output", help="Output JSON file for results")
    parser.add_argument("--no-llm", action="store_true", help="Disable local LLM (use heuristics only)")
    
    args = parser.parse_args()
    
    # Validate inputs
    if not os.path.exists(args.resume):
        print(f"❌ Resume file not found: {args.resume}")
        sys.exit(1)
    
    # Check if job_desc is a file or text
    if os.path.exists(args.job_desc):
        with open(args.job_desc, 'r') as f:
            job_description = f.read()
    else:
        job_description = args.job_desc
    
    # Initialize evaluator
    evaluator = CandidateEvaluator(use_local_llm=not args.no_llm)
    
    try:
        # Run evaluation
        results = evaluator.evaluate_candidate(
            resume_path=args.resume,
            job_description=job_description,
            github_url=args.github,
            leetcode_username=args.leetcode
        )
        
        # Print results
        evaluator.print_results()
        
        # Save to file if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\n💾 Results saved to: {args.output}")
        
        print(f"\n🎉 Evaluation complete!")
        
    except KeyboardInterrupt:
        print("\n❌ Evaluation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Evaluation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()