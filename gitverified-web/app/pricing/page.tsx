import Header from "../components/Header";
import Link from "next/link";

/**
 * Pricing page — previously rendered a blank stub with no content,
 * leaving users on an empty page with no context or call to action.
 * Now shows a "Coming Soon" notice so users understand the page is
 * intentionally under construction, not broken.
 */
export default function PricingPage() {
  return (
    <main className="min-h-screen pt-32 px-6 flex flex-col items-center">
      <Header />

      <div className="max-w-2xl w-full text-center space-y-8 py-16">
        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-white/10 bg-white/5 text-xs font-medium text-gray-300">
          <span className="w-1.5 h-1.5 rounded-full bg-yellow-400 animate-pulse"></span>
          Coming Soon
        </div>

        <h1 className="text-4xl md:text-5xl font-serif font-thin text-white tracking-tight">
          Pricing
        </h1>

        <p className="text-lg text-gray-400 leading-relaxed">
          Flexible plans for teams of all sizes are on the way.
          GitVerified is currently in early access — pricing will be
          announced shortly.
        </p>

        <div className="glass-card border border-white/10 rounded-xl p-8 space-y-4 text-left">
          <h2 className="text-white font-semibold text-lg">Early Access</h2>
          <ul className="space-y-3 text-gray-400 text-sm">
            <li className="flex items-start gap-3">
              <span className="text-green-400 mt-0.5">✓</span>
              <span>Self-hosted — run the full stack on your own infrastructure</span>
            </li>
            <li className="flex items-start gap-3">
              <span className="text-green-400 mt-0.5">✓</span>
              <span>Open source — inspect every scoring decision</span>
            </li>
            <li className="flex items-start gap-3">
              <span className="text-green-400 mt-0.5">✓</span>
              <span>No vendor lock-in — powered by local Ollama models</span>
            </li>
          </ul>
        </div>

        <div className="flex flex-col sm:flex-row gap-4 justify-center pt-4">
          <Link
            href="/"
            className="px-6 py-2.5 rounded-lg border border-white/10 bg-white/5 text-white text-sm hover:bg-white/10 transition-colors"
          >
            ← Back to Home
          </Link>
          <Link
            href="https://github.com/cheese-cakee/GitVerified"
            target="_blank"
            className="px-6 py-2.5 rounded-lg bg-white text-black text-sm font-medium hover:bg-gray-200 transition-colors"
          >
            View on GitHub
          </Link>
        </div>
      </div>
    </main>
  );
}
