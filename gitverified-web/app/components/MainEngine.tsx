"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import CheckItem from "./CheckItem";
import Leaderboard from "./Leaderboard";

type Step = {
  id: string;
  label: string;
  status: 'pending' | 'running' | 'pass' | 'failed';
  logs: string[];
};

type SystemStatus = {
  backend: boolean;
  ollama: boolean;
  models: string[];
  ready: boolean;
};

type EvaluationResult = {
  final: {
    overall_score: number;
    recommendation: 'PASS' | 'WAITLIST' | 'REJECT';
    reasoning: string;
    score_breakdown: {
      integrity: number;
      code_quality: number;
      uniqueness: number;
      relevance: number;
      cp: number;
    };
  };
  agents: Record<string, { score: number; reasoning?: string; verdict?: string }>;
};

export default function MainEngine() {
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [mode, setMode] = useState<'single' | 'batch'>('single');
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [jobDescription, setJobDescription] = useState("");
  const [githubUrl, setGithubUrl] = useState("");
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [evaluationResult, setEvaluationResult] = useState<EvaluationResult | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [steps, setSteps] = useState<Step[]>([
    { id: 'integrity', label: 'Resume Integrity Scan', status: 'pending', logs: [] },
    { id: 'code_quality', label: 'Code Quality Analysis', status: 'pending', logs: [] },
    { id: 'uniqueness', label: 'Project Uniqueness Judge', status: 'pending', logs: [] },
    { id: 'relevance', label: 'Job Relevance Matching', status: 'pending', logs: [] },
    { id: 'synthesis', label: 'AI Synthesis (Ollama)', status: 'pending', logs: [] },
  ]);

  const [consoleOutput, setConsoleOutput] = useState<string[]>([]);
  const [batchProgress, setBatchProgress] = useState(0);
  const [batchTotal, setBatchTotal] = useState(0);
  const [batchResults, setBatchResults] = useState<{
    leaderboard: Array<{name: string; score: number; recommendation: string; github_url?: string; details?: Record<string, unknown>}>;
    eliminated: Array<{name: string; reason: string; category?: string}>;
    flagged: Array<{name: string; flags: string[]; score?: number}>;
  } | null>(null);
  const [selectedCandidate, setSelectedCandidate] = useState<Record<string, unknown> | null>(null);

  // Check system status on mount
  useEffect(() => {
    checkSystemStatus();
  }, []);

  const checkSystemStatus = async () => {
    try {
      const res = await fetch('/api/status');
      const status = await res.json();
      setSystemStatus(status);
    } catch {
      setSystemStatus({ backend: false, ollama: false, models: [], ready: false });
    }
  };

  // Auto-scroll logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [consoleOutput]);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      resetState(Array.from(files));
    }
  };

  const resetState = useCallback((files: File[]) => {
    // Central reset — used by both handleFileUpload and handleDrop so every
    // field is consistently cleared.  Previously handleDrop omitted
    // isEvaluating, leaving the button disabled and the "Analyzing..." label
    // stuck if files were dropped mid-evaluation.
    const validFiles = files.filter(f => f.type === 'application/pdf' || f.name.toLowerCase().endsWith('.pdf'));
    if (validFiles.length === 0) return;
    setUploadedFiles(validFiles);
    setMode(validFiles.length > 1 ? 'batch' : 'single');
    setConsoleOutput([]);
    setIsComplete(false);
    setIsEvaluating(false);   // was missing from handleDrop
    setEvaluationResult(null);
    setBatchProgress(0);      // reset stale batch progress from previous run
    setBatchTotal(0);
    setBatchResults(null);
    setSteps(s => s.map(step => ({ ...step, status: 'pending' })));
    if (validFiles.length < files.length) {
      console.warn(`Dropped ${files.length - validFiles.length} non-PDF file(s) — ignored.`);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      resetState(Array.from(files));
    }
  }, [resetState]);

  const runAnalysis = async () => {
    if (uploadedFiles.length === 0) return;

    setIsEvaluating(true);
    setIsComplete(false);
    setEvaluationResult(null);
    setConsoleOutput([`> Initializing GitVerified Engine (LOCAL MODE)...`]);
    setConsoleOutput(prev => [...prev, `> Using Ollama for AI analysis...`]);

    if (mode === 'single') {
      await runSingleAnalysis();
    } else {
      await runBatchAnalysis();
    }
  };

  const runSingleAnalysis = async () => {
    // Previously, the first 4 steps (integrity, code_quality, uniqueness,
    // relevance) were faked — each step was marked "pass" after an 800ms
    // setTimeout with no API call. Only the final "synthesis" step made a
    // real request. This meant the checkmarks had zero informational value
    // and did not reflect actual agent execution.
    //
    // Now: we make ONE real API call to /api/evaluate, then map the agent
    // results from the response back to the step indicators. The step panel
    // shows "running" for all while the request is in flight, then reflects
    // the actual per-agent outcome (pass if score > 0, failed if error).

    // Mark all steps as running while the request is in-flight
    setSteps(prev => prev.map(s => ({ ...s, status: 'running' })));
    setConsoleOutput(prev => [...prev, `> Sending to backend for full evaluation...`]);

    try {
      const formData = new FormData();
      formData.append('resume', uploadedFiles[0]);
      formData.append('job_description', jobDescription);
      formData.append('github_url', githubUrl);

      const response = await fetch('/api/evaluate', {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const result = await response.json();
        setEvaluationResult(result);

        // Map real agent results to step statuses
        const agentStepMap: Record<string, string> = {
          integrity: 'integrity',
          code_quality: 'code_quality',
          uniqueness: 'uniqueness',
          relevance: 'relevance',
        };
        setSteps(prev => prev.map(step => {
          if (step.id === 'synthesis') {
            return { ...step, status: 'pass' };
          }
          const agentKey = agentStepMap[step.id];
          if (agentKey) {
            const agentData = result.agents?.[agentKey];
            const hadError = agentData?.error || agentData?.score === 0;
            return { ...step, status: hadError ? 'failed' : 'pass' };
          }
          return { ...step, status: 'pass' };
        }));

        const breakdown = result.final?.score_breakdown;
        if (breakdown) {
          setConsoleOutput(prev => [
            ...prev,
            `> Integrity:     ${breakdown.integrity}/10`,
            `> Code Quality:  ${breakdown.code_quality}/10`,
            `> Uniqueness:    ${breakdown.uniqueness}/10`,
            `> Relevance:     ${breakdown.relevance}/10`,
            `> Problem Solving: ${breakdown.cp || 0}/10`,
            `> ─────────────────────────────`,
            `> Final Score: ${result.final?.overall_score}/10 → ${result.final?.recommendation}`,
          ]);
        } else {
          setConsoleOutput(prev => [...prev, `> Analysis Complete. Score: ${result.final?.overall_score || 'N/A'}/10`]);
        }
      } else {
        const error = await response.json().catch(() => ({}));
        setSteps(prev => prev.map(s => ({ ...s, status: 'failed' })));
        setConsoleOutput(prev => [...prev, `> ERROR: ${error.message || error.error || 'Backend not available'}`]);
      }
    } catch {
      setSteps(prev => prev.map(s => ({ ...s, status: 'failed' })));
      setConsoleOutput(prev => [...prev, `> ERROR: Cannot reach backend. Is python api_server.py running?`]);
    }

    setIsEvaluating(false);
    setIsComplete(true);
  };

  const runBatchAnalysis = async () => {
    setBatchProgress(0);
    setBatchTotal(uploadedFiles.length);
    setBatchResults(null);
    setConsoleOutput(prev => [...prev, `> Starting batch analysis of ${uploadedFiles.length} resumes...`]);
    
    try {
      // Prepare form data with all resumes
      const formData = new FormData();
      formData.append('job_description', jobDescription);
      
      uploadedFiles.forEach((file, idx) => {
        formData.append(`resume_${idx}`, file);
      });
      
      // Start progress polling
      const pollInterval = setInterval(async () => {
        try {
          const progressRes = await fetch('/api/batch/progress');
          if (progressRes.ok) {
            const progress = await progressRes.json();
            if (progress.is_running) {
              setBatchProgress(progress.current);
              setConsoleOutput(prev => {
                const lastLine = prev[prev.length - 1];
                if (lastLine?.startsWith('> Processing:')) {
                  return [...prev.slice(0, -1), `> Processing: ${progress.current}/${progress.total} (${progress.percentage}%)`];
                }
                return [...prev, `> Processing: ${progress.current}/${progress.total} (${progress.percentage}%)`];
              });
            }
          }
        } catch {
          // Polling error, continue
        }
      }, 1000);
      
      // Call batch evaluation API
      const response = await fetch('/api/evaluate/batch', {
        method: 'POST',
        body: formData,
      });
      
      clearInterval(pollInterval);
      
      if (response.ok) {
        const result = await response.json();
        setBatchResults(result.results);
        setBatchProgress(result.processed);
        
        const { leaderboard, eliminated, flagged } = result.results;
        setConsoleOutput(prev => [
          ...prev,
          `> ✅ Batch Analysis Complete!`,
          `>    Leaderboard: ${leaderboard.length} candidates`,
          `>    Eliminated: ${eliminated.length} candidates`,
          `>    Flagged: ${flagged.length} candidates`,
        ]);
      } else {
        const error = await response.json();
        setConsoleOutput(prev => [...prev, `> ❌ ERROR: ${error.error || 'Batch processing failed'}`]);
      }
    } catch (error) {
      setConsoleOutput(prev => [...prev, `> ❌ ERROR: Make sure backend is running (python api_server.py)`]);
    }
    
    setIsEvaluating(false);
    setIsComplete(true);
  };

  const stopBatchAnalysis = async () => {
    try {
      await fetch('/api/evaluate/stop', { method: 'POST' });
      setConsoleOutput(prev => [...prev, '> ⏹️ Stop requested...']);
    } catch {
      setConsoleOutput(prev => [...prev, '> Failed to send stop request']);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 7) return 'bg-green-500';
    if (score >= 5) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const getRecommendationColor = (rec: string) => {
    if (rec === 'PASS') return 'text-green-400';
    if (rec === 'WAITLIST') return 'text-yellow-400';
    return 'text-red-400';
  };

  const exportToCSV = () => {
    if (!batchResults) return;

    // Generate CSV content
    const lines: string[] = [];
    
    // Header
    lines.push("Category,Rank,Name,Score,Status,GitHub URL,Reason/Flags");
    
    // Leaderboard
    batchResults.leaderboard.forEach((c, i) => {
      lines.push(`Leaderboard,${i + 1},"${c.name}",${c.score?.toFixed(1) || 'N/A'},${c.recommendation || 'N/A'},"${c.github_url || ''}",""`);
    });
    
    // Eliminated
    batchResults.eliminated.forEach((c) => {
      lines.push(`Eliminated,,"${c.name}",,,"","${c.reason || ''}"`);
    });
    
    // Flagged
    batchResults.flagged.forEach((c) => {
      lines.push(`Flagged,,"${c.name}",${c.score?.toFixed(1) || 'N/A'},,"","${c.flags?.join('; ') || ''}"`);
    });
    
    const csvContent = lines.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `candidate_results_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <section className="w-full h-screen bg-black flex flex-col pt-20">
       <div className="flex-1 max-w-[1600px] w-full mx-auto p-6 flex gap-6">
          
          {/* LEFT: Checks Panel */}
          <div className="w-80 flex flex-col gap-4">
             <div className="glass-card rounded-xl p-4 flex-1 flex flex-col border-white/10">
                <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                   <div className={`w-2 h-2 rounded-full ${isEvaluating ? 'bg-yellow-500 animate-pulse' : 'bg-green-500'}`}></div>
                   {mode === 'single' ? 'Execution Plan' : 'Batch Processor'}
                </div>
                
                {mode === 'single' ? (
                    <div className="space-y-1">
                        {steps.map(step => (
                            <CheckItem key={step.id} status={step.status} label={step.label} />
                        ))}
                    </div>
                ) : (
                    <div className="flex flex-col items-center justify-center flex-1 space-y-4">
                         <div className="text-4xl font-bold text-white">{batchProgress}/{batchTotal}</div>
                         <div className="w-full bg-gray-800 h-2 rounded-full overflow-hidden">
                             <div className="bg-blue-500 h-full transition-all duration-300" style={{ width: `${batchTotal > 0 ? (batchProgress / batchTotal) * 100 : 0}%` }}></div>
                         </div>
                         <p className="text-xs text-gray-400 text-center">Processing resumes with Ollama...</p>
                         {isEvaluating && (
                           <button 
                             onClick={stopBatchAnalysis}
                             className="px-4 py-2 bg-red-500/20 border border-red-500/50 text-red-400 rounded hover:bg-red-500/30 text-sm"
                           >
                             ⏹ Stop Evaluation
                           </button>
                         )}
                    </div>
                )}
             </div>
             
             {/* System Status */}
             <div className="glass-card rounded-xl p-4 border-white/10">
                <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">System Status</div>
                {/* Show skeleton indicators while the initial status fetch is in-flight.
                    Previously systemStatus was null until the fetch resolved, rendering
                    nothing — users saw blank status with no indication of loading. */}
                <div className="space-y-2 pt-2">
                   <div className="flex items-center justify-between text-xs">
                      <span className="text-gray-500">Python Backend</span>
                      {systemStatus === null
                        ? <span className="text-gray-500 animate-pulse">○ Checking…</span>
                        : <span className={systemStatus.backend ? 'text-green-400' : 'text-red-400'}>
                            {systemStatus.backend ? '● Online' : '○ Offline'}
                          </span>
                      }
                   </div>
                   <div className="flex items-center justify-between text-xs">
                      <span className="text-gray-500">Ollama AI</span>
                      {systemStatus === null
                        ? <span className="text-gray-500 animate-pulse">○ Checking…</span>
                        : <span className={systemStatus.ollama ? 'text-green-400' : 'text-red-400'}>
                            {systemStatus.ollama ? '● Online' : '○ Offline'}
                          </span>
                      }
                   </div>
                </div>
                <button 
                  onClick={checkSystemStatus}
                  className="mt-3 w-full text-xs py-1 border border-white/10 rounded hover:bg-white/5 text-gray-400"
                >
                  Refresh Status
                </button>
             </div>
          </div>

          {/* CENTRE: Output / Result */}
          <div className="flex-1 glass-card rounded-xl border-white/10 flex flex-col overflow-hidden relative">
              
              {isComplete && mode === 'batch' && batchResults ? (
                  <div className="flex-1 overflow-y-auto p-4 space-y-6">
                    {/* Header with Export */}
                    <div className="flex items-center justify-between pb-4 border-b border-white/10">
                      <div>
                        <h2 className="text-lg font-bold text-white">Batch Results</h2>
                        <p className="text-xs text-gray-400">
                          {batchResults.leaderboard.length} passed • {batchResults.eliminated.length} eliminated • {batchResults.flagged.length} flagged
                        </p>
                      </div>
                      <button
                        onClick={exportToCSV}
                        className="px-4 py-2 bg-green-500/20 border border-green-500/50 text-green-400 rounded hover:bg-green-500/30 text-sm flex items-center gap-2"
                      >
                        📥 Export CSV
                      </button>
                    </div>

                    {/* Leaderboard Table */}
                    <div>
                      <h3 className="text-sm font-semibold text-green-400 mb-2 flex items-center gap-2">
                        🏆 Leaderboard ({batchResults.leaderboard.length})
                      </h3>
                      {batchResults.leaderboard.length > 0 ? (
                        <div className="bg-green-500/5 border border-green-500/20 rounded-lg overflow-hidden">
                          <table className="w-full text-xs">
                            <thead className="bg-green-500/10">
                              <tr className="text-green-400">
                                <th className="p-2 text-left">#</th>
                                <th className="p-2 text-left">Name</th>
                                <th className="p-2 text-left">Score</th>
                                <th className="p-2 text-left">Status</th>
                                <th className="p-2 text-left">Action</th>
                              </tr>
                            </thead>
                            <tbody>
                              {batchResults.leaderboard.map((c, i) => (
                                <tr key={i} className="border-t border-green-500/10 hover:bg-green-500/5 cursor-pointer">
                                  <td className="p-2 text-gray-400">{i + 1}</td>
                                  <td className="p-2 text-white">{c.name}</td>
                                  <td className="p-2 text-green-400 font-mono">{c.score?.toFixed(1)}/10</td>
                                  <td className="p-2">
                                    <span className={`px-2 py-0.5 rounded text-xs ${c.recommendation === 'PASS' ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'}`}>
                                      {c.recommendation}
                                    </span>
                                  </td>
                                  <td className="p-2">
                                    <button 
                                      onClick={() => setSelectedCandidate(c.details || null)}
                                      className="text-blue-400 hover:underline"
                                    >
                                      View Details
                                    </button>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <p className="text-gray-500 text-xs">No candidates qualified for leaderboard</p>
                      )}
                    </div>

                    {/* Eliminated Table */}
                    <div>
                      <h3 className="text-sm font-semibold text-gray-400 mb-2 flex items-center gap-2">
                        🚫 Eliminated ({batchResults.eliminated.length})
                      </h3>
                      {batchResults.eliminated.length > 0 ? (
                        <div className="bg-gray-500/5 border border-gray-500/20 rounded-lg overflow-hidden">
                          <table className="w-full text-xs">
                            <thead className="bg-gray-500/10">
                              <tr className="text-gray-400">
                                <th className="p-2 text-left">Name</th>
                                <th className="p-2 text-left">Reason</th>
                              </tr>
                            </thead>
                            <tbody>
                              {batchResults.eliminated.map((c, i) => (
                                <tr key={i} className="border-t border-gray-500/10">
                                  <td className="p-2 text-gray-300">{c.name}</td>
                                  <td className="p-2 text-gray-500">{c.reason}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <p className="text-gray-500 text-xs">No candidates eliminated</p>
                      )}
                    </div>

                    {/* Flagged/Cheaters Table */}
                    <div>
                      <h3 className="text-sm font-semibold text-red-400 mb-2 flex items-center gap-2">
                        ⚠️ Flagged ({batchResults.flagged.length})
                      </h3>
                      {batchResults.flagged.length > 0 ? (
                        <div className="bg-red-500/5 border border-red-500/20 rounded-lg overflow-hidden">
                          <table className="w-full text-xs">
                            <thead className="bg-red-500/10">
                              <tr className="text-red-400">
                                <th className="p-2 text-left">Name</th>
                                <th className="p-2 text-left">Flags</th>
                              </tr>
                            </thead>
                            <tbody>
                              {batchResults.flagged.map((c, i) => (
                                <tr key={i} className="border-t border-red-500/10">
                                  <td className="p-2 text-gray-300">{c.name}</td>
                                  <td className="p-2 text-red-400">{c.flags?.join(', ') || 'Suspicious activity'}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <p className="text-gray-500 text-xs">No candidates flagged</p>
                      )}
                    </div>
                  </div>
              ) : isComplete && mode === 'batch' ? (
                  <Leaderboard />
              ) : (
                <>
                    {/* Header */}
                    <div className="h-12 border-b border-white/5 flex items-center px-4 bg-white/5 justify-between">
                        <div className="flex items-center gap-2 text-sm text-gray-400">
                            <span className="text-gray-600">~/analysis/</span>
                            <span className="text-white">{mode === 'batch' ? 'batch_report.csv' : 'candidate_report.json'}</span>
                        </div>
                        {isEvaluating && <span className="text-xs text-yellow-500 animate-pulse">● Processing...</span>}
                    </div>

                    {/* Content */}
                    <div className="flex-1 bg-black/40 p-6 font-mono text-sm overflow-y-auto custom-scrollbar">
                        {!isEvaluating && !isComplete && (
                            <div className="h-full flex flex-col items-center justify-center text-gray-600">
                                <p>Ready to analyze. Upload resume to begin.</p>
                                <p className="text-xs mt-2 opacity-50">
                                  {uploadedFiles.length > 0 ? `${uploadedFiles.length} file(s) ready` : 'Waiting for Input'}
                                </p>
                            </div>
                        )}

                        {(isEvaluating || isComplete) && (
                            <div className="space-y-1">
                                {consoleOutput.map((log, i) => (
                                    <div key={i} className={`${log.startsWith('>') ? 'text-gray-400' : 'text-gray-600 pl-4'}`}>
                                        {log}
                                    </div>
                                ))}
                                
                                {/* Result Card */}
                                {isComplete && mode === 'single' && evaluationResult && (
                                    <div className={`mt-8 p-6 rounded-lg border animate-fade-in-up ${
                                      evaluationResult.final.recommendation === 'PASS' ? 'border-green-500/20 bg-green-900/10' :
                                      evaluationResult.final.recommendation === 'WAITLIST' ? 'border-yellow-500/20 bg-yellow-900/10' :
                                      'border-red-500/20 bg-red-900/10'
                                    }`}>
                                        <div className="flex items-center gap-4 mb-4">
                                            <div className={`w-14 h-14 rounded-full ${getScoreColor(evaluationResult.final.overall_score)} text-black flex items-center justify-center font-bold text-lg`}>
                                              {/* Display the actual /10 score, not score*10 which was
                                                  showing 75 in the circle while the label said 7.5/10 */}
                                              {evaluationResult.final.overall_score}
                                            </div>
                                            <div>
                                                <h3 className="text-xl font-bold text-white">
                                                  Score: {evaluationResult.final.overall_score}/10
                                                </h3>
                                                <p className={`text-sm font-semibold ${getRecommendationColor(evaluationResult.final.recommendation)}`}>
                                                  {evaluationResult.final.recommendation}
                                                </p>
                                            </div>
                                        </div>
                                        <p className="text-gray-400 text-sm mb-4">{evaluationResult.final.reasoning}</p>
                                        
                                        {/* Score Breakdown */}
                                        <div className="grid grid-cols-2 gap-3 text-xs">
                                          <div className="flex justify-between">
                                            <span className="text-gray-500">Integrity</span>
                                            <span className="text-white">{evaluationResult.final.score_breakdown.integrity}/10</span>
                                          </div>
                                          <div className="flex justify-between">
                                            <span className="text-gray-500">Code Quality</span>
                                            <span className="text-white">{evaluationResult.final.score_breakdown.code_quality}/10</span>
                                          </div>
                                          <div className="flex justify-between">
                                            <span className="text-gray-500">Uniqueness</span>
                                            <span className="text-white">{evaluationResult.final.score_breakdown.uniqueness}/10</span>
                                          </div>
                                          <div className="flex justify-between">
                                            <span className="text-gray-500">Relevance</span>
                                            <span className="text-white">{evaluationResult.final.score_breakdown.relevance}/10</span>
                                          </div>
                                          <div className="flex justify-between">
                                            <span className="text-gray-500">Problem Solving</span>
                                            <span className="text-white">{evaluationResult.final.score_breakdown.cp || 0}/10</span>
                                          </div>
                                        </div>
                                    </div>
                                )}

                                {/* Error state when no result */}
                                {isComplete && mode === 'single' && !evaluationResult && (
                                    <div className="mt-8 p-6 rounded-lg border border-red-500/20 bg-red-900/10">
                                        <h3 className="text-lg font-bold text-red-400 mb-2">Backend Not Available</h3>
                                        <p className="text-gray-400 text-sm">Make sure to start the Python API server:</p>
                                        <code className="text-xs text-green-400 block mt-2 bg-black/50 p-2 rounded">
                                          python api_server.py
                                        </code>
                                    </div>
                                )}
                                
                                <div ref={logsEndRef}></div>
                            </div>
                        )}
                    </div>
                </>
              )}
          </div>

          {/* RIGHT: Input */}
          <div className="w-80 glass-card rounded-xl p-6 border-white/10 flex flex-col gap-6">
               <div>
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Resume Upload</h3>
                    {mode === 'batch' && (
                      <span className="text-xs px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded">BATCH MODE</span>
                    )}
                  </div>
                  
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileUpload}
                    accept=".pdf"
                    multiple
                    className="hidden"
                  />

                  <div 
                    onClick={() => fileInputRef.current?.click()}
                    onDrop={handleDrop}
                    onDragOver={(e) => e.preventDefault()}
                    className={`border-2 border-dashed border-white/10 rounded-lg h-28 flex flex-col items-center justify-center text-center p-4 transition-all cursor-pointer hover:border-white/30 ${uploadedFiles.length > 0 ? 'bg-white/5 border-green-500/50' : ''}`}
                  >
                      <div className="w-8 h-8 rounded-full bg-white/5 flex items-center justify-center mb-2">
                        <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" /></svg>
                      </div>
                      <span className="text-xs text-gray-400">
                          {uploadedFiles.length === 0 
                            ? 'Drop PDFs or click (select multiple for batch)' 
                            : uploadedFiles.length === 1 
                              ? `1 file: ${uploadedFiles[0]?.name}`
                              : `${uploadedFiles.length} files selected`}
                      </span>
                  </div>
               </div>

               <div>
                  <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Job Description</h3>
                  <textarea
                    value={jobDescription}
                    onChange={(e) => setJobDescription(e.target.value)}
                    placeholder="Paste job description here (optional - used for relevance matching and dynamic weighting)"
                    className="w-full h-24 bg-white/5 border border-white/10 rounded-lg p-3 text-xs text-white placeholder-gray-500 resize-none focus:outline-none focus:border-white/30"
                  />
               </div>

               {/* Info about auto-extraction */}
               <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
                 <p className="text-xs text-blue-400">
                   <span className="font-semibold">GitHub Auto-Detection:</span> GitHub profile/repo URLs will be automatically extracted from the resume PDF and analyzed.
                 </p>
               </div>
               
               <button 
                  onClick={runAnalysis}
                  disabled={isEvaluating || uploadedFiles.length === 0}
                  className="mt-auto w-full py-3 bg-white text-black text-sm font-bold rounded hover:bg-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
               >
                  {isEvaluating ? 'Analyzing...' : mode === 'batch' ? `Analyze ${uploadedFiles.length} Resumes` : 'Run Analysis'}
               </button>
          </div>

       </div>
    </section>
  );
}
