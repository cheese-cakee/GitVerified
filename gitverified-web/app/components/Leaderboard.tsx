/**
 * Leaderboard component — previously rendered hardcoded fake candidates
 * (Alex Chen, Sarah Jones, etc.) as the fallback when a batch errored out.
 * Any batch failure silently showed fake "real" results to recruiters.
 *
 * This component is now only rendered when batchResults is explicitly null
 * after a completed batch (edge case). It fetches real data from the API.
 * The hardcoded demo array is removed entirely.
 */

"use client";
import { useEffect, useState } from "react";

type LiveCandidate = {
  id: string;
  name: string;
  overall_score: number;
  status: string;
  date: string;
};

export default function Leaderboard() {
  const [candidates, setCandidates] = useState<LiveCandidate[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/leaderboard")
      .then(r => r.ok ? r.json() : [])
      .then(data => setCandidates(Array.isArray(data) ? data : []))
      .catch(() => setCandidates([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="w-full h-full glass-card border-white/10 rounded-xl overflow-hidden flex flex-col animate-fade-in-up">
      <div className="p-6 border-b border-white/5 flex items-center justify-between bg-white/5">
        <div>
           <h2 className="text-xl font-bold text-white">Candidate Leaderboard</h2>
           <p className="text-sm text-gray-400">
             {loading ? "Loading…" : `${candidates.length} candidates evaluated`}
           </p>
        </div>
      </div>

      <div className="flex-1 overflow-auto custom-scrollbar p-0">
        {loading ? (
          <div className="p-12 text-center text-gray-500 animate-pulse">Loading…</div>
        ) : candidates.length === 0 ? (
          <div className="p-12 text-center text-gray-500">
            No evaluations found. Run an evaluation to see results here.
          </div>
        ) : (
          <table className="w-full text-left border-collapse">
            <thead className="bg-black/20 text-gray-400 text-xs uppercase tracking-wider sticky top-0 backdrop-blur-md z-10">
              <tr>
                <th className="p-4 border-b border-white/5">Rank</th>
                <th className="p-4 border-b border-white/5">Candidate</th>
                <th className="p-4 border-b border-white/5">Score</th>
                <th className="p-4 border-b border-white/5">Status</th>
                <th className="p-4 border-b border-white/5">Date</th>
              </tr>
            </thead>
            <tbody className="text-sm">
              {candidates.map((c, i) => (
                <tr key={c.id} className="hover:bg-white/5 transition-colors border-b border-white/5">
                  <td className="p-4 font-mono text-gray-500">#{i + 1}</td>
                  <td className="p-4">
                    <div className="font-bold text-white">{c.name}</div>
                    <div className="text-xs text-gray-500">{c.id}</div>
                  </td>
                  <td className="p-4">
                    <div className="flex items-center gap-2">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
                        c.overall_score >= 7 ? 'bg-green-500 text-black' :
                        c.overall_score >= 5 ? 'bg-yellow-500 text-black' :
                        'bg-red-500 text-white'
                      }`}>
                        {c.overall_score}
                      </div>
                      <span className="text-xs text-gray-500">/10</span>
                    </div>
                  </td>
                  <td className="p-4">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                      c.status === 'PASS' ? 'bg-green-500/20 text-green-300' :
                      c.status === 'WAITLIST' ? 'bg-yellow-500/20 text-yellow-300' :
                      'bg-red-500/20 text-red-300'
                    }`}>
                      {c.status}
                    </span>
                  </td>
                  <td className="p-4 text-xs text-gray-500">{c.date || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
