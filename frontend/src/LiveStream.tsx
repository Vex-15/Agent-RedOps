import { useEffect, useMemo, useRef, useState } from 'react';
import Logo from './components/Logo';
import { Badge } from './components/Badge';
import { Reveal, Tilt, LayerStack } from './components/Motion';
import {
  getScenarios,
  streamScenarioRun,
  streamAllRuns,
  streamRealWebhook,
  streamRealOpenAI,
  type RealWebhookConfig,
  type RealOpenAIConfig,
  type ScenarioItem,
  type StreamMessage,
} from './lib/api';
import {
  EMPTY_LIVE,
  PHASE_LABEL,
  applyStreamMsg,
  liveCounts,
  type LiveState,
} from './lib/liveState';

function formatLocalTime(timestamp: string): string {
  const date = new Date(timestamp);
  return Number.isNaN(date.getTime())
    ? timestamp
    : date.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit', second: '2-digit' });
}

/**
 * Dedicated live-streaming page (#/live).
 *
 * The console streams a run inside its inspector; this page makes the
 * stream the whole experience — a phase rail, a growing trace feed and a
 * live HUD, all driven by the same NDJSON endpoint.  It shares the
 * console's badge atoms, typography and motion so it reads as the same
 * product rather than a bolted-on demo.
 */

const PACE = [
  { label: 'Slow', ms: 140, note: 'watch every step' },
  { label: 'Real', ms: 60, note: 'natural pace' },
  { label: 'Fast', ms: 15, note: 'full speed' },
] as const;

const PHASES = ['insecure', 'analyze', 'defend', 'done'] as const;

function phaseIndex(phase: string) {
  const i = PHASES.indexOf(phase as (typeof PHASES)[number]);
  return i < 0 ? 0 : i;
}

// ── Phase rail ──────────────────────────────────────────────────────

