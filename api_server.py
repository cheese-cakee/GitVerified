"""
GitVerified Local API Server
Simple HTTP API for resume evaluation with Ollama
100% Local - No external API tokens required
"""

import json
import os
import sys
import re
import time
import threading
import socketserver
import atexit
import shutil
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
import urllib.request

# Absolute base directory (project root, regardless of cwd)
BASE_DIR = Path(__file__).parent.resolve()

# Max upload size: 20 MB
MAX_UPLOAD_BYTES = 20 * 1024 * 1024

# Allowed CORS origin
CORS_ORIGIN = "http://localhost:3000"

# Add agents to path using absolute path
sys.path.insert(0, str(BASE_DIR / 'agents'))

# Global state for batch processing
batch_state = {
    'is_running': False,
    'should_stop': False,
    'current_index': 0,
    'total_count': 0,
    'results': {
        'leaderboard': [],
        'eliminated': [],
        'flagged': []
    }
}
batch_lock = threading.Lock()

class GitVerifiedHandler(BaseHTTPRequestHandler):
    """Local API handler for GitVerified"""
    
    def send_cors_headers(self):
        # Restrict to the local frontend only — wildcard CORS would allow any
        # page the user visits to silently read candidate data from localhost.
        origin = self.headers.get('Origin', '')
        if origin == CORS_ORIGIN:
            self.send_header('Access-Control-Allow-Origin', CORS_ORIGIN)
        else:
            self.send_header('Access-Control-Allow-Origin', CORS_ORIGIN)
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()
    
    def do_GET(self):
        path = urlparse(self.path).path
        
        if path == '/' or path == '':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(b'''
<!DOCTYPE html>
<html>
<head><title>GitVerified API</title>
<style>
body { font-family: system-ui; padding: 40px; background: #0a0a0a; color: #fff; }
h1 { color: #10b981; }
.endpoint { background: #1a1a1a; padding: 15px; margin: 10px 0; border-radius: 8px; border: 1px solid #333; }
.method { color: #3b82f6; font-weight: bold; }
.status { color: #10b981; }
</style>
</head>
<body>
<h1>GitVerified API Server</h1>
<p class="status">Server is running!</p>
<p>Local AI-powered candidate evaluation. No API tokens required.</p>

<div class="endpoint">
<h3><span class="method">POST</span> /api/evaluate</h3>
<p>Evaluate a candidate resume with AI</p>
</div>

<div class="endpoint">
<h3><span class="method">GET</span> /api/status</h3>
<p>Check system status (Ollama, backend health)</p>
</div>

<div class="endpoint">
<h3><span class="method">GET</span> /api/leaderboard</h3>
<p>Get candidate leaderboard</p>
</div>

<p style="color: #666; margin-top: 30px;">Frontend: <a href="http://localhost:3000" style="color: #3b82f6;">http://localhost:3000</a></p>
</body>
</html>
            ''')
            return
        
        elif path == '/api/status':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            
            status = self.check_system_status()
            self.wfile.write(json.dumps(status).encode())
            return

        elif path == '/api/leaderboard':
            self.handle_leaderboard()
            return
        
        elif path == '/api/batch/progress':
            self.handle_batch_progress()
            return
        
        self.send_response(404)
        self.end_headers()
    
    def do_POST(self):
        path = urlparse(self.path).path
        
        if path == '/api/evaluate':
            self.handle_evaluate()
            return
        
        if path == '/api/evaluate/batch':
            self.handle_batch_evaluate()
            return
        
        if path == '/api/evaluate/stop':
            self.handle_stop_evaluation()
            return
        
        self.send_response(404)
        self.send_cors_headers()
        self.end_headers()
    
    def parse_multipart(self, content_type, body):
        """Simple multipart form parser"""
        result = {'files': {}, 'fields': {}}
        
        # Extract boundary
        boundary_match = re.search(r'boundary=(.+?)(?:;|$)', content_type)
        if not boundary_match:
            return result
        
        boundary = boundary_match.group(1).strip()
        if boundary.startswith('"') and boundary.endswith('"'):
            boundary = boundary[1:-1]
        
        # Split by boundary
        parts = body.split(('--' + boundary).encode())
        
        for part in parts:
            if not part or part == b'--' or part == b'--\r\n':
                continue
            
            # Split headers from content
            try:
                if b'\r\n\r\n' in part:
                    header_section, content = part.split(b'\r\n\r\n', 1)
                elif b'\n\n' in part:
                    header_section, content = part.split(b'\n\n', 1)
                else:
                    continue
                
                header_text = header_section.decode('utf-8', errors='ignore')
                
                # Extract field name
                name_match = re.search(r'name="([^"]+)"', header_text)
                if not name_match:
                    continue
                
                field_name = name_match.group(1)
                
                # Check if it's a file
                filename_match = re.search(r'filename="([^"]+)"', header_text)
                
                # Clean content (remove trailing boundary markers)
                content = content.rstrip(b'\r\n').rstrip(b'--').rstrip(b'\r\n')
                
                if filename_match:
                    result['files'][field_name] = {
                        'filename': filename_match.group(1),
                        'content': content
                    }
                else:
                    result['fields'][field_name] = content.decode('utf-8', errors='ignore').strip()
                    
            except Exception as e:
                print(f"Error parsing part: {e}")
                continue
        
        return result
    
    def handle_leaderboard(self):
        """Get leaderboard data from stored evaluations"""
        try:
            evals_dir = BASE_DIR / "data" / "evaluations"
            candidates = []
            
            if evals_dir.exists():
                for eval_file in evals_dir.glob("*.json"):
                    try:
                        with open(eval_file, "r") as f:
                            data = json.load(f)
                            
                        # Extract info
                        final = data.get("final", {})
                        candidate = data.get("candidate", {})
                        agents = data.get("agents", {})
                        
                        # Determine name
                        name = "Unknown Candidate"
                        resume_path = candidate.get("resume_path", "")
                        if resume_path and "tmp" not in resume_path:
                            name = Path(resume_path).stem.replace("_", " ").title()
                        elif candidate.get("github_url"):
                            name = candidate.get("github_url").split("/")[-1]
                        elif candidate.get("leetcode_username"):
                            name = candidate.get("leetcode_username")
                            
                        # Add to list
                        candidates.append({
                            "id": eval_file.stem,
                            "name": name,
                            "role": "Software Engineer", # Inferred or default
                            "overall_score": final.get("overall_score", 0),
                            "status": final.get("recommendation", "REVIEW"),
                            "date": time.strftime('%Y-%m-%d', time.localtime(eval_file.stat().st_mtime)),
                            "skills": ["Python", "React", "Node.js"], # Placeholder or extracted
                            "details": {
                                "integrity": final.get("score_breakdown", {}).get("integrity", 0),
                                "quality": final.get("score_breakdown", {}).get("code_quality", 0),
                                "cp": agents.get("cp", {}).get("score", 0)
                            }
                        })
                    except Exception as e:
                        print(f"Error reading eval {eval_file}: {e}")
            
            # Sort by score desc
            candidates.sort(key=lambda x: x["overall_score"], reverse=True)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(candidates).encode())
            
        except Exception as e:
            print(f"Leaderboard error: {e}")
            self.send_response(500)
            self.end_headers()
    
    def handle_batch_progress(self):
        """Get current batch processing progress"""
        global batch_state
        
        with batch_lock:
            progress = {
                'is_running': batch_state['is_running'],
                'current': batch_state['current_index'],
                'total': batch_state['total_count'],
                'percentage': round(batch_state['current_index'] / max(1, batch_state['total_count']) * 100, 1),
                'results': {
                    'leaderboard_count': len(batch_state['results']['leaderboard']),
                    'eliminated_count': len(batch_state['results']['eliminated']),
                    'flagged_count': len(batch_state['results']['flagged'])
                }
            }
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(progress).encode())
    
    def handle_stop_evaluation(self):
        """Stop the current batch evaluation"""
        global batch_state
        
        with batch_lock:
            if batch_state['is_running']:
                batch_state['should_stop'] = True
                message = "Stop requested"
            else:
                message = "No batch running"
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps({'message': message}).encode())
    
    def handle_batch_evaluate(self):
        """Handle batch resume evaluation"""
        global batch_state

        try:
            content_type = self.headers.get('Content-Type', '')
            content_length = int(self.headers.get('Content-Length', 0))

            if content_length > MAX_UPLOAD_BYTES:
                self.send_response(413)
                self.send_header('Content-Type', 'application/json')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({'error': f'Upload exceeds {MAX_UPLOAD_BYTES // (1024*1024)} MB limit'}).encode())
                return

            body = self.rfile.read(content_length)
            
            job_description = ''
            resumes = []
            
            if 'multipart/form-data' in content_type:
                parsed = self.parse_multipart(content_type, body)
                job_description = parsed['fields'].get('job_description', '')
                
                # Collect all resume files
                for field_name, file_data in parsed['files'].items():
                    if 'resume' in field_name or field_name.endswith('.pdf'):
                        resumes.append({
                            'filename': file_data['filename'],
                            'content': file_data['content']
                        })
            
            if not resumes:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'No resumes provided'}).encode())
                return
            
            # Initialize batch state
            with batch_lock:
                batch_state['is_running'] = True
                batch_state['should_stop'] = False
                batch_state['current_index'] = 0
                batch_state['total_count'] = len(resumes)
                batch_state['results'] = {
                    'leaderboard': [],
                    'eliminated': [],
                    'flagged': []
                }
            
            print(f"\n{'='*50}")
            print(f"Starting BATCH evaluation: {len(resumes)} resumes")
            print(f"{'='*50}\n")
            
            # Save resumes and process — use absolute paths from BASE_DIR
            upload_dir = BASE_DIR / "data" / "uploads" / "batch"
            upload_dir.mkdir(parents=True, exist_ok=True)

            for i, resume_data in enumerate(resumes):
                # Check for stop request
                with batch_lock:
                    if batch_state['should_stop']:
                        print("Batch stopped by user")
                        break
                    # Increment AFTER the stop check so reported count matches
                    # actual completions — previously incremented before check,
                    # causing off-by-one in the final processed count.
                    batch_state['current_index'] = i + 1

                # Sanitize filename: strip path components, allow only safe chars,
                # and force .pdf extension to prevent path traversal.
                safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', Path(resume_data['filename']).name)
                filename = f"batch_{int(time.time())}_{i}_{safe_name}.pdf"
                resume_path = str(upload_dir / filename)
                
                try:
                    with open(resume_path, "wb") as f:
                        f.write(resume_data['content'])
                    
                    print(f"\n[{i+1}/{len(resumes)}] Processing: {resume_data['filename']}")
                    
                    # Extract GitHub URL from resume
                    resume_text = self.extract_resume_text(resume_path)
                    github_url = self.extract_github_from_resume(resume_text) or ''
                    
                    # Categorize based on GitHub presence
                    if not github_url:
                        # No GitHub = Eliminated
                        with batch_lock:
                            batch_state['results']['eliminated'].append({
                                'name': Path(resume_data['filename']).stem.replace('_', ' ').title(),
                                'filename': resume_data['filename'],
                                'reason': 'No GitHub URL found',
                                'category': 'NO_GITHUB'
                            })
                        print(f"  -> ELIMINATED: No GitHub URL")
                        continue
                    
                    # Run full evaluation
                    result = self.run_evaluation(resume_path, job_description, github_url, None, None)
                    
                    # Determine category based on results
                    final = result.get('final', {})
                    agents = result.get('agents', {})
                    integrity = agents.get('integrity', {})
                    
                    candidate_data = {
                        'name': Path(resume_data['filename']).stem.replace('_', ' ').title(),
                        'filename': resume_data['filename'],
                        'score': final.get('overall_score', 0),
                        'recommendation': final.get('recommendation', 'REVIEW'),
                        'github_url': github_url,
                        'details': result
                    }
                    
                    # Check for cheater flags
                    cheater_flags = integrity.get('flags', [])
                    has_white_text = any('white' in str(f).lower() or 'hidden' in str(f).lower() for f in cheater_flags)
                    has_keyword_stuffing = any('stuff' in str(f).lower() or 'spam' in str(f).lower() for f in cheater_flags)
                    
                    with batch_lock:
                        if has_white_text or has_keyword_stuffing:
                            candidate_data['flags'] = cheater_flags
                            batch_state['results']['flagged'].append(candidate_data)
                            print(f"  -> FLAGGED: {cheater_flags}")
                        elif final.get('recommendation') == 'REJECT':
                            candidate_data['reason'] = final.get('reasoning', 'Score too low')
                            batch_state['results']['eliminated'].append(candidate_data)
                            print(f"  -> ELIMINATED: {final.get('reasoning', 'Low score')[:50]}")
                        else:
                            batch_state['results']['leaderboard'].append(candidate_data)
                            print(f"  -> LEADERBOARD: Score {final.get('overall_score', 0)}")
                    
                except Exception as e:
                    print(f"  -> ERROR: {e}")
                    with batch_lock:
                        batch_state['results']['eliminated'].append({
                            'name': Path(resume_data['filename']).stem.replace('_', ' ').title(),
                            'filename': resume_data['filename'],
                            'reason': f'Processing error: {str(e)}',
                            'category': 'ERROR'
                        })
            
            # Sort leaderboard by score and snapshot all state under the lock
            # to avoid a race where a new batch resets current_index to 0
            # between the lock release and the response write.
            with batch_lock:
                batch_state['results']['leaderboard'].sort(
                    key=lambda x: x.get('score', 0),
                    reverse=True
                )
                batch_state['is_running'] = False
                final_results = {
                    'leaderboard': list(batch_state['results']['leaderboard']),
                    'eliminated': list(batch_state['results']['eliminated']),
                    'flagged': list(batch_state['results']['flagged']),
                }
                final_processed = batch_state['current_index']  # read inside lock

            print(f"\n{'='*50}")
            print(f"Batch complete:")
            print(f"  Leaderboard: {len(final_results['leaderboard'])}")
            print(f"  Eliminated: {len(final_results['eliminated'])}")
            print(f"  Flagged: {len(final_results['flagged'])}")
            print(f"{'='*50}\n")

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({
                'status': 'complete',
                'processed': final_processed,
                'total': len(resumes),
                'results': final_results
            }).encode())
            
        except Exception as e:
            print(f"Batch evaluation error: {e}")
            import traceback
            traceback.print_exc()
            
            with batch_lock:
                batch_state['is_running'] = False
            
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def handle_evaluate(self):
        """Handle resume evaluation request"""
        try:
            content_type = self.headers.get('Content-Type', '')
            content_length = int(self.headers.get('Content-Length', 0))

            if content_length > MAX_UPLOAD_BYTES:
                self.send_response(413)
                self.send_header('Content-Type', 'application/json')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({'error': f'Upload exceeds {MAX_UPLOAD_BYTES // (1024*1024)} MB limit'}).encode())
                return

            body = self.rfile.read(content_length)
            
            resume_path = None
            job_description = ''
            github_url = ''
            leetcode_username = ''
            codeforces_username = ''
            
            if 'multipart/form-data' in content_type:
                # Parse multipart form data
                parsed = self.parse_multipart(content_type, body)
                
                job_description = parsed['fields'].get('job_description', '')
                github_url = parsed['fields'].get('github_url', '')
                leetcode_username = parsed['fields'].get('leetcode_username', '')
                codeforces_username = parsed['fields'].get('codeforces_username', '')
                
                # Save resume file — use absolute path, force .pdf extension
                if 'resume' in parsed['files']:
                    file_data = parsed['files']['resume']
                    upload_dir = BASE_DIR / "data" / "uploads"
                    upload_dir.mkdir(parents=True, exist_ok=True)

                    filename = f"resume_{int(time.time())}.pdf"
                    resume_path = str(upload_dir / filename)

                    with open(resume_path, "wb") as f:
                        f.write(file_data['content'])
                    print(f"Saved resume to: {resume_path}")
                    
            elif 'application/json' in content_type:
                data = json.loads(body) if body else {}
                job_description = data.get('job_description', '')
                github_url = data.get('github_url', '')
                leetcode_username = data.get('leetcode_username', '')
                codeforces_username = data.get('codeforces_username', '')
                resume_path = data.get('resume_path', '')
            
            # Run evaluation
            result = self.run_evaluation(resume_path, job_description, github_url, leetcode_username, codeforces_username)
            
            # Save evaluation result using absolute path
            try:
                evals_dir = BASE_DIR / "data" / "evaluations"
                evals_dir.mkdir(parents=True, exist_ok=True)
                eval_id = f"eval_{int(time.time())}"
                save_path = str(evals_dir / f"{eval_id}.json")
                with open(save_path, "w") as f:
                    json.dump(result, f, indent=2)
                print(f"Saved evaluation to {save_path}")
            except Exception as e:
                print(f"Failed to save evaluation: {e}")
            
            # Send response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
            
        except Exception as e:
            print(f"Evaluation error: {e}")
            import traceback
            traceback.print_exc()
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def run_evaluation(self, resume_path, job_description, github_url, leetcode_username=None, codeforces_username=None):
        """Run candidate evaluation using local agents + Ollama"""
        print(f"\n{'='*50}")
        print("Starting GitVerified Evaluation")
        print(f"Resume: {resume_path}")
        print(f"Job: {job_description[:50]}..." if job_description else "No job description")
        print(f"{'='*50}\n")
        
        results = {
            'status': 'complete',
            'candidate': {
                'resume_path': resume_path or 'uploaded',
                'job_description': job_description,
                'github_url': github_url,
                'leetcode_username': leetcode_username,
                'codeforces_username': codeforces_username
            },
            'agents': {},
            'final': {}
        }
        
        # Try to use hybrid model client
        client = None
        use_ai = False
        try:
            from hybrid_model import get_hybrid_client
            client = get_hybrid_client()
            use_ai = client.is_available()
            print(f"Ollama available: {use_ai}")
        except Exception as e:
            print(f"Could not load hybrid model: {e}")
        
        # Extract resume text
        resume_text = self.extract_resume_text(resume_path)
        
        # If no GitHub URL provided, try to extract from resume
        if not github_url:
            extracted_url = self.extract_github_from_resume(resume_text)
            if extracted_url:
                github_url = extracted_url
                print(f"Extracted GitHub URL from resume: {github_url}")
        
        # Extract LeetCode/Codeforces usernames from resume links
        if not leetcode_username:
            leetcode_username = self.extract_leetcode_from_resume(resume_text)
            if leetcode_username:
                print(f"Extracted LeetCode username: {leetcode_username}")
        
        if not codeforces_username:
            codeforces_username = self.extract_codeforces_from_resume(resume_text)
            if codeforces_username:
                print(f"Extracted Codeforces username: {codeforces_username}")
        
        # Fetch GitHub data once, share across agents
        github_analysis = None
        if github_url:
            try:
                from github_fetcher import analyze_github_repo
                analysis = analyze_github_repo(github_url)
                if not analysis.error:
                    github_analysis = {
                        'metadata': analysis.metadata.__dict__ if analysis.metadata else {},
                        'content': analysis.content.__dict__ if analysis.content else {}
                    }
                    print(f"Fetched GitHub data: {analysis.metadata.full_name if analysis.metadata else 'N/A'}")
                else:
                    print(f"GitHub fetch warning: {analysis.error}")
            except Exception as e:
                print(f"GitHub fetch failed: {e}")
        
        # Run agents
        print("\nRunning Integrity Scan...")
        results['agents']['integrity'] = self.run_integrity_agent(resume_text, github_analysis, client, use_ai)
        
        print("Running Code Quality Analysis...")
        results['agents']['code_quality'] = self.run_code_quality_agent(github_url, github_analysis, client, use_ai)
        
        print("Running Uniqueness Analysis...")
        results['agents']['uniqueness'] = self.run_uniqueness_agent(github_url, github_analysis, client, use_ai)
        
        print("Running Relevance Analysis...")
        results['agents']['relevance'] = self.run_relevance_agent(resume_text, job_description, client, use_ai)
        
        print("Running Competitive Programming Analysis...")
        results['agents']['cp'] = self.run_cp_agent(leetcode_username, codeforces_username, resume_text, client, use_ai)
        
        # Synthesize final result
        print("\nSynthesizing results...")
        results['final'] = self.synthesize_results(results['agents'], job_description)
        
        print(f"\nFinal Score: {results['final']['overall_score']}/10")
        print(f"Recommendation: {results['final']['recommendation']}\n")
        
        return results
    
    def extract_resume_text(self, resume_path):
        """Extract text AND hyperlinks from PDF resume"""
        try:
            import fitz
            doc = fitz.open(resume_path)
            text = ""
            links = []
            
            for page in doc:
                text += page.get_text()
                
                # Extract hyperlinks from the page
                for link in page.get_links():
                    if link.get("uri"):
                        links.append(link["uri"])
            
            doc.close()
            
            # Append found links to the text so they can be extracted
            if links:
                text += "\n\n--- EXTRACTED LINKS ---\n"
                text += "\n".join(links)
                print(f"Extracted {len(links)} hyperlinks from PDF")
            
            return text[:8000]  # Increased limit
        except ImportError:
            print("PyMuPDF not installed - using placeholder")
            return "Resume text extraction requires: pip install pymupdf"
        except Exception as e:
            print(f"PDF extraction failed: {e}")
            return f"Could not extract text: {e}"
    
    def extract_github_from_resume(self, resume_text):
        """Extract GitHub URL (profile or repo) from resume text.

        Trailing punctuation (periods, commas, closing parens) is stripped
        so 'github.com/user/repo.' does not produce a broken URL.
        """
        if not resume_text:
            return None

        # Capture repo URL; stop before any trailing punctuation/whitespace
        repo_pattern = r'https?://github\.com/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_.-]+?)(?=[.,;)\s]|$)'
        match = re.search(repo_pattern, resume_text)
        if match:
            return f'https://github.com/{match.group(1)}/{match.group(2)}'

        # Repo without https scheme
        repo_pattern = r'github\.com/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_.-]+?)(?=[.,;)\s]|$)'
        match = re.search(repo_pattern, resume_text)
        if match:
            return f'https://github.com/{match.group(1)}/{match.group(2)}'

        # Profile URL
        profile_pattern = r'https?://github\.com/([a-zA-Z0-9_-]+?)(?=[.,;)\s/]|$)'
        match = re.search(profile_pattern, resume_text)
        if match:
            return f'https://github.com/{match.group(1)}'

        # Profile without https
        profile_pattern = r'github\.com/([a-zA-Z0-9_-]+?)(?=[.,;)\s/]|$)'
        match = re.search(profile_pattern, resume_text)
        if match:
            return f'https://github.com/{match.group(1)}'

        return None
    
    def extract_leetcode_from_resume(self, resume_text):
        """Extract LeetCode username from resume text/links"""
        if not resume_text:
            return None
        
        # Match leetcode.com/u/username or leetcode.com/username patterns
        patterns = [
            r'leetcode\.com/u/([a-zA-Z0-9_-]+)',
            r'leetcode\.com/([a-zA-Z0-9_-]+)(?:/|$|\s)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, resume_text, re.IGNORECASE)
            if match:
                username = match.group(1)
                # Filter out common non-username paths
                if username.lower() not in ['problems', 'contest', 'discuss', 'explore', 'submissions']:
                    return username
        
        return None
    
    def extract_codeforces_from_resume(self, resume_text):
        """Extract Codeforces username from resume text/links"""
        if not resume_text:
            return None
        
        # Match codeforces.com/profile/username pattern
        patterns = [
            r'codeforces\.com/profile/([a-zA-Z0-9_-]+)',
            r'codeforces\.com/([a-zA-Z0-9_-]+)(?:/|$|\s)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, resume_text, re.IGNORECASE)
            if match:
                username = match.group(1)
                # Filter out common non-username paths
                if username.lower() not in ['contests', 'problemset', 'ratings', 'blog', 'api']:
                    return username
        
        return None
    
    def run_integrity_agent(self, resume_text, github_analysis, client, use_ai):
        """Run resume integrity and cheater detection analysis"""
        try:
            from integrity import scan_resume_integrity
            
            result = scan_resume_integrity(
                resume_text=resume_text,
                github_analysis=github_analysis
            )
            return result
            
        except Exception as e:
            print(f"Integrity agent failed: {e}")
            # Fallback — use 5.0 (neutral) not 7.0 so a crash doesn't hand
            # free integrity credit to a potentially fraudulent resume.
            # cheater_severity must be present; synthesize_results() reads it.
            return {
                'agent': 'integrity',
                'score': 5.0,
                'verdict': 'UNKNOWN',
                'reasoning': f'Integrity agent error — neutral score applied: {e}',
                'flags': [],
                'cheater_severity': 'unknown',
                'backend_used': 'fallback'
            }
    
    def run_code_quality_agent(self, github_url, github_analysis, client, use_ai):
        """Run code quality analysis using actual GitHub code"""
        try:
            from code_quality import scan_code_quality
            
            if github_analysis:
                return scan_code_quality(github_analysis=github_analysis)
            elif github_url:
                return scan_code_quality(github_url=github_url)
            else:
                return {'agent': 'code_quality', 'score': 0, 'error': 'No GitHub URL provided', 'backend': 'none'}
        except Exception as e:
            print(f"Code quality agent failed: {e}")
            return {'agent': 'code_quality', 'score': 50, 'verdict': 'Unknown', 'flags': [], 'backend': 'fallback', 'error': str(e)}
    
    def run_uniqueness_agent(self, github_url, github_analysis, client, use_ai):
        """Run project uniqueness analysis using actual GitHub data"""
        try:
            from uniqueness import analyze_project_uniqueness
            
            if github_analysis:
                return analyze_project_uniqueness(github_analysis=github_analysis)
            elif github_url:
                return analyze_project_uniqueness(github_url=github_url)
            else:
                return {'agent': 'uniqueness', 'score': 0, 'reasoning': 'No GitHub URL provided', 'backend': 'none'}
        except Exception as e:
            print(f"Uniqueness agent failed: {e}")
            return {'agent': 'uniqueness', 'score': 5.0, 'reasoning': f'Analysis failed: {e}', 'backend': 'fallback'}
    
    def run_relevance_agent(self, resume_text, job_description, client, use_ai):
        """Run job relevance analysis.

        Previously this either called Ollama or returned a hardcoded 7.0,
        completely ignoring the purpose-built agents/relevance.py module.
        Now the dedicated heuristic agent always runs first (keyword match,
        experience years, education, seniority detection). If Ollama is
        available AND a job description was provided, the AI result is used
        to refine the score; otherwise the heuristic result stands.

        This also means candidates without a job description no longer
        receive a free 7.0 — they get a neutral 5.0 from the heuristic
        agent when there are no keywords to match against.
        """
        try:
            from relevance import evaluate_job_relevance
            result = evaluate_job_relevance(resume_text, job_description or "")
            # If Ollama is available, try to refine with AI
            if use_ai and client and job_description:
                prompt = f"""Does this candidate match the job?
Job: {job_description[:400]}
Resume: {resume_text[:400]}
Respond with ONLY valid JSON: {{"score": 7.0, "reasoning": "match explanation"}}"""
                try:
                    response = client.chat(prompt, max_tokens=200)
                    text = response.get('response', '{}')
                    json_match = re.search(r'\{[^}]+\}', text)
                    if json_match:
                        ai_result = json.loads(json_match.group())
                        # Blend: 60% heuristic, 40% AI to stay grounded
                        blended = round(
                            result['score'] * 0.6 + float(ai_result.get('score', result['score'])) * 0.4, 1
                        )
                        result['score'] = blended
                        result['reasoning'] = ai_result.get('reasoning', result['reasoning'])
                        result['backend_used'] = 'heuristics+ollama'
                except Exception as e:
                    print(f"Relevance AI refinement failed (using heuristic): {e}")
            return result
        except Exception as e:
            print(f"Relevance agent failed: {e}")
            return {'agent': 'relevance', 'score': 5.0, 'reasoning': 'Analysis failed — neutral score applied', 'backend_used': 'fallback'}
    
    def run_cp_agent(self, leetcode, codeforces, resume_text, client, use_ai):
        """Run Problem Solving analysis (LeetCode, Codeforces)"""
        try:
            from problem_solving import evaluate_cp_profile
            return evaluate_cp_profile(leetcode, codeforces, resume_text)
        except Exception as e:
            print(f"Problem Solving Agent failed: {e}")
            import traceback
            traceback.print_exc()
            return {'agent': 'problem_solving', 'score': 0, 'error': str(e)}

    def synthesize_results(self, agents, job_description=""):
        """Synthesize all agent results into final evaluation with dynamic weights"""
        
        # Get scores from agents
        integrity_score = float(agents.get('integrity', {}).get('score', 5))
        quality_score = float(agents.get('code_quality', {}).get('score', 50))
        # Normalize code_quality from 0-100 to 0-10.
        # NOTE: apply_weights() in weight_calculator.py also contains this
        # normalization, but that function is NOT called from here — weights
        # are fetched via calculate_weights() and applied inline below.
        # Do NOT add a second division here; that would produce 0.75 from 7.5.
        if quality_score > 10:
            quality_score = quality_score / 10
        uniqueness_score = float(agents.get('uniqueness', {}).get('score', 5))
        relevance_score = float(agents.get('relevance', {}).get('score', 5))
        cp_score = float(agents.get('cp', {}).get('score', 0))
        
        # Calculate dynamic weights based on job description
        weight_info = {"weights": {"integrity": 0.15, "code_quality": 0.30, "uniqueness": 0.20, "relevance": 0.25, "cp": 0.10}, "job_type": "general"}
        try:
            from weight_calculator import calculate_weights
            weight_info = calculate_weights(job_description)
            print(f"Using weights for {weight_info['job_type']}: {weight_info['weights']}")
        except Exception as e:
            print(f"Weight calculator failed, using defaults: {e}")
        
        weights = weight_info["weights"]
        
        # Calculate weighted score
        overall_score = (
            integrity_score * weights.get('integrity', 0.15) +
            quality_score * weights.get('code_quality', 0.30) +
            uniqueness_score * weights.get('uniqueness', 0.20) +
            relevance_score * weights.get('relevance', 0.25) +
            cp_score * weights.get('cp', 0.10)
        )
        
        # Check for cheater severity - auto-reject if critical.
        # 'unknown' means the integrity agent errored — treat as 'none' to
        # avoid penalising candidates for a server-side failure.
        cheater_severity = agents.get('integrity', {}).get('cheater_severity', 'none') or 'none'
        if cheater_severity == 'critical':
            overall_score = max(0, overall_score - 5)
            recommendation = 'REJECT'
            reasoning = f'FLAGGED: Critical integrity issues detected. Score: {overall_score:.1f}/10'
        elif cheater_severity == 'high':
            overall_score = max(0, overall_score - 2)
            if overall_score >= 5.0:
                recommendation = 'WAITLIST'
                reasoning = f'Manual review required: Integrity concerns. Score: {overall_score:.1f}/10'
            else:
                recommendation = 'REJECT'
                reasoning = f'Does not meet standards with integrity issues. Score: {overall_score:.1f}/10'
        elif overall_score >= 7.0 and integrity_score >= 6.0:
            recommendation = 'PASS'
            reasoning = f'Strong candidate with overall score of {overall_score:.1f}/10'
        elif overall_score >= 5.0 and integrity_score >= 4.0:
            recommendation = 'WAITLIST'
            reasoning = f'Potential candidate with overall score of {overall_score:.1f}/10'
        else:
            recommendation = 'REJECT'
            reasoning = f'Does not meet standards with overall score of {overall_score:.1f}/10'
        
        return {
            'overall_score': round(overall_score, 1),
            'recommendation': recommendation,
            'reasoning': reasoning,
            'score_breakdown': {
                'integrity': round(integrity_score, 1),
                'code_quality': round(quality_score, 1),
                'uniqueness': round(uniqueness_score, 1),
                'relevance': round(relevance_score, 1),
                'cp': round(cp_score, 1)
            },
            'weights_used': weights,
            'job_type_detected': weight_info.get('job_type', 'general'),
            'cheater_severity': cheater_severity
        }
    
    def check_system_status(self):
        """Check if Ollama is running"""
        status = {'backend': True, 'ollama': False, 'models': [], 'ready': True}
        
        try:
            req = urllib.request.Request('http://localhost:11434/api/tags')
            with urllib.request.urlopen(req, timeout=2) as response:
                if response.status == 200:
                    data = json.loads(response.read())
                    status['ollama'] = True
                    status['models'] = [m['name'] for m in data.get('models', [])]
        except:
            pass
        
        return status
    
    def log_message(self, format, *args):
        """Custom logging"""
        print(f"[API] {args[0]}" if args else "")

class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    """Multi-threaded HTTP server so batch-progress polling works during batch runs."""
    daemon_threads = True


def _cleanup_uploads():
    """Remove temporary upload files on clean shutdown."""
    upload_dir = BASE_DIR / "data" / "uploads"
    if upload_dir.exists():
        for f in upload_dir.glob("resume_*.pdf"):
            try:
                f.unlink()
            except OSError:
                pass
        batch_dir = upload_dir / "batch"
        if batch_dir.exists():
            try:
                shutil.rmtree(batch_dir)
            except OSError:
                pass
    print("[Cleanup] Temporary upload files removed.")


def run_server(port=3001):
    """Start the API server"""
    atexit.register(_cleanup_uploads)
    server = ThreadedHTTPServer(('0.0.0.0', port), GitVerifiedHandler)
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║           GitVerified Local API Server                       ║
╠══════════════════════════════════════════════════════════════╣
║  Server running on: http://localhost:{port}                    ║
║  Frontend:          http://localhost:3000                    ║
║  Ollama:            http://localhost:11434                   ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")

if __name__ == '__main__':
    run_server()