import { useCallback, useEffect, useState } from 'react';
import Logo from './components/Logo';
import {
  getScenarios,
  getRuns,
  getRunDetail,
  runScenario,
  runAllScenarios,
  getDashboardMetrics,
  type ScenarioItem,
  type RunItem,
  type RunDetail,
  type DashboardMetrics,
} from './lib/api';

// ── Small UI atoms ─────────────────────────────────────────────────────
function Badge({ tone, children }: { tone: 'red' | 'green' | 'amber' | 'gray'; children: React.ReactNode }) {
  const tones = {
    red: 'bg-crimson-faint text-crimson border-crimson/25',
    green: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    amber: 'bg-amber-50 text-amber-700 border-amber-200',
    gray: 'bg-lab text-muted border-line',
  } as const;
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-[11px] font-mono font-medium border ${tones[tone]}`}>
      {children}
    </span>
  );
}

function MetricCard({ label, value, note, tone = 'ink' }: { label: string; value: string | number; note: string; tone?: 'ink' | 'red' | 'green' | 'amber' }) {
  const toneClass = { ink: 'text-ink', red: 'text-crimson', green: 'text-emerald-600', amber: 'text-amber-600' }[tone];
  return (
    <div className="panel panel-shadow p-5">
      <div className="text-[11px] font-semibold uppercase tracking-wider text-muted">{label}</div>
      <div className={`text-2xl font-bold mt-1 tabular-nums ${toneClass}`}>{value}</div>
      <div className="text-xs text-muted mt-2">{note}</div>
    </div>
  );
}

export default function Dashboard() {
  const [scenarios, setScenarios] = useState<ScenarioItem[]>([]);
  const [runs, setRuns] = useState<RunItem[]>([]);
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [detail, setDetail] = useState<RunDetail | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [live, setLive] = useState<boolean | null>(null);

  const refresh = useCallback(async () => {
    const [sc, rn, mt] = await Promise.all([getScenarios(), getRuns(), getDashboardMetrics()]);
    setScenarios(sc.data);
    setRuns(rn.data);
    setMetrics(mt.data);
    setLive(sc.live && rn.live && mt.live);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const loadDetail = async (runId: string | null) => {
    setSelectedRunId(runId);
    setDetail(null);
    if (!runId) return;
    const res = await getRunDetail(runId);
    setDetail(res.data);
  };

  const execute = async (scenarioId: number) => {
    setBusyId(scenarioId);
    const res = await runScenario(scenarioId);
    if (res && typeof res.run_id === 'string') await loadDetail(res.run_id);
    await refresh();
    setBusyId(null);
  };

  const executeAll = async () => {
    await runAllScenarios();
    await refresh();
  };

  const selectedRun = runs.find((r) => r.run_id === selectedRunId) ?? null;
  const isBusy = busyId !== null;

  return (
    <div className="min-h-screen bg-paper text-ink">
      {/* ── Top bar ── */}
      <header className="sticky top-0 z-30 bg-paper/85 backdrop-blur border-b border-line">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <Logo />
          <div className="flex items-center gap-3">
            <span className="text-[11px] font-mono px-2 py-0.5 rounded border border-line bg-panel text-muted">
              v0.2.0-pipeline
            </span>
            <span
              className={`text-[11px] font-mono px-2 py-0.5 rounded border ${
                live === null
                  ? 'border-line bg-panel text-muted'
                  : live
                    ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                    : 'border-crimson/25 bg-crimson-faint text-crimson'
              }`}
            >
              {live === null ? 'connecting…' : live ? 'backend live' : 'demo mode'}
            </span>
            <button onClick={executeAll} className="btn-primary !py-1.5 !px-4 text-[13px]">
              <span>▶</span> Run All Scenarios
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* ── Title ── */}
        <div className="mb-8">
          <div className="eyebrow mb-2">Defensive multi-agent security evaluation</div>
          <h1 className="font-display text-3xl sm:text-4xl">
            AGENT <span className="text-crimson">CONSOLE</span>
          </h1>
          <p className="text-muted text-sm mt-3 max-w-xl">
            Run scenarios against the simulated requester → vendor → approver → purchaser pipeline, inspect deception
            traces, and verify guards neutralize every attack path.
          </p>
        </div>

        {/* ── Metrics ── */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
          <MetricCard label="Active Scenarios" value={scenarios.length} note="Deterministic multi-agent cases" />
          <MetricCard
            label="Total Violations"
            value={metrics?.total_violations ?? '—'}
            note="Detected across all runs"
            tone="red"
          />
          <MetricCard
            label="Blocked by Defense"
            value={metrics?.blocked_by_defense ?? '—'}
            note="Guards verified at trust boundaries"
            tone="green"
          />
          <MetricCard
            label="Avg Latency"
            value={metrics ? `${metrics.avg_latency_ms.toFixed(1)} ms` : '—'}
            note="Local deterministic execution"
          />
        </div>

        {/* ── Main grid ── */}
        <div className="grid lg:grid-cols-5 gap-6">
          {/* Left column */}
          <div className="lg:col-span-3 space-y-6">
            {/* Scenarios */}
            <section className="panel panel-shadow overflow-hidden">
              <div className="px-5 py-3.5 border-b border-line flex items-center justify-between bg-lab/50">
                <h2 className="text-sm font-semibold">Security Scenarios</h2>
                <span className="font-mono text-[11px] text-muted">Requester → Vendor → Approver → Purchaser</span>
              </div>
              <div className="divide-y divide-line">
                {scenarios.map((sc) => (
                  <div key={sc.id} className="px-5 py-4 hover:bg-crimson-faint/40 transition-colors">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-mono text-[11px] px-2 py-0.5 rounded border border-line bg-lab text-muted">
                            SC-0{sc.id}
                          </span>
                          <h3 className="font-medium text-sm">{sc.name}</h3>
                        </div>
                        <p className="text-muted text-[13px] mt-1">{sc.description}</p>
                        <div className="flex flex-wrap gap-1.5 mt-2.5">
                          {sc.expected_violations.length > 0 ? (
                            sc.expected_violations.map((v) => (
                              <Badge key={v} tone="red">
                                {v}
                              </Badge>
                            ))
                          ) : (
                            <Badge tone="green">Positive Baseline</Badge>
                          )}
                        </div>
                      </div>
                      <button
                        onClick={() => execute(sc.id)}
                        disabled={isBusy}
                        className="btn-secondary !py-1.5 !px-3 text-xs whitespace-nowrap disabled:opacity-50"
                      >
                        {busyId === sc.id ? 'Running…' : 'Run Test'}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            {/* Runs table */}
            <section className="panel panel-shadow overflow-hidden">
              <div className="px-5 py-3.5 border-b border-line bg-lab/50">
                <h2 className="text-sm font-semibold">Recent Execution Runs</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="text-[11px] uppercase tracking-wider text-muted border-b border-line">
                    <tr>
                      <th className="px-5 py-2.5 font-mono">Run ID</th>
                      <th className="px-5 py-2.5">Scenario</th>
                      <th className="px-5 py-2.5">Violations</th>
                      <th className="px-5 py-2.5">Attack Paths</th>
                      <th className="px-5 py-2.5">Defense</th>
                      <th className="px-5 py-2.5">Latency</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {runs.map((r) => (
                      <tr
                        key={r.run_id}
                        onClick={() => loadDetail(r.run_id)}
                        className={`cursor-pointer transition-colors ${
                          selectedRunId === r.run_id ? 'bg-crimson-faint/60' : 'hover:bg-lab/60'
                        }`}
                      >
                        <td className="px-5 py-3 font-mono text-xs text-crimson">{r.run_id}</td>
                        <td className="px-5 py-3 font-medium text-[13px]">{r.scenario_name}</td>
                        <td className="px-5 py-3 tabular-nums">
                          {r.violation_count > 0 ? <span className="text-crimson font-semibold">{r.violation_count}</span> : <span className="text-muted">0</span>}
                        </td>
                        <td className="px-5 py-3 tabular-nums">
                          {r.attack_path_count > 0 ? <span className="text-amber-600 font-semibold">{r.attack_path_count}</span> : <span className="text-muted">None</span>}
                        </td>
                        <td className="px-5 py-3">
                          <Badge tone={r.defense_verdict === 'all_blocked' ? 'green' : r.defense_verdict === 'some_bypassed' ? 'amber' : 'gray'}>
                            {r.defense_verdict ?? 'clean'}
                          </Badge>
                        </td>
                        <td className="px-5 py-3 text-muted tabular-nums text-[13px]">{r.latency_ms} ms</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </div>

          {/* Right column: inspector */}
          <div className="lg:col-span-2">
            <section className="panel panel-shadow p-5 lg:sticky lg:top-20">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-semibold">Attack Path & Defense Trace</h2>
                <span className="font-mono text-[11px] text-muted">{selectedRun?.run_id ?? 'select a run'}</span>
              </div>

              {selectedRun || detail ? (
                <div className="space-y-5">
                  <div className="bg-lab border border-line rounded-lg p-3.5 text-xs">
                    <div className="text-muted font-semibold uppercase tracking-wide text-[10px]">Scenario</div>
                    <div className="font-medium mt-0.5">{detail?.scenario_name ?? selectedRun?.scenario_name}</div>
                    <div className="text-muted mt-2 flex gap-4">
                      <span>
                        Violations <b className="text-crimson">{detail?.violations.length ?? selectedRun?.violation_count ?? 0}</b>
                      </span>
                      <span>
                        Attack paths <b className="text-amber-600">{detail?.attack_paths.length ?? selectedRun?.attack_path_count ?? 0}</b>
                      </span>
                    </div>
                  </div>

                  {/* Timeline of trace events */}
                  {detail && (
                    <div>
                      <div className="text-[10px] font-semibold text-muted uppercase tracking-wider mb-2.5">
                        Deception Flow
                      </div>
                      <div className="relative space-y-3">
                        <span className="absolute left-[5px] top-2 bottom-2 w-px bg-line-strong" />
                        {detail.trace.slice(0, 8).map((ev) => {
                          const untrusted = !ev.trusted;
                          return (
                            <div key={ev.id} className="relative pl-5">
                              <span
                                className={`absolute left-0 top-1 w-[11px] h-[11px] rounded-full border-2 border-paper ${
                                  untrusted ? 'bg-crimson' : 'bg-emerald-500'
                                }`}
                              />
                              <div className="flex items-baseline gap-2">
                                <span className="font-mono text-[10px] text-muted shrink-0">{ev.timestamp}</span>
                                <span className={`text-xs font-medium ${untrusted ? 'text-crimson' : 'text-ink'}`}>
                                  {ev.action}
                                </span>
                              </div>
                              <div className="text-[11px] text-muted">
                                {ev.agent} · {ev.kind}
                                {untrusted && <span className="text-crimson font-medium untrusted-flag"> · untrusted</span>}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Violation */}
                  {detail?.violations[0] && (
                    <div className="border border-crimson/25 bg-crimson-faint/60 rounded-lg p-3.5">
                      <div className="text-[10px] font-semibold uppercase tracking-wider text-crimson mb-1">
                        Detected Violation
                      </div>
                      <div className="text-sm font-medium">{detail.violations[0].title}</div>
                      <p className="text-[12px] text-muted mt-1 leading-relaxed">{detail.violations[0].description}</p>
                      {detail.violations[0].root_cause && (
                        <p className="text-[12px] mt-2">
                          <span className="font-semibold text-crimson">Root cause:</span>{' '}
                          <span className="text-muted">{detail.violations[0].root_cause}</span>
                        </p>
                      )}
                    </div>
                  )}

                  {/* Defense */}
                  {detail?.defenses[0] && (
                    <div className="border-t border-line pt-4">
                      <div className="text-[10px] font-semibold text-emerald-700 uppercase tracking-wider mb-2">
                        Verified Defense
                      </div>
                      <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs">
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-semibold text-emerald-800">{detail.defenses[0].defense.name}</span>
                          <Badge tone="green">{detail.defenses[0].verdict}</Badge>
                        </div>
                        <p className="text-muted mt-1.5 leading-relaxed">{detail.defenses[0].explanation}</p>
                        <p className="font-mono text-[10px] text-muted mt-2">{detail.defenses[0].defense.code_location}</p>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-12 text-muted text-sm">
                  Select a scenario execution or run to inspect the detailed attack path and verify defense behavior.
                </div>
              )}
            </section>
          </div>
        </div>
      </div>

      {/* ── Footer ── */}
      <footer className="border-t border-line py-5">
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between text-xs text-muted">
          <span>© 2026 RedOps · Agent Console</span>
          <span className="font-mono">Simulated environment · no real purchases executed</span>
        </div>
      </footer>
    </div>
  );
}