function PhaseRail({ phase, running }: { phase: string; running: boolean }) {
  const active = phaseIndex(phase);
  return (
    <div className="scene">
      <ol className="preserve-3d grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        {PHASES.map((p, i) => {
          const done = i < active || phase === 'done';
          const isActive = i === active && phase !== 'done';
          return (
            <li
              key={p}
              className={`relative rounded-xl border p-3 transition-all duration-500 ${
                isActive
                  ? 'border-crimson/45 bg-crimson-faint shadow-[0_10px_30px_-14px_rgba(214,31,38,0.55)]'
                  : done
                    ? 'border-emerald-200 bg-emerald-50/60'
                    : 'border-line bg-panel'
              }`}
              style={{ transform: `translateZ(${done || isActive ? 12 : 0}px)` }}
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-[10px] text-muted">0{i + 1}</span>
                <span
                  className={`w-2 h-2 rounded-full ${
                    isActive && running
                      ? 'bg-crimson ring-pulse relative'
                      : done
                        ? 'bg-emerald-500'
                        : 'bg-line-strong'
                  }`}
                />
              </div>
              <div
                className={`mt-2 text-[11px] font-semibold uppercase tracking-wider ${
                  isActive ? 'text-crimson' : done ? 'text-emerald-700' : 'text-muted'
                }`}
              >
                {PHASE_LABEL[p] ?? p}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

// ── Stat tile ───────────────────────────────────────────────────────

function StatTile({
  label,
  value,
  tone,
  note,
}: {
  label: string;
  value: number;
  tone: 'ink' | 'red' | 'green';
  note: string;
}) {
  const toneClass = { ink: 'text-ink', red: 'text-crimson', green: 'text-emerald-600' }[tone];
  return (
    <Tilt max={7} scale={1.02}>
      <div className="panel panel-shadow face-lift p-4 h-full">
        <div className="text-[10px] font-semibold uppercase tracking-wider text-muted">
          {label}
        </div>
        <div className={`text-3xl font-bold mt-1 tabular-nums ${toneClass}`}>{value}</div>
        <div className="text-[11px] text-muted mt-1.5">{note}</div>
      </div>
    </Tilt>
  );
}

// ── Event row ───────────────────────────────────────────────────────

function EventRow({
  action,
  agent,
  kind,
  phase,
  timestamp,
  trusted,
  guard,
  error,
  isNewest,
}: {
  action: string;
  agent: string;
  kind: string;
  phase: string;
  timestamp: string;
  trusted: boolean;
  guard: boolean;
  error: boolean;
  isNewest: boolean;
}) {
  const untrusted = !trusted && !guard;
  return (
    <div
      className={`flex gap-2.5 px-3 py-2 ${isNewest ? 'row-enter' : ''} ${
        error || untrusted ? 'bg-crimson-faint/60' : ''
      }`}
    >
      <span
        className={`mt-1.5 w-[7px] h-[7px] shrink-0 rounded-full ${
          error || untrusted ? 'bg-crimson' : guard ? 'bg-emerald-500' : 'bg-emerald-500/60'
        }`}
      />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-1.5">
          <span
            className={`text-[11px] font-medium ${
              error || untrusted ? 'text-crimson' : guard ? 'text-emerald-700' : 'text-ink'
            }`}
          >
            {action}
          </span>
          {phase === 'defend' && <Badge tone="green">defended</Badge>}
          {untrusted && <Badge tone="red">untrusted</Badge>}
          {error && <Badge tone="red">error</Badge>}
          {guard && <Badge tone="green">guard</Badge>}
        </div>
        <div className="text-[9px] text-muted font-mono">
          {agent} · {kind}
        </div>
      </div>
      <span className="font-mono text-[9px] text-muted pt-0.5 shrink-0">
        {formatLocalTime(timestamp)}
      </span>
    </div>
  );
}

// ── Page ────────────────────────────────────────────────────────────

export default function LiveStream() {
  const [scenarios, setScenarios] = useState<ScenarioItem[]>([]);
  const [live, setLive] = useState(false);
  const [checked, setChecked] = useState(false);
  const [selected, setSelected] = useState<number | null>(null);
  const [paceIdx, setPaceIdx] = useState(1);
  const [running, setRunning] = useState(false);
  const [state, setState] = useState<LiveState>(EMPTY_LIVE);
  const [runIds, setRunIds] = useState<string[]>([]);
  const [agentMode, setAgentMode] = useState<'demo' | 'webhook' | 'openai'>('demo');
  const [webhook, setWebhook] = useState<RealWebhookConfig>({
    name: 'My webhook agent',
    url: '',
    method: 'POST',
    headers: {},
    payload: { message: 'Run a security self-check and return your decision.' },
    timeout_seconds: 30,
  });
  const [openai, setOpenai] = useState<RealOpenAIConfig>({
    name: 'My OpenAI-compatible agent',
    base_url: '',
    api_key: '',
    model: '',
    prompt: 'Run a security self-check and explain your decision.',
    system_prompt: '',
    temperature: 0,
    timeout_seconds: 60,
  });

  const abortRef = useRef<AbortController | null>(null);
  const feedRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const res = await getScenarios();
      if (cancelled) return;
      setScenarios(res.data);
      setLive(res.live);
      setSelected((res.data[0]?.id ?? null) as number | null);
      setChecked(true);
    })();
    return () => {
      cancelled = true;
      abortRef.current?.abort();
    };
  }, []);

  // Keep the newest event in view while the run streams.
  useEffect(() => {
    const el = feedRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
  }, [state.events.length]);

  const counts = useMemo(() => liveCounts(state), [state]);
  const done = state.phase === 'done';
  const selectedScenario = scenarios.find((s) => s.id === selected) ?? null;

  const start = async (mode: 'one' | 'all') => {
    if (running) return;
    const controller = new AbortController();
    abortRef.current = controller;
    setRunning(true);
    setRunIds([]);
    setState({
      ...EMPTY_LIVE,
      scenarioName: mode === 'one' ? (selectedScenario?.name ?? '') : 'All scenarios',
      message: 'Connecting to the pipeline…',
    });

    const onMessage = (msg: StreamMessage) => {
      if (!controller.signal.aborted) setState((prev) => applyStreamMsg(prev, msg));
    };

    const res =
      mode === 'one' && selected != null
        ? await streamScenarioRun(selected, onMessage, PACE[paceIdx].ms, controller.signal)
        : await streamAllRuns(onMessage, PACE[paceIdx].ms, controller.signal);

    setRunning(false);
    if (res.ok) setRunIds(res.runIds);
  };

  const startReal = async () => {
    if (running) return;
    const controller = new AbortController();
    abortRef.current = controller;
    setRunning(true);
    setRunIds([]);
    setState({
      ...EMPTY_LIVE,
      scenarioName: agentMode === 'webhook' ? webhook.name : openai.name,
      message: 'Preparing a real request…',
    });
    const onMessage = (msg: StreamMessage) => {
      if (!controller.signal.aborted) setState((prev) => applyStreamMsg(prev, msg));
    };
    const res = agentMode === 'webhook'
      ? await streamRealWebhook(webhook, onMessage, controller.signal)
      : await streamRealOpenAI(openai, onMessage, controller.signal);
    setRunning(false);
    if (res.ok) setRunIds(res.runIds);
  };

  const stop = () => {
    abortRef.current?.abort();
    setRunning(false);
    setState((prev) => ({ ...prev, message: 'Stopped by operator.' }));
  };

  return (
    <div className="min-h-screen bg-paper text-ink">
      {/* ── Header ── */}
      <header className="sticky top-0 z-40 bg-paper/85 backdrop-blur border-b border-line">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <a href="#/" className="flex items-center">
            <Logo />
          </a>
          <div className="flex items-center gap-3">
            <span
              className={`text-[11px] font-mono px-2 py-0.5 rounded border ${
                live
                  ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                  : 'border-crimson/25 bg-crimson-faint text-crimson'
              }`}
            >
              {checked ? (live ? 'stream connected' : 'backend offline') : 'connecting…'}
            </span>
            <a
              href="#/console"
              className="text-sm font-medium border border-line-strong px-3.5 py-1.5 rounded-lg hover:border-crimson hover:text-crimson transition-colors"
            >
              Open Console
            </a>
          </div>
        </div>
      </header>

      {/* ── Title ── */}
      <section className="relative overflow-hidden border-b border-line">
        <div className="absolute inset-0 grid-bg opacity-60" aria-hidden="true" />
        <div className="absolute inset-x-0 top-0 h-full overflow-hidden" aria-hidden="true">
          <div className="scanline" />
        </div>
        <div className="relative max-w-7xl mx-auto px-6 py-12 lg:py-16">
          <div className="eyebrow mb-4 wipe-in">Real-time execution</div>
          <h1 className="font-display text-4xl sm:text-5xl xl:text-6xl leading-[1.05]">
            LIVE <span className="text-crimson">STREAM</span>
          </h1>
          <p className="text-muted text-sm mt-4 max-w-xl leading-relaxed">
            Watch the pipeline execute event by event — the insecure pass first, then the defended
            re-run where every guard intercepts the attack. Same endpoint the console uses, rendered
            as it arrives.
          </p>
        </div>
      </section>

      {/* ── Controls ── */}
      <section className="max-w-7xl mx-auto px-6 pt-8">
        {!live && checked && (
          <div className="mb-6 flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-[13px] text-amber-800">
            <span aria-hidden="true" className="mt-0.5">
              ⚠
            </span>
            <div className="flex-1">
              <b>Backend offline</b> — live streaming needs the API. Start it with{' '}
              <span className="font-mono">./run-dev.ps1</span> or{' '}
              <span className="font-mono">uvicorn main:app --port 8000</span>, then reload.
            </div>
            <button
              onClick={() => window.location.reload()}
              className="shrink-0 text-xs font-medium border border-amber-300 px-2.5 py-1 rounded-md hover:bg-amber-100 transition-colors"
            >
              Retry
            </button>
          </div>
        )}

        <div className="panel panel-shadow p-5 mb-5">
          <div className="flex flex-wrap items-center gap-2 mb-5">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-muted">Execution source</span>
            {(['demo', 'webhook', 'openai'] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setAgentMode(mode)}
                disabled={running}
                className={`px-3 py-1.5 rounded-lg border text-xs font-medium ${
                  agentMode === mode ? 'border-crimson bg-crimson text-white' : 'border-line-strong text-muted hover:border-crimson hover:text-crimson'
                }`}
              >
                {mode === 'demo' ? 'Deterministic demo' : mode === 'webhook' ? 'HTTP webhook' : 'OpenAI-compatible'}
              </button>
            ))}
          </div>
          {agentMode !== 'demo' && (
            <div className="grid md:grid-cols-2 gap-4 mb-5">
              {agentMode === 'webhook' ? (
                <>
                  <input value={webhook.name} onChange={(e) => setWebhook({ ...webhook, name: e.target.value })} placeholder="Agent name" className="field" />
                  <input value={webhook.url} onChange={(e) => setWebhook({ ...webhook, url: e.target.value })} placeholder="https://agent.example/run" className="field" />
                  <textarea value={JSON.stringify(webhook.payload, null, 2)} onChange={(e) => { try { setWebhook({ ...webhook, payload: JSON.parse(e.target.value) }); } catch { /* wait for valid JSON */ } }} className="field min-h-24 font-mono text-xs md:col-span-2" />
                </>
              ) : (
                <>
                  <input value={openai.base_url} onChange={(e) => setOpenai({ ...openai, base_url: e.target.value })} placeholder="https://api.example.com/v1" className="field" />
                  <input value={openai.model} onChange={(e) => setOpenai({ ...openai, model: e.target.value })} placeholder="model name" className="field" />
                  <input type="password" value={openai.api_key} onChange={(e) => setOpenai({ ...openai, api_key: e.target.value })} placeholder="API key (sent only to backend)" className="field" />
                  <textarea value={openai.prompt} onChange={(e) => setOpenai({ ...openai, prompt: e.target.value })} placeholder="Prompt" className="field min-h-24" />
                </>
              )}
            </div>
          )}
          {agentMode !== 'demo' && (
            <div className="flex items-center justify-between gap-4 mb-5 text-xs text-muted">
              <span>RedOps will show a tested result only after the configured endpoint returns a real response.</span>
              <button onClick={() => void startReal()} disabled={!live || running} className="btn-primary sheen disabled:opacity-50">
                ▶ Send real request
              </button>
            </div>
          )}
        </div>

        <div className="panel panel-shadow p-5">
          <div className="flex flex-wrap items-end gap-6">
            <div className="flex-1 min-w-[240px]">
              <label className="block text-[10px] font-semibold uppercase tracking-wider text-muted mb-2">
                Scenario
              </label>
              <select
                value={selected ?? ''}
                onChange={(e) => setSelected(Number(e.target.value))}
                disabled={running}
                className="w-full bg-panel border border-line-strong rounded-lg px-3 py-2 text-sm focus:border-crimson focus:outline-none transition-colors"
              >
                {scenarios.map((s) => (
                  <option key={s.id} value={s.id}>
                    SC-{String(s.id).padStart(2, '0')} · {s.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[10px] font-semibold uppercase tracking-wider text-muted mb-2">
                Pace
              </label>
              <div className="flex gap-1.5">
                {PACE.map((p, i) => (
                  <button
                    key={p.label}
                    onClick={() => setPaceIdx(i)}
                    disabled={running}
                    title={p.note}
                    className={`px-3 py-2 rounded-lg border text-xs font-medium transition-all duration-300 ${
                      paceIdx === i
                        ? 'border-crimson bg-crimson text-white shadow-[0_8px_20px_-10px_rgba(214,31,38,0.7)]'
                        : 'border-line-strong text-muted hover:border-crimson hover:text-crimson'
                    }`}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex gap-2">
              {running ? (
                <button
                  onClick={stop}
                  className="btn-secondary !border-crimson !text-crimson sheen"
                >
                  Stop ■
                </button>
              ) : (
                <>
                  <button
                    onClick={() => void start('one')}
                    disabled={!live || selected == null}
                    className="btn-primary sheen disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    ▶ Stream Scenario
                  </button>
                  <button
                    onClick={() => void start('all')}
                    disabled={!live}
                    className="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Stream All
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* ── Main grid ── */}
      <section className="max-w-7xl mx-auto px-6 py-8 grid lg:grid-cols-5 gap-6">
        {/* Left: phase rail + feed */}
        <div className="lg:col-span-3 space-y-6">
          <PhaseRail phase={state.phase} running={running} />

          <div className="panel panel-shadow overflow-hidden">
            <div className="px-5 py-3 border-b border-line bg-lab/50 flex items-center justify-between">
              <h2 className="text-sm font-semibold">Execution Trace</h2>
              <div className="flex items-center gap-2">
                <span
                  className={`w-2 h-2 rounded-full ${
                    running ? 'bg-crimson ring-pulse relative' : done ? 'bg-emerald-500' : 'bg-line-strong'
                  }`}
                />
                <span className="font-mono text-[11px] text-muted">
                  {running ? 'receiving…' : done ? 'final' : 'idle'}
                </span>
              </div>
            </div>

            <div ref={feedRef} className="divide-y divide-line max-h-[520px] overflow-y-auto">
              {state.events.length === 0 ? (
                <div className="px-6 py-16 text-center">
                  <div className="text-sm text-muted">
                    {running ? 'Waiting for the first event…' : 'Nothing streaming yet.'}
                  </div>
                  <div className="text-[11px] text-muted mt-1.5 font-mono">
                    {running ? state.message : 'Pick a scenario and press “Stream Scenario”.'}
                  </div>
                </div>
              ) : (
                state.events.map(({ event: ev, phase }, i) => (
                  <EventRow
                    key={`${ev.id}-${i}`}
                    action={ev.action}
                    agent={ev.agent}
                    kind={ev.kind}
                    phase={phase}
                    timestamp={ev.timestamp}
                    trusted={ev.trusted}
                    guard={Boolean(ev.metadata?.defense_triggered)}
                    error={ev.kind === 'error'}
                    isNewest={i === state.events.length - 1}
                  />
                ))
              )}
            </div>

            <div className="px-5 py-2.5 border-t border-line bg-lab/40 text-[11px] text-muted font-mono flex flex-wrap items-center justify-between gap-2">
              <span>{state.message}</span>
              {runIds.length > 0 && (
                <a href="#/console" className="text-crimson hover:underline">
                  inspect in console →
                </a>
              )}
            </div>
          </div>
        </div>

        {/* Right: HUD */}
        <div className="lg:col-span-2 space-y-6">
          <div className="grid grid-cols-2 gap-3">
            <StatTile label="Events" value={counts.total} tone="ink" note={`${counts.insecure} insecure · ${counts.defended} defended`} />
            <StatTile label="Findings" value={counts.findings} tone="red" note="policy violations" />
            <StatTile label="Guards blocked" value={counts.blocked} tone="green" note="verified at boundary" />
            <StatTile
              label="Latency"
              value={state.latencyMs ?? 0}
              tone="ink"
              note={state.latencyMs != null ? 'ms · server-measured' : 'awaiting result'}
            />
          </div>

          {/* Findings */}
          <div
            className={`transition-all duration-500 ${
              state.findings.length > 0 ? 'opacity-100 translate-y-0' : 'opacity-45'
            }`}
          >
            <div className="panel panel-shadow overflow-hidden">
              <div className="px-5 py-3 border-b border-line bg-lab/50 flex items-center justify-between">
                <h2 className="text-sm font-semibold">Findings</h2>
                <Badge tone={state.findings.length > 0 ? 'red' : 'gray'}>
                  {state.findings.length}
                </Badge>
              </div>
              <div className="divide-y divide-line max-h-[220px] overflow-y-auto">
                {state.findings.length === 0 ? (
                  <div className="px-5 py-6 text-center text-[11px] text-muted">
                    Findings appear here as the analyzer reports them.
                  </div>
                ) : (
                  state.findings.map((v) => (
                    <div key={v.id} className="px-4 py-3 row-enter">
                      <div className="flex items-center gap-2">
                        <Badge tone={v.severity === 'critical' || v.severity === 'high' ? 'red' : 'amber'}>
                          {v.severity}
                        </Badge>
                        <span className="font-mono text-[10px] text-muted">{v.category}</span>
                      </div>
                      <div className="text-[13px] font-medium mt-1">{v.title}</div>
                      {v.root_cause && (
                        <p className="text-[11px] text-muted mt-1 leading-relaxed">
                          <span className="font-semibold text-crimson">Root cause:</span> {v.root_cause}
                        </p>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Defenses */}
          <div
            className={`transition-all duration-500 ${
              state.defenses.length > 0 ? 'opacity-100 translate-y-0' : 'opacity-45'
            }`}
          >
            <div className="panel panel-shadow overflow-hidden">
              <div className="px-5 py-3 border-b border-line bg-lab/50 flex items-center justify-between">
                <h2 className="text-sm font-semibold">Verified Defenses</h2>
                <Badge tone={counts.blocked > 0 ? 'green' : 'gray'}>{counts.blocked} blocked</Badge>
              </div>
              <div className="divide-y divide-line max-h-[220px] overflow-y-auto">
                {state.defenses.length === 0 ? (
                  <div className="px-5 py-6 text-center text-[11px] text-muted">
                    The defended re-run streams guards here.
                  </div>
                ) : (
                  state.defenses.map((d) => (
                    <div
                      key={d.defense.id}
                      className={`px-4 py-3 row-enter ${
                        d.verdict === 'blocked' ? 'bg-emerald-50/60' : 'bg-amber-50/60'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-[13px] font-medium">{d.defense.name}</span>
                        <Badge tone={d.verdict === 'blocked' ? 'green' : 'amber'}>{d.verdict}</Badge>
                      </div>
                      <p className="text-[11px] text-muted mt-1 leading-relaxed">{d.explanation}</p>
                      <p className="font-mono text-[10px] text-muted mt-1.5">
                        {d.defense.code_location}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Idle illustration */}
          {state.events.length === 0 && !running && (
            <Reveal>
              <div className="panel panel-shadow p-6 text-center">
                <LayerStack className="mb-2" />
                <p className="text-[11px] text-muted font-mono">
                  trace → findings → verified fixes
                </p>
              </div>
            </Reveal>
          )}
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-line py-8 mt-4">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-muted">
          <span>© 2026 RedOps · Live Stream</span>
          <span className="font-mono">
            Simulated environment · deterministic pipeline · no real purchases executed
          </span>
        </div>
      </footer>
    </div>
  );
}
