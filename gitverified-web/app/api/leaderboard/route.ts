import { NextResponse } from 'next/server';

const BACKEND_URL = 'http://localhost:3001';

/**
 * Proxy the leaderboard request to the Python backend.
 * api.ts previously called http://localhost:3001/api/leaderboard directly,
 * bypassing this proxy layer entirely. That breaks in any non-localhost
 * deployment. All API calls now route through Next.js proxy routes.
 */
export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/api/leaderboard`, {
      method: 'GET',
      next: { revalidate: 10 },
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: `Backend returned ${response.status}` },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Leaderboard proxy error:', error);
    return NextResponse.json(
      { error: 'Backend not available. Is python api_server.py running?' },
      { status: 503 }
    );
  }
}
