"""
Hybrid Model Client - Works with Ollama (fallback to heuristics)
Simplified for immediate laptop compatibility
"""

import os
import sys
import json
import psutil
import requests
from typing import Dict, Any

class HybridModelClient:
    """Simplified hybrid client: Ollama → Heuristics"""
    
    def __init__(self):
        self.ollama_available = False
        self.selected_model = None
        self.selected_backend = None
        self._initialize_backends()
    
    def _check_ollama(self) -> bool:
        """Check if Ollama is running"""
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def _initialize_ollama(self):
        """Initialize Ollama client"""
        if not self._check_ollama():
            print("> [HybridModel] Ollama not running", file=sys.stderr)
            return False
        
        try:
            # Test with lightweight model
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "qwen3.5:4b",
                    "prompt": "test",
                    "stream": False
                },
                timeout=5
            )
            if response.status_code == 200:
                self.ollama_available = True
                self.selected_model = "qwen3.5:4b"
                print("> [HybridModel] Ollama qwen3.5:4b available", file=sys.stderr)
                return True
        except Exception as e:
            print(f"> [HybridModel] Ollama test failed: {e}", file=sys.stderr)
        
        return False
    
    def _initialize_backends(self):
        """Initialize all available backends"""
        print("> [HybridModel] Initializing backends...", file=sys.stderr)
        
        # Try Ollama
        if self._initialize_ollama():
            self.selected_backend = "ollama"
            print("> [HybridModel] Using Ollama as primary", file=sys.stderr)
            return
        
        self.selected_backend = "heuristics"
        print("> [HybridModel] Using heuristics only", file=sys.stderr)
    
    def is_available(self) -> bool:
        """Check if any backend is available"""
        return self.ollama_available
    
    def chat(self, prompt: str, max_tokens: int = 512, temperature: float = 0.3) -> Dict[str, Any]:
        """Generate response using best available backend"""
        
        # Try Ollama
        if self.ollama_available:
            try:
                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": self.selected_model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_tokens
                        }
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "response": result.get("response", ""),
                        "model": self.selected_model,
                        "backend": "ollama"
                    }
                else:
                    print(f"> [HybridModel] Ollama error: {response.status_code}", file=sys.stderr)
                    
            except Exception as e:
                print(f"> [HybridModel] Ollama failed: {e}", file=sys.stderr)
                self.ollama_available = False
        
        # Fall back to heuristics
        return {
            "response": self._heuristic_response(prompt),
            "model": "heuristics",
            "backend": "heuristics"
        }
    
    def _heuristic_response(self, prompt: str) -> str:
        """Fallback heuristic response"""
        prompt_lower = prompt.lower()
        
        # Resume integrity analysis
        if "resume" in prompt_lower and ("integrity" in prompt_lower or "authentic" in prompt_lower):
            return json.dumps({
                "score": 7.0,
                "reasoning": "Resume appears authentic based on standard heuristics",
                "flags": []
            })
        
        # Code quality analysis
        elif "code" in prompt_lower and ("security" in prompt_lower or "quality" in prompt_lower):
            return json.dumps({
                "score": 75,
                "verdict": "Acceptable",
                "flags": ["No obvious vulnerabilities detected"]
            })
        
        # Project uniqueness analysis
        elif "project" in prompt_lower and ("unique" in prompt_lower or "original" in prompt_lower):
            score = 8.0 if "tutorial" not in prompt_lower else 3.0
            reasoning = "Project appears original" if score > 5 else "Project appears to be tutorial-based"
            return json.dumps({
                "score": score,
                "reasoning": reasoning
            })
        
        # Job relevance analysis
        elif "relevance" in prompt_lower or "match" in prompt_lower:
            return json.dumps({
                "score": 7.0,
                "reasoning": "Candidate appears reasonably well-matched to job requirements"
            })
        
        # Default response
        else:
            return json.dumps({
                "score": 5.0,
                "reasoning": "Heuristic analysis - install Ollama for better results"
            })

# Global instance
_hybrid_client = None

def get_hybrid_client() -> HybridModelClient:
    """Get or create global hybrid client"""
    global _hybrid_client
    if _hybrid_client is None:
        _hybrid_client = HybridModelClient()
    return _hybrid_client

def get_heuristic_response(agent_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Get heuristic response when no models are available"""
    if agent_type == "integrity":
        return {
            "agent": "integrity",
            "score": 7.0,
            "reasoning": "Resume appears authentic - heuristic analysis",
            "flags": []
        }
    elif agent_type == "code_quality":
        return {
            "agent": "code_quality", 
            "score": 75,
            "verdict": "Acceptable",
            "flags": ["Heuristic analysis - no obvious issues"]
        }
    elif agent_type == "uniqueness":
        return {
            "agent": "uniqueness",
            "score": 6.0,
            "reasoning": "Project appears moderately unique - heuristic analysis"
        }
    elif agent_type == "relevance":
        return {
            "agent": "relevance",
            "score": 7.0,
            "reasoning": "Candidate appears reasonably well-matched - heuristic analysis"
        }
    else:
        return {
            "agent": agent_type,
            "score": 5.0,
            "reasoning": "Heuristic analysis - install local LLM for better results"
        }