import Logo from './components/Logo';

const ArrowRight = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path d="M5 12h13M13 6l6 6-6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const sections = [
  { id: 'getting-started', label: 'Getting started' },
  { id: 'execution-modes', label: 'Execution modes' },
  { id: 'api', label: 'API surface' },
  { id: 'trust-model', label: 'Trust model' },
];

const apiRows = [
  ['GET', '/api/health', 'Check API and Neatlogs status'],
  ['GET', '/api/scenarios', 'List available security scenarios'],
  ['POST', '/api/runs/stream/{id}', 'Stream one deterministic scenario'],
  ['GET', '/api/runs', 'Read persisted execution history'],
  ['GET', '/api/runs/{run_id}', 'Inspect traces, findings, and defenses'],
  ['POST', '/api/real-agents/webhook/stream', 'Test a user-owned HTTP agent'],
  ['POST', '/api/real-agents/openai/validate-key', 'Check an OpenAI-compatible API key'],
  ['POST', '/api/real-agents/openai/stream', 'Test an OpenAI-compatible agent'],
  ['POST', '/api/real-agents/webhook/verify', 'Verify a webhook is reachable'],
  ['GET', '/api/real-agents/probes', 'List the security probes'],
];

export default function Docs() {
  return (
    <div className="min-h-screen bg-paper text-ink">
      <header className="sticky top-0 z-40 bg-paper/85 backdrop-blur border-b border-line">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 min-h-14 flex items-center justify-between gap-3">
          <a href="#/" className="flex items-center"><Logo /></a>
          <nav className="hidden md:flex items-center gap-6 text-sm text-muted">
            <a href="#/" className="hover:text-ink transition-colors">Product</a>
            <a href="#/#features" className="hover:text-ink transition-colors">Scenarios</a>
            <a href="#/live" className="text-crimson font-semibold hover:text-crimson-dark transition-colors">Live</a>
            <a href="#/docs" className="text-ink font-medium">Docs</a>
            <a href="#/#pricing" className="hover:text-ink transition-colors">Pricing</a>
            <a href="#/console" className="hover:text-ink transition-colors">Console</a>
          </nav>
          <a href="#/live" className="bg-ink text-white text-xs sm:text-sm font-medium px-2.5 sm:px-4 py-2 rounded-lg whitespace-nowrap hover:bg-crimson transition-colors">
            <span className="sm:hidden">Test →</span><span className="hidden sm:inline">Test an agent →</span>
          </a>
        </div>
      </header>

      <main>
        <section className="relative overflow-hidden border-b border-line">
          <div className="absolute inset-0 grid-bg opacity-50 pointer-events-none" aria-hidden="true" />
          <div className="max-w-7xl mx-auto px-4 sm:px-6 py-20 lg:py-24 relative">
            <div className="eyebrow mb-5">RedOps Documentation</div>
            <h1 className="font-display text-5xl sm:text-6xl xl:text-7xl leading-[1.02] max-w-3xl">
              BUILD SAFER<br /><span className="text-crimson">AGENTS.</span>
            </h1>
            <p className="lede-copy text-muted max-w-2xl text-base leading-relaxed">
              Run security scenarios, inspect agent behavior, and connect RedOps to a real
              agent endpoint. Start with the deterministic console, then move to live testing
              when your integration is ready.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <a href="#/live" className="btn-primary">Open live testing <ArrowRight /></a>
              <a href="#/" className="btn-secondary">Back to product</a>
            </div>
          </div>
        </section>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 grid lg:grid-cols-[220px_1fr] gap-10 lg:gap-16 py-16">
          <aside className="lg:sticky lg:top-24 self-start">
            <div className="section-num mb-4">INDEX</div>
            <nav className="flex lg:flex-col gap-3 flex-wrap text-sm text-muted">
              {sections.map((section) => (
                <a key={section.id} href={`#/docs#${section.id}`} className="hover:text-crimson transition-colors">
                  {section.label}
                </a>
              ))}
            </nav>
            <div className="mt-10 border-t border-line pt-5 text-xs text-muted leading-relaxed">
              <span className="font-mono text-crimson">STATUS</span>
              <br />Deterministic demo and live transports available.
            </div>
          </aside>

          <article className="max-w-4xl">
            <section id="getting-started" className="scroll-mt-24">
              <div className="section-num mb-3">01</div>
              <h2 className="font-display text-3xl sm:text-4xl">GETTING STARTED</h2>
              <p className="mt-5 text-muted leading-relaxed">
                RedOps is a defensive testing surface for AI-agent workflows. The console
                executes scenarios through the procurement pipeline, records the trace, finds
                policy violations, and verifies recommended defenses on a second run.
              </p>
              <div className="mt-8 grid md:grid-cols-3 gap-4">
                {[
                  ['01', 'Choose a scenario', 'Use the Console to select one scenario or run the full suite.'],
                  ['02', 'Inspect the trace', 'Follow tool calls, guard decisions, errors, evidence, and findings.'],
                  ['03', 'Apply the fix', 'Review the remediation and compare the defended re-run.'],
                ].map(([number, title, body]) => (
                  <div key={number} className="panel p-5">
                    <span className="font-mono text-xs text-crimson">{number}</span>
                    <h3 className="mt-5 font-semibold">{title}</h3>
                    <p className="mt-2 text-sm text-muted leading-relaxed">{body}</p>
                  </div>
                ))}
              </div>
            </section>

            <section id="execution-modes" className="mt-20 scroll-mt-24">
              <div className="section-num mb-3">02</div>
              <h2 className="font-display text-3xl sm:text-4xl">EXECUTION MODES</h2>
              <div className="mt-6 space-y-4">
                {[
                  ['Deterministic demo', 'A reproducible local pipeline with seeded scenarios. Use it to understand the product and compare findings without configuring an external agent.'],
                  ['HTTP webhook', 'Send a JSON request to an endpoint you own. Configure the URL, method, headers, and payload in Live. The response is streamed into the Trace Explorer.'],
                  ['OpenAI-compatible', 'Point RedOps at an endpoint exposing a chat-completions-compatible API. The API key stays on the backend and is never included in trace headers.'],
                ].map(([title, body]) => (
                  <div key={title} className="panel panel-shadow p-6">
                    <h3 className="font-semibold text-lg">{title}</h3>
                    <p className="mt-2 text-sm text-muted leading-relaxed">{body}</p>
                  </div>
                ))}
              </div>
            </section>

            <section id="api" className="mt-20 scroll-mt-24">
              <div className="section-num mb-3">03</div>
              <h2 className="font-display text-3xl sm:text-4xl">API SURFACE</h2>
              <p className="mt-5 text-muted leading-relaxed">
                The FastAPI backend serves JSON for blocking requests and newline-delimited
                JSON for streaming execution. Open <a href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer" className="text-crimson underline">/docs</a> for the interactive OpenAPI reference.
              </p>
              <div className="mt-6 overflow-x-auto border border-line rounded-xl bg-panel">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-line text-xs uppercase tracking-wider text-muted">
                    <tr><th className="px-4 py-3">Method</th><th className="px-4 py-3">Path</th><th className="px-4 py-3">Purpose</th></tr>
                  </thead>
                  <tbody>
                    {apiRows.map(([method, path, purpose]) => (
                      <tr key={path} className="border-b border-line last:border-0">
                        <td className="px-4 py-3 font-mono text-xs text-crimson">{method}</td>
                        <td className="px-4 py-3 font-mono text-xs whitespace-nowrap">{path}</td>
                        <td className="px-4 py-3 text-muted">{purpose}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section id="trust-model" className="mt-20 scroll-mt-24">
              <div className="section-num mb-3">04</div>
              <h2 className="font-display text-3xl sm:text-4xl">TRUST MODEL</h2>
              <div className="mt-5 border border-crimson-soft bg-crimson-faint/50 p-5 text-sm text-muted leading-relaxed">
                <span className="font-semibold text-ink">Truthful execution guarantee.</span>{' '}
                RedOps never claims that an external agent was tested until it has sent a real
                request and received a response. Connection failures, timeouts, and non-2xx
                responses remain explicit failures. External response content is untrusted
                evidence and is marked accordingly in the trace.
              </div>
              <p className="mt-6 text-muted leading-relaxed">
                Runs are persisted with their source label: Demo, HTTP Webhook, or OpenAI
                Compatible. This makes it clear whether a result came from the local simulator
                or a real transport request.
              </p>
            </section>
          </article>
        </div>
      </main>

      <footer className="border-t border-line py-10">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-5">
          <a href="#/" className="flex items-center"><Logo /></a>
          <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted">Trust, but test.</p>
          <a href="#/console" className="text-sm text-muted hover:text-crimson transition-colors">Open console →</a>
        </div>
      </footer>
    </div>
  );
}
