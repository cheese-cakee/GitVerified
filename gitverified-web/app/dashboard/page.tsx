"use client";

/**
 * Dashboard — converted to client component so Export CSV and View Report
 * buttons can have working onClick handlers. Previously both were dead:
 * Export CSV had no handler at all, and View Report rendered an invisible
 * button with no action. Leaderboard data is now fetched client-side.
 */

import { useState, useEffect } from "react";
import Link from "next/link";
import { getLeaderboardData, Candidate } from "../lib/api";

type ModalData = Candidate | null;

export default function Dashboard() {
    const [candidates, setCandidates] = useState<Candidate[]>([]);
    const [loading, setLoading] = useState(true);
    const [modal, setModal] = useState<ModalData>(null);

    useEffect(() => {
        getLeaderboardData()
            .then(setCandidates)
            .finally(() => setLoading(false));
    }, []);

    const exportCSV = () => {
        if (candidates.length === 0) return;
        const header = "Rank,Name,ID,Status,P-Score,Flag,Date";
        const rows = candidates.map((c, i) =>
            `${i + 1},"${c.name}","${c.id}","${c.status}",${c.p_score},"${c.flag}","${c.date || ''}"`
        );
        const csv = [header, ...rows].join("\n");
        const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `leaderboard_${new Date().toISOString().split("T")[0]}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    };

    return (
        <div className="min-h-screen bg-black text-white p-8 font-sans selection:bg-white/20">
            {/* Header */}
            <header className="flex justify-between items-center mb-12 max-w-6xl mx-auto">
                <div className="flex items-center gap-3">
                    <div className="w-6 h-6 bg-white rounded-full"></div>
                    <h1 className="text-xl font-semibold tracking-tight">
                        GitVerified <span className="text-gray-500 font-normal">/ Leaderboard</span>
                    </h1>
                </div>
                <Link href="/" className="text-sm text-gray-400 hover:text-white transition-colors">← Home</Link>
            </header>

            <main className="max-w-6xl mx-auto">
                <div className="flex justify-between items-end mb-6">
                    <div>
                        <h2 className="text-3xl font-bold glow-text mb-2">Leaderboard</h2>
                        <p className="text-gray-400">Top candidates sorted by overall score.</p>
                    </div>
                    <div className="flex gap-4">
                        <button
                            onClick={exportCSV}
                            disabled={candidates.length === 0}
                            className="px-4 py-2 bg-white/5 border border-white/10 rounded-md text-sm text-gray-300 hover:bg-white/10 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                        >
                            Export CSV
                        </button>
                        <Link
                            href="/engine"
                            className="px-4 py-2 bg-white text-black rounded-md text-sm font-semibold hover:bg-gray-200 transition-colors"
                        >
                            New Evaluation
                        </Link>
                    </div>
                </div>

                <div className="border border-white/10 rounded-xl overflow-hidden bg-black/50 backdrop-blur-md">
                    {loading ? (
                        <div className="p-12 text-center text-gray-500 animate-pulse">Loading evaluations…</div>
                    ) : candidates.length === 0 ? (
                        <div className="p-12 text-center text-gray-500">
                            No evaluations found.{" "}
                            <Link href="/engine" className="text-blue-400 hover:underline">Run an evaluation</Link> to see results here.
                        </div>
                    ) : (
                        <table className="w-full text-left border-collapse">
                            <thead>
                                <tr className="border-b border-white/10 bg-white/5 text-xs uppercase tracking-wider text-gray-500">
                                    <th className="px-6 py-4 font-medium">Rank</th>
                                    <th className="px-6 py-4 font-medium">Candidate</th>
                                    <th className="px-6 py-4 font-medium">Status</th>
                                    <th className="px-6 py-4 font-medium">Score</th>
                                    <th className="px-6 py-4 font-medium">Flag</th>
                                    <th className="px-6 py-4 font-medium text-right">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5">
                                {candidates.map((c, i) => (
                                    <tr key={c.id} className="group hover:bg-white/5 transition-colors">
                                        <td className="px-6 py-4 text-gray-500 font-mono text-sm">#{i + 1}</td>
                                        <td className="px-6 py-4">
                                            <div className="font-medium text-white">{c.name}</div>
                                            <div className="text-xs text-gray-500">ID: {c.id}</div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <Badge status={c.status} />
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex items-center gap-2">
                                                <span className={`text-lg font-bold ${getScoreColor(c.p_score)}`}>{c.p_score}</span>
                                                <span className="text-xs text-gray-600">/100</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className="text-sm text-gray-400">{c.flag}</span>
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            {/* Previously this button had no onClick and was invisible until
                                                hover — users could not interact with it at all. */}
                                            <button
                                                onClick={() => setModal(c)}
                                                className="text-sm text-blue-400 hover:text-blue-300 hover:underline transition-colors"
                                            >
                                                View Report →
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            </main>

            {/* Report Modal */}
            {modal && (
                <div
                    className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4"
                    onClick={() => setModal(null)}
                >
                    <div
                        className="bg-gray-900 border border-white/10 rounded-xl p-6 max-w-md w-full space-y-4"
                        onClick={e => e.stopPropagation()}
                    >
                        <div className="flex justify-between items-start">
                            <div>
                                <h3 className="text-lg font-bold text-white">{modal.name}</h3>
                                <p className="text-xs text-gray-500">ID: {modal.id} {modal.date ? `· ${modal.date}` : ''}</p>
                            </div>
                            <button onClick={() => setModal(null)} className="text-gray-500 hover:text-white text-xl leading-none">×</button>
                        </div>
                        <div className="grid grid-cols-2 gap-3 text-sm">
                            <ScoreRow label="Overall" value={modal.p_score} max={100} />
                            <ScoreRow label="Integrity" value={modal.truth} max={100} />
                            <ScoreRow label="Relevance" value={modal.passion} max={100} />
                            <ScoreRow label="Code Quality" value={modal.code} max={100} />
                        </div>
                        <div className="pt-2 border-t border-white/10">
                            <Badge status={modal.status} />
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

function ScoreRow({ label, value, max }: { label: string; value: number; max: number }) {
    const pct = Math.round((value / max) * 100);
    return (
        <div>
            <div className="flex justify-between text-xs text-gray-400 mb-1">
                <span>{label}</span>
                <span>{value}/{max}</span>
            </div>
            <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
                <div
                    className={`h-full rounded-full ${pct >= 70 ? 'bg-green-500' : pct >= 40 ? 'bg-yellow-500' : 'bg-red-500'}`}
                    style={{ width: `${pct}%` }}
                />
            </div>
        </div>
    );
}

function Badge({ status }: { status: string }) {
    const s = status.toUpperCase();
    let colorClass = "bg-gray-500/10 text-gray-500 border-gray-500/20";
    let pulse = false;

    if (s === "PASS" || s === "INTERVIEW") {
        colorClass = "bg-green-500/10 text-green-500 border-green-500/20";
        pulse = true;
    } else if (s === "WAITLIST") {
        colorClass = "bg-yellow-500/10 text-yellow-500 border-yellow-500/20";
    } else if (s === "REJECT") {
        colorClass = "bg-red-500/10 text-red-500 border-red-500/20";
    }

    return (
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${colorClass}`}>
            {pulse && <span className="w-1.5 h-1.5 rounded-full bg-green-500 mr-1.5 animate-pulse"></span>}
            {status}
        </span>
    );
}

function getScoreColor(score: number) {
    if (score >= 90) return "text-green-400 drop-shadow-[0_0_8px_rgba(74,222,128,0.5)]";
    if (score >= 70) return "text-yellow-400";
    return "text-red-500";
}
