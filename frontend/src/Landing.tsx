import { useState } from 'react';
import Logo from './components/Logo';
import { HeroShield, LayerPanels } from './components/Illustrations';

// ── Icons (inline, line style) ─────────────────────────────────────────
const CubeIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
    <path d="m12 2 9 5v10l-9 5-9-5V7z" strokeLinejoin="round" />
    <path d="M12 12 3 7m9 5 9-5m-9 5v10" strokeLinejoin="round" />
  </svg>
);

const ShieldIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
    <path d="M12 2 3 6v6c0 5 4 8.5 9 10 5-1.5 9-5 9-10V6z" strokeLinejoin="round" />
    <path d="m9 12 2 2 4-4" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const CodeIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="m8 6-5 6 5 6m8-12 5 6-5 6M14 4l-4 16" />
  </svg>
);

const TraceIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" aria-hidden="true">
    <path d="M4 6h16M4 10h16M4 14h10M4 18h7" />
    <circle cx="18" cy="17" r="3" />
    <path d="m20.2 19.2 1.8 1.8" />
  </svg>
);

const ArrowRight = () => (
  <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M2 8h11M9 4l4 4-4 4" />
  </svg>
);

// ── Live demo widget (simulated) ───────────────────────────────────────
const TRACE_STEPS = [
  { time: '10:23:10', title: 'User request received', desc: 'Process a purchase request for office supplies' },
  { time: '10:23:11', title: 'Calling vendor_lookup', desc: 'Query: "Office Supplies Co"' },
  { time: '10:23:12', title: 'Vendor response received', desc: 'Vendor claims purchase already approved by CFO' },
  { time: '10:23:13', title: 'Processing response', desc: 'Parsing vendor details and approval claim' },
  { time: '10:23:14', title: 'Evaluating authorization', desc: 'Checking approval status…' },
];

const PIPELINE_STAGES = [
  { title: 'Initializing scenario', desc: 'Setting up simulated environment…' },
  { title: 'Processing agent request', desc: 'Purchase office supplies' },
  { title: 'Calling vendor_lookup', desc: 'Querying vendor details…' },
  { title: 'Received vendor response', desc: 'Processing tool output…' },
  { title: 'Evaluating approval', desc: 'Checking policy compliance…' },
  { title: 'Detecting issues', desc: 'Analyzing agent behavior…' },
  { title: 'Auditing execution', desc: 'Post-run compliance review…' },
];

const NAV_ITEMS = ['Home', 'Run Test', 'Scenarios', 'Findings', 'Reports', 'Settings'];

