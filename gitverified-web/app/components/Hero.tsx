"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

export default function Hero() {
  const [activeTab, setActiveTab] = useState(0);
  
  // Simulation of dynamic content popping in
  useEffect(() => {
    const interval = setInterval(() => {
      setActiveTab((prev) => (prev + 1) % 3);
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="relative w-full flex flex-col items-center justify-center pt-32 pb-16 px-4 min-h-[90vh]">
      {/* Dynamic Background Elements */}
      <div className="absolute inset-0 bg-grid z-0 pointer-events-none opacity-30"></div>
      <div className="absolute top-20 left-1/2 -translate-x-1/2 w-[800px] h-[600px] bg-gradient-to-b from-purple-500/10 via-blue-500/5 to-transparent blur-[120px] rounded-full z-0 pointer-events-none"></div>

      <div className="z-10 text-center max-w-5xl mx-auto space-y-12 w-full">
        
        {/* Main Title Area */}
        <div className="space-y-6">
           <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-white/10 bg-white/5 text-xs font-medium text-gray-300 animate-fade-in-up">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>
            System Online: Verification Engine Active
          </div>

          <h1 className="text-4xl md:text-6xl font-serif font-thin text-white tracking-tight leading-tight">
            <span className="glow-text">Verification System</span>
            <br />
            <span className="text-gray-400">for Recruiters</span>
          </h1>

          <p className="text-xl text-gray-400 max-w-2xl mx-auto font-light leading-relaxed font-sans">
            The agentic standard for candidate assessment.
          </p>
          
          <div className="flex flex-col items-center gap-6">
             {/* Powered By */}
             <div className="flex items-center justify-center gap-2 text-sm text-gray-500">
               <span>Powered by</span>
               <Link href="https://ollama.ai" target="_blank" className="flex items-center gap-2 px-3 py-1 bg-white/5 rounded-lg border border-white/5 text-white/90 font-medium hover:bg-white/10 transition-colors">
                  🦙 Ollama
               </Link>
             </div>

             {/* GitHub Button */}
             <Link href="https://github.com/cheese-cakee/GitVerified" target="_blank" className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors border-b border-white/20 hover:border-white pb-0.5">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/></svg>
                <span>View Source on GitHub</span>
             </Link>
          </div>
        </div>

        {/* Dynamic Abstract Visual / Code Snippet */}
        <div className="relative w-full max-w-2xl mx-auto h-[120px] md:h-[160px] perspective-1000">
           <div className={`absolute inset-0 transition-all duration-700 ease-in-out transform ${activeTab === 0 ? 'opacity-100 translate-y-0 scale-100' : 'opacity-0 translate-y-10 scale-95'}`}>
              <div className="glass-card p-6 rounded-xl border border-blue-500/30 shadow-[0_0_50px_rgba(59,130,246,0.1)] flex items-center justify-between">
                 <div className="text-left space-y-2">
                    <div className="h-2 w-24 bg-blue-500/50 rounded animate-pulse"></div>
                    <div className="h-2 w-48 bg-gray-700 rounded"></div>
                    <div className="h-2 w-36 bg-gray-700 rounded"></div>
                 </div>
                 <div className="h-12 w-12 rounded-full bg-blue-500/10 flex items-center justify-center text-blue-400 border border-blue-500/20">
                    ID
                 </div>
              </div>
           </div>

           <div className={`absolute inset-0 transition-all duration-700 ease-in-out transform ${activeTab === 1 ? 'opacity-100 translate-y-0 scale-100' : 'opacity-0 translate-y-10 scale-95'}`}>
             <div className="glass-card p-6 rounded-xl border border-purple-500/30 shadow-[0_0_50px_rgba(168,85,247,0.1)] flex flex-col gap-3">
                 <div className="flex gap-2 font-mono text-xs text-purple-300">
                    <span className="text-purple-500">{">"}</span> analyzing_repo...
                 </div>
                 <div className="w-full bg-gray-800/50 h-1.5 rounded-full overflow-hidden">
                    <div className="bg-purple-500 h-full w-2/3 animate-[shimmer_2s_infinite]"></div>
                 </div>
              </div>
           </div>

            <div className={`absolute inset-0 transition-all duration-700 ease-in-out transform ${activeTab === 2 ? 'opacity-100 translate-y-0 scale-100' : 'opacity-0 translate-y-10 scale-95'}`}>
              <div className="glass-card p-4 rounded-xl border border-green-500/30 shadow-[0_0_50px_rgba(34,197,94,0.1)]">
                 <div className="flex items-center gap-3">
                    <div className="h-3 w-3 rounded-full bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.8)]"></div>
                    <span className="font-mono text-sm text-green-400">Candidate Verified</span>
                 </div>
              </div>
           </div>
        </div>
      </div>
    </div>
  );
}
