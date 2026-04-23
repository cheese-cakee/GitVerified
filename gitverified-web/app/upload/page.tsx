"use client";

import { useState, useCallback } from "react";
import Link from "next/link";

export default function UploadPage() {
    const [isDragging, setIsDragging] = useState(false);
    const [files, setFiles] = useState<File[]>([]);
    const [uploading, setUploading] = useState(false);

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
            const newFiles = Array.from(e.dataTransfer.files).filter(f => f.type === "application/pdf");
            setFiles(prev => [...prev, ...newFiles]);
        }
    }, []);

    const handleUpload = () => {
        setUploading(true);
        // Simulate upload delay
        setTimeout(() => {
            setUploading(false);
            alert(`Successfully uploaded ${files.length} resumes to batch processing`);
            setFiles([]);
        }, 2000);
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
                    <p className="text-gray-400">Drag & drop candidate PDFs here. We process up to 100 files in parallel.</p>
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
                    <p className="text-sm text-gray-500 mb-6">or click to browse filesystem</p>

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
                                {uploading ? "Processing..." : "Start Batch Analysis"}
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
            </main>
        </div>
    );
}
