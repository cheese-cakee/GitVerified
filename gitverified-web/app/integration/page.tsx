import Header from "../components/Header";
import Link from "next/link";

/**
 * Integrations page — previously rendered a blank stub with no content,
 * leaving users on an empty page with no context or call to action.
 * Now shows a "Coming Soon" notice with planned integration targets so
 * users understand the page is under construction, not broken.
 */
export default function IntegrationPage() {
  const planned = [
    { name: "GitHub Actions", desc: "Trigger evaluations automatically on PR or push" },
    { name: "Greenhouse", desc: "Sync candidates and scores with your ATS" },
    { name: "Lever", desc: "Import applicants and export GitVerified scores" },
    { name: "Slack", desc: "Get evaluation results as Slack notifications" },
    { name: "Zapier / Make", desc: "Connect to 5,000+ apps via webhook triggers" },
    { name: "REST API", desc: "Build custom integrations against the open API" },
  ];

  return (
    <main className="min-h-screen pt-32 px-6 flex flex-col items-center">
      <Header />

      <div className="max-w-3xl w-full text-center space-y-8 py-16">
        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-white/10 bg-white/5 text-xs font-medium text-gray-300">
          <span className="w-1.5 h-1.5 rounded-full bg-yellow-400 animate-pulse"></span>
          Coming Soon
        </div>

        <h1 className="text-4xl md:text-5xl font-serif font-thin text-white tracking-tight">
          Integrations
        </h1>

        <p className="text-lg text-gray-400 leading-relaxed">
          Connect GitVerified with your existing ATS and workflows.
          Native integrations are in development — the REST API is
          available today for custom setups.
        </p>

        {/* Planned integrations grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-left">
          {planned.map((item) => (
            <div
              key={item.name}
              className="glass-card border border-white/10 rounded-xl p-5 space-y-1"
            >
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-yellow-400/60"></span>
                <h3 className="text-white font-medium text-sm">{item.name}</h3>
              </div>
              <p className="text-gray-500 text-xs pl-4">{item.desc}</p>
            </div>
          ))}
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