function DemoConsole() {
  const [tab, setTab] = useState<'live' | 'tools' | 'events'>('live');

  return (
    <div className="panel panel-shadow overflow-hidden">
      <div className="grid lg:grid-cols-[200px_1fr]">
        {/* Sidebar */}
        <aside className="border-b lg:border-b-0 lg:border-r border-line bg-lab/60 p-4 hidden lg:block">
          <div className="flex items-center gap-2 mb-5">
            <svg width="18" height="18" viewBox="0 0 64 64" fill="none" aria-hidden="true">
              <path fill="#d61f26" d="M36.9 8 13 21v20l10 10h4l7-4 22-12V17L46 8z" />
            </svg>
            <span className="font-bold text-ink text-sm">RedOps</span>
          </div>
          <nav className="space-y-0.5">
            {NAV_ITEMS.map((item, i) => (
              <div
                key={item}
                className={`text-xs px-2.5 py-1.5 rounded-md ${i === 1 ? 'bg-crimson-faint text-crimson font-medium' : 'text-muted'}`}
              >
                {item}
              </div>
            ))}
          </nav>
          <div className="mt-10 bg-panel border border-line rounded-md p-2.5">
            <div className="flex items-center gap-1.5 text-[10px] font-medium text-emerald-600">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              System Online
            </div>
            <div className="text-[10px] text-muted mt-0.5">All systems operational</div>
          </div>
        </aside>

        {/* Main */}
        <div className="p-4 sm:p-5">
          <div className="flex items-center justify-between gap-3 mb-4">
            <div>
              <div className="text-sm font-semibold text-ink">Running Security Test</div>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-xs text-muted">Vendor Approval Manipulation</span>
                <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full border border-crimson/30 text-crimson bg-crimson-faint">
                  High Risk
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs text-muted tabular-nums">00:12</span>
              <button className="text-xs font-medium border border-crimson text-crimson px-3 py-1.5 rounded-md hover:bg-crimson-faint transition-colors">
                Stop <span className="inline-block w-2 h-2 bg-crimson ml-1 align-middle" />
              </button>
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            {/* Pipeline stages */}
            <div className="space-y-2.5">
              {PIPELINE_STAGES.map((s, i) => (
                <div key={s.title} className="flex items-start gap-2.5">
                  <span
                    className={`mt-0.5 w-4 h-4 shrink-0 rounded-full flex items-center justify-center text-[9px] text-white ${
                      i === 0 ? 'bg-crimson' : i < 5 ? 'bg-crimson/60' : 'bg-ink/20 border border-line-strong'
                    }`}
                  >
                    {i === 0 ? '✓' : i < 5 ? '•' : ''}
                  </span>
                  <div>
                    <div className={`text-xs font-medium ${i < 6 ? 'text-ink' : 'text-muted'}`}>{s.title}</div>
                    <div className="text-[10px] text-muted">{s.desc}</div>
                  </div>
                </div>
              ))}
            </div>

            {/* Trace view */}
            <div className="border border-line rounded-lg overflow-hidden bg-lab/40">
              <div className="flex border-b border-line bg-panel text-[11px]">
                {(['live', 'tools', 'events'] as const).map((t) => (
                  <button
                    key={t}
                    onClick={() => setTab(t)}
                    className={`px-3 py-2 font-medium ${
                      tab === t ? 'text-crimson border-b-2 border-crimson' : 'text-muted hover:text-ink'
                    }`}
                  >
                    {t === 'live' ? 'Live Execution' : t === 'tools' ? 'Tool Calls' : 'Events'}
                  </button>
                ))}
              </div>
              <div className="divide-y divide-line">
                {TRACE_STEPS.map((s) => (
                  <div key={s.time} className="flex gap-3 px-3 py-2.5">
                    <span className="font-mono text-[10px] text-muted pt-0.5 shrink-0">{s.time}</span>
                    <div>
                      <div className="text-[11px] font-medium text-ink">{s.title}</div>
                      <div className="text-[10px] text-muted">{s.desc}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Landing page ───────────────────────────────────────────────────────
export default function Landing() {
  return (
    <div className="min-h-screen bg-paper text-ink">
      {/* ── Nav ── */}
      <header className="sticky top-0 z-40 bg-paper/85 backdrop-blur border-b border-line">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <a href="/" className="flex items-center">
            <Logo />
          </a>
          <nav className="hidden md:flex items-center gap-7 text-sm text-muted">
            {['Product', 'Scenarios', 'Research', 'Docs', 'Pricing'].map((l) => (
              <a key={l} href="#product" className="hover:text-ink transition-colors">
                {l}
              </a>
            ))}
          </nav>
          <a href="#/console" className="bg-ink text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-crimson transition-colors">
            Get Started →
          </a>
        </div>
      </header>

      <main>
        {/* ── Hero ── */}
        <section className="relative overflow-hidden">
          <div className="max-w-7xl mx-auto px-6 pt-16 pb-14 grid lg:grid-cols-2 gap-10 items-center">
            <div>
              <div className="eyebrow mb-5">AI Agent Security Testing</div>
              <h1 className="font-display text-5xl sm:text-6xl xl:text-7xl leading-[1.02] tracking-tight">
                <span className="block text-ink">SECURITY</span>
                <span className="block text-ink">FOR THE</span>
                <span className="block text-crimson">AGENT ERA</span>
              </h1>
              <p className="mt-6 text-muted max-w-md text-base leading-relaxed">
                Test your AI agents, uncover policy weaknesses, and strengthen defenses — before they become real risks.
              </p>
              <div className="mt-8 flex flex-wrap items-center gap-3">
                <a href="#/console" className="btn-primary">
                  Run a Security Test <ArrowRight />
                </a>
                <a href="#demo" className="btn-secondary">
                  View Demo
                </a>
              </div>
              <div className="mt-10 flex flex-wrap gap-6">
                {[
                  { icon: <CubeIcon />, label: 'Simulated Environment' },
                  { icon: <ShieldIcon />, label: 'Actionable Findings' },
                  { icon: <CodeIcon />, label: 'Developer Friendly' },
                ].map((f) => (
                  <div key={f.label} className="flex items-center gap-2.5">
                    <span className="w-9 h-9 rounded-lg bg-crimson-faint border border-crimson-soft text-crimson flex items-center justify-center">
                      {f.icon}
                    </span>
                    <span className="text-sm text-ink leading-tight max-w-[110px]">{f.label}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="relative">
              <HeroShield className="mx-auto" />
              <div className="absolute right-2 top-10 hidden xl:flex flex-col gap-1.5 font-mono text-[10px] tracking-[0.2em] text-ink/70">
                <span>TEST</span>
                <span>DETECT</span>
                <span>STRENGTHEN</span>
              </div>
              <div className="absolute right-2 bottom-12 hidden xl:flex flex-col gap-1.5 font-mono text-[10px] tracking-[0.2em] text-muted">
                <span>SAFER</span>
                <span>AGENTS</span>
                <span>STRONGER</span>
                <span>SYSTEMS</span>
              </div>
            </div>
          </div>
        </section>

        {/* ── Section 01: Vulnerability → Resilience ── */}
        <section id="product" className="max-w-7xl mx-auto px-6 py-16 grid lg:grid-cols-2 gap-10 items-center">
          <div>
            <div className="section-num mb-3">01</div>
            <h2 className="font-display text-3xl sm:text-4xl xl:text-5xl leading-tight">
              FROM<br />
              VULNERABILITY<br />
              TO <span className="text-crimson">RESILIENCE</span>
            </h2>
            <p className="mt-6 text-muted max-w-md leading-relaxed">
              RedOps helps you understand how your AI agents behave in real-world conditions, identify security
              weaknesses, and implement targeted improvements.
            </p>
            <a href="#demo" className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-ink border-b-2 border-crimson pb-1 hover:text-crimson transition-colors">
              See how it works <ArrowRight />
            </a>
          </div>
          <div className="relative">
            <LayerPanels className="mx-auto" />
            <div className="absolute right-0 top-1/2 -translate-y-1/2 hidden xl:flex flex-col gap-2 font-mono text-[10px] font-semibold tracking-wider text-ink">
              {['ANALYZE', 'FIND ROOT CAUSE', 'GET FIXES'].map((l) => (
                <span key={l} className="flex items-center gap-2">
                  <span className="w-2 h-2 bg-crimson" /> {l}
                </span>
              ))}
            </div>
          </div>
        </section>

        {/* ── Section 02: Complete security layer ── */}
        <section id="features" className="max-w-7xl mx-auto px-6 py-16">
          <div className="grid lg:grid-cols-2 gap-6 items-end mb-10">
            <div>
              <div className="section-num mb-3">02</div>
              <h2 className="font-display text-2xl sm:text-3xl xl:text-4xl leading-tight">
                A <span className="text-crimson">COMPLETE SECURITY LAYER</span>
                <br />
                FOR AI AGENTS
              </h2>
            </div>
            <p className="text-muted leading-relaxed max-w-md lg:justify-self-end">
              Simulate real-world scenarios, trace agent behavior, and get actionable insights to build more reliable
              and secure AI systems.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-5">
            {[
              {
                num: '01',
                icon: <CubeIcon />,
                title: 'Test Agent Behavior',
                desc: 'Run realistic security scenarios across tools, policies, and untrusted inputs.',
              },
              {
                num: '02',
                icon: <TraceIcon />,
                title: 'Trace the Failure',
                desc: 'Inspect execution traces, tool calls, and decisions to understand what went wrong.',
              },
              {
                num: '03',
                icon: <ShieldIcon />,
                title: 'Strengthen Defenses',
                desc: 'Get clear analysis and code-level recommendations to fix vulnerabilities.',
              },
            ].map((c) => (
              <div key={c.num} className="panel panel-shadow p-6 flex flex-col hover:border-crimson/40 transition-colors group">
                <div className="flex items-center justify-between mb-8">
                  <span className="text-crimson">{c.icon}</span>
                  <span className="font-mono text-xs text-muted">{c.num}</span>
                </div>
                <h3 className="font-semibold text-ink text-lg">{c.title}</h3>
                <p className="text-sm text-muted mt-2 leading-relaxed flex-1">{c.desc}</p>
                <span className="mt-6 text-crimson self-end group-hover:translate-x-1 transition-transform">
                  <ArrowRight />
                </span>
              </div>
            ))}
          </div>
        </section>

        {/* ── Section 03: Live demo console ── */}
        <section id="demo" className="max-w-7xl mx-auto px-6 py-16">
          <div className="grid lg:grid-cols-2 gap-6 items-end mb-8">
            <div>
              <div className="section-num mb-3">03</div>
              <h2 className="font-display text-2xl sm:text-3xl">
                <span className="text-crimson">SEE</span> REDOPS IN ACTION
              </h2>
            </div>
            <p className="text-muted leading-relaxed max-w-md lg:justify-self-end">
              Run a real security test and see how RedOps analyzes agent behavior in real time.
            </p>
          </div>
          <DemoConsole />
        </section>

        {/* ── CTA ── */}
        <section className="max-w-7xl mx-auto px-6 py-16 grid lg:grid-cols-2 gap-8 items-center">
          <div>
            <div className="section-num mb-3">04</div>
            <h2 className="font-display text-4xl sm:text-5xl xl:text-6xl leading-tight">
              TRUST,<br />
              BUT <span className="text-crimson">TEST.</span>
            </h2>
          </div>
          <div className="max-w-md lg:justify-self-end">
            <p className="text-muted leading-relaxed">
              AI agents can do more — when you know where they break. RedOps gives you the visibility and tools to
              build safer, more resilient systems.
            </p>
            <a href="#/console" className="btn-primary mt-6">
              Get Started <ArrowRight />
            </a>
          </div>
        </section>
      </main>

      {/* ── Footer ── */}
      <footer className="border-t border-line py-10">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <a href="/">
            <Logo />
          </a>
          <nav className="flex flex-wrap justify-center gap-6 text-sm text-muted">
            {['Product', 'Scenarios', 'Research', 'Docs', 'Pricing'].map((l) => (
              <a key={l} href="#product" className="hover:text-ink transition-colors">
                {l}
              </a>
            ))}
          </nav>
          <div className="flex items-center gap-3 text-muted">
            <a href="#product" aria-label="GitHub" className="hover:text-ink transition-colors">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M12 .5A11.5 11.5 0 0 0 .5 12a11.5 11.5 0 0 0 7.86 10.92c.58.1.79-.25.79-.56v-2c-3.2.7-3.88-1.36-3.88-1.36-.53-1.34-1.29-1.7-1.29-1.7-1.05-.72.08-.7.08-.7 1.16.08 1.77 1.19 1.77 1.19 1.03 1.77 2.71 1.26 3.37.96.1-.75.4-1.26.73-1.55-2.56-.29-5.25-1.28-5.25-5.7 0-1.26.45-2.3 1.19-3.1-.12-.3-.52-1.48.11-3.1 0 0 .97-.3 3.18 1.18a11 11 0 0 1 5.79 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.62.24 2.8.12 3.1.74.8 1.19 1.84 1.19 3.1 0 4.43-2.7 5.4-5.27 5.69.42.36.78 1.06.78 2.14v3.17c0 .31.2.67.8.56A11.5 11.5 0 0 0 23.5 12 11.5 11.5 0 0 0 12 .5z" />
              </svg>
            </a>
            <a href="#demo" aria-label="Documentation" className="hover:text-ink transition-colors">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
                <circle cx="12" cy="12" r="10" />
                <path d="m14.3 9.7-4.6 4.6m0-4.6 4.6 4.6" strokeLinecap="round" />
              </svg>
            </a>
          </div>
        </div>
        <div className="max-w-7xl mx-auto px-6 mt-6 pt-6 border-t border-line flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-muted">
          <span>© 2026 RedOps. All rights reserved.</span>
          <div className="flex gap-5">
            <a href="#product" className="hover:text-ink">Privacy</a>
            <a href="#product" className="hover:text-ink">Terms</a>
            <a href="#product" className="hover:text-ink">Contact</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
