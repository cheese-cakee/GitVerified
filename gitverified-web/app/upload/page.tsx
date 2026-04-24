"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

type BatchResult = {
    leaderboard: Array<{ name: string; score: number; recommendation: string }>;
    eliminated: Array<{ name: string; reason: string }>;
    flagged: Array<{ name: string; flags: string[] }>;
};

export default function UploadPage() {
    const router = useRouter();
    const [isDragging, setIsDragging] = useState(false);
    const [files, setFiles] = useState<File[]>([]);
    const [uploading, setUploading] = useState(false);
    const [jobDescription, setJobDescription] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [result, setResult] = useState<BatchResult | null>(null);

    const onDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(true);
    }, []);

    const onDragLeave = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
    }, []);

    const onDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            // Filter to PDFs only — non-PDFs previously passed through and
            // caused confusing backend errors instead of a clear "wrong type" message.
            const newFiles = Array.from(e.dataTransfer.files).filter(
                f => f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf")
            );
            if (newFiles.length < e.dataTransfer.files.length) {
                setError(`${e.dataTransfer.files.length - newFiles.length} non-PDF file(s) were skipped.`);
            } else {
                setError(null);
            }
            setFiles(prev => [...prev, ...newFiles]);
        }
    }, []);

    const handleUpload = async () => {
        // Previously this was a fake setTimeout + alert() with no API call.
        // Now it POSTs to /api/evaluate/batch and displays real results.
        if (files.length === 0) return;
        setUploading(true);
        setError(null);
        setResult(null);

        try {
            const formData = new FormData();
            formData.append("job_description", jobDescription);
            files.forEach((file, idx) => {
                formData.append(`resume_${idx}`, file);
            });

            const res = await fetch("/api/evaluate/batch", {
                method: "POST",
                body: formData,
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.error || `Server error ${res.status}`);
            }

            const data = await res.json();
            setResult(data.results);
            setFiles([]);
        } catch (e) {
            setError(e instanceof Error ? e.message : "Batch processing failed. Is python api_server.py running?");
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="min-h-screen bg-black text-white p-8 font-sans selection:bg-white/20">
            {/* Header */}
            <header className="flex justify-between items-center mb-12 max-w-4xl mx-auto">
                <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
                    <span className="text-gray-400">&larr; Back</span>
                </Link>
                <h1 className="text-xl font-semibold tracking-tight">Upload Batch</h1>
                <div className="w-10"></div> {/* Spacer */}
            </header>

            <main className="max-w-4xl mx-auto">
                <div className="text-center mb-10">
                    <h2 className="text-4xl font-bold glow-text mb-4">Ingest Resumes</h2>
                    <p className="text-gray-400">Drag & drop candidate PDFs here for batch evaluation.</p>
                </div>

                {/* Job Description */}
                <div className="mb-6">
                    <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                        Job Description (optional — improves relevance scoring)
                    </label>
                    <textarea
                        value={jobDescription}
                        onChange={e => setJobDescription(e.target.value)}
                        placeholder="Paste the job description here…"
                        rows={3}
                        className="w-full bg-white/5 border border-white/10 rounded-lg p-3 text-sm text-white placeholder-gray-600 resize-none focus:outline-none focus:border-white/30"
                    />
                </div>

                <div
                    className={`
                        relative border-2 border-dashed rounded-2xl p-12 transition-all duration-200 ease-in-out flex flex-col items-center justify-center min-h-[300px]
                        ${isDragging ? "border-white bg-white/5 scale-[1.02]" : "border-white/20 hover:border-white/40 bg-transparent"}
                    `}
                    onDragOver={onDragOver}
                    onDragLeave={onDragLeave}
                    onDrop={onDrop}
                >
                    <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mb-6">
                        <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path></svg>
                    </div>

                    <p className="text-lg font-medium text-white mb-2">Drag and drop PDFs here</p>
                    <p className="text-sm text-gray-500 mb-6">or click to browse — PDF files only</p>

                    <input
                        type="file"
                        multiple
                        accept=".pdf"
                        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                        onChange={(e) => {
                            if (e.target.files) {
                                setFiles(prev => [...prev, ...Array.from(e.target.files!)]);
                            }
                        }}
                    />
                </div>

                {/* Error */}
                {error && (
                    <div className="mt-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-sm text-red-400">
                        {error}
                    </div>
                )}

                {/* File List */}
                {files.length > 0 && (
                    <div className="mt-8">
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Queue ({files.length})</h3>
                            <button
                                onClick={handleUpload}
                                disabled={uploading}
                                className={`px-6 py-2 bg-white text-black font-semibold rounded-full hover:bg-gray-200 transition-all ${uploading ? "opacity-50 cursor-not-allowed" : ""}`}
                            >
                                {uploading ? "Processing…" : `Analyze ${files.length} Resume${files.length > 1 ? "s" : ""}`}
                            </button>
                        </div>
                        <div className="space-y-2">
                            {files.map((f, i) => (
                                <div key={i} className="flex justify-between items-center p-3 bg-white/5 rounded-lg border border-white/5">
                                    <div className="flex items-center gap-3">
                                        <div className="w-8 h-8 rounded bg-red-500/20 text-red-400 flex items-center justify-center text-xs font-bold">PDF</div>
                                        <span className="text-sm text-gray-200">{f.name}</span>
                                    </div>
                                    <span className="text-xs text-gray-500">{(f.size / 1024).toFixed(1)} KB</span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Results */}
                {result && (
                    <div className="mt-10 space-y-6">
                        <h3 className="text-xl font-bold text-white">Batch Results</h3>

                        {/* Leaderboard */}
                        <div>
                            <h4 className="text-sm font-semibold text-green-400 mb-2">🏆 Leaderboard ({result.leaderboard.length})</h4>
                            {result.leaderboard.length > 0 ? (
                                <div className="border border-green-500/20 rounded-lg overflow-hidden">
                                    <table className="w-full text-xs">
                                        <thead className="bg-green-500/10 text-green-400">
                                            <tr>
                                                <th className="p-2 text-left">#</th>
                                                <th className="p-2 text-left">Name</th>
                                                <th className="p-2 text-left">Score</th>
                                                <th className="p-2 text-left">Status</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {result.leaderboard.map((c, i) => (
                                                <tr key={i} className="border-t border-green-500/10">
                                                    <td className="p-2 text-gray-400">{i + 1}</td>
                                                    <td className="p-2 text-white">{c.name}</td>
                                                    <td className="p-2 text-green-400 font-mono">{c.score?.toFixed(1)}/10</td>
                                                    <td className="p-2 text-gray-300">{c.recommendation}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            ) : <p className="text-gray-500 text-xs">No candidates qualified.</p>}
                        </div>

                        {/* Eliminated */}
                        {result.eliminated.length > 0 && (
                            <div>
                                <h4 className="text-sm font-semibold text-gray-400 mb-2">🚫 Eliminated ({result.eliminated.length})</h4>
                                <div className="border border-gray-500/20 rounded-lg overflow-hidden">
                                    <table className="w-full text-xs">
                                        <tbody>
                                            {result.eliminated.map((c, i) => (
                                                <tr key={i} className="border-b border-gray-500/10">
                                                    <td className="p-2 text-gray-300">{c.name}</td>
                                                    <td className="p-2 text-gray-500">{c.reason}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}

                        {/* Flagged */}
                        {result.flagged.length > 0 && (
                            <div>
                                <h4 className="text-sm font-semibold text-red-400 mb-2">⚠️ Flagged ({result.flagged.length})</h4>
                                <div className="border border-red-500/20 rounded-lg overflow-hidden">
                                    <table className="w-full text-xs">
                                        <tbody>
                                            {result.flagged.map((c, i) => (
                                                <tr key={i} className="border-b border-red-500/10">
                                                    <td className="p-2 text-gray-300">{c.name}</td>
                                                    <td className="p-2 text-red-400">{c.flags?.join(", ")}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </main>
        </div>
    );
}
