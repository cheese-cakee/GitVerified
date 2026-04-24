export interface Candidate {
    id: string;
    name: string;
    p_score: number;
    truth: number;
    passion: number;
    code: number;
    status: string;
    flag: string;
    date?: string;
}

export interface EvaluationResult {
    status?: string;
    candidate: {
        resume_path: string;
        job_description: string;
        github_url?: string;
    };
    agents: {
        integrity?: { score: number; reasoning?: string; flags?: string[] };
        code_quality?: { score: number; verdict?: string; flags?: string[] };
        uniqueness?: { score: number; reasoning?: string };
        relevance?: { score: number; reasoning?: string };
        cp?: { score: number; reasoning?: string; flags?: string[] };
    };
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
        weights_used?: Record<string, number>;
        job_type_detected?: string;
    };
}

export interface SystemStatus {
    backend: boolean;
    ollama: boolean;
    models: string[];
    ready: boolean;
}

/**
 * Check system status (backend, Ollama)
 *
 * Uses the Next.js proxy route (/api/status) instead of calling
 * http://localhost:3001 directly. Direct calls break in any environment
 * other than the developer's own machine (Vercel, Docker, different port).
 */
export async function getSystemStatus(): Promise<SystemStatus> {
    try {
        const res = await fetch('/api/status');
        if (res.ok) {
            return await res.json();
        }
    } catch (error) {
        console.error('Status check failed:', error);
    }
    return { backend: false, ollama: false, models: [], ready: false };
}

/**
 * Evaluate a candidate resume
 *
 * Routes through /api/evaluate (Next.js proxy) instead of localhost:3001
 * directly so this works in any deployment environment.
 */
export async function evaluateCandidate(
    resumeFile: File,
    jobDescription: string,
    githubUrl?: string,
    leetcodeUsername?: string,
    codeforcesUsername?: string
): Promise<EvaluationResult> {
    const formData = new FormData();
    formData.append('resume', resumeFile);
    formData.append('job_description', jobDescription);
    if (githubUrl) formData.append('github_url', githubUrl);
    if (leetcodeUsername) formData.append('leetcode_username', leetcodeUsername);
    if (codeforcesUsername) formData.append('codeforces_username', codeforcesUsername);

    const res = await fetch('/api/evaluate', {
        method: 'POST',
        body: formData,
    });

    if (!res.ok) {
        const error = await res.json();
        throw new Error(error.message || 'Evaluation failed');
    }

    return await res.json();
}

/**
 * Get leaderboard data via Next.js proxy route.
 * Previously called http://localhost:3001/api/leaderboard directly, which
 * fails in any non-localhost environment (Vercel, Docker, CI).
 */
export async function getLeaderboardData(): Promise<Candidate[]> {
    try {
        const res = await fetch('/api/leaderboard', {
            next: { revalidate: 10 }
        });
        
        if (!res.ok) return [];
        
        const data = await res.json();
        
        type LeaderboardItem = {
            id: string;
            name: string;
            overall_score?: number;
            status: string;
            date?: string;
            details?: {
                integrity?: number;
                relevance?: number;
                quality?: number;
                cp?: number;
            };
            tags?: string[];
        };

        return (data as LeaderboardItem[]).map((item) => ({
            id: item.id,
            name: item.name,
            p_score: Math.round((item.overall_score || 0) * 10),
            truth: Math.round((item.details?.integrity || 0) * 10),
            passion: Math.round((item.details?.relevance || 0) * 10), // relevance → passion
            code: Math.round((item.details?.quality || 0) * 10),
            status: item.status,
            flag: item.tags?.[0] ?? "Candidate",
            date: item.date,
        }));
    } catch (error) {
        console.error("Failed to fetch leaderboard:", error);
        return [];
    }
}
