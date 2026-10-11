/**
 * API client for the RedOps backend (FastAPI at /api).
 *
 * When the backend is reachable, everything is live. When it is not, the
 * client falls back to demo data captured from the real pipeline (see
 * backend/scripts_gen_demo_data.py) and simulates scenario execution
 * locally, so the console stays usable as a standalone showcase.
 *
 * Every response carries a `live` flag so the UI can tell the user which
 * mode it is in. The demo module is imported lazily (code-split), so it
 * never weighs down the bundle when the API is up.
 */

export interface ScenarioItem {
  id: number;
  name: string;
  description: string;
  tool_overrides: Record<string, unknown>;
  expected_violations: string[];
  expected_outcome: string;
}

export interface RunItem {
  id: number;
  run_id: string;
  scenario_name: string;
  status: string;
  error: string;
  violation_count: number;
  attack_path_count: number;
  defense_verdict: string | null;
  latency_ms: number;
  started_at: string;
  finished_at: string;
}

export interface TraceEvent {
  id: string;
  timestamp: string;
  agent: string;
  kind: string;
  action: string;
  input_data: Record<string, unknown>;
  output_data: Record<string, unknown>;
  metadata: Record<string, unknown>;
  trusted: boolean;
  unverified_source?: boolean;
}

export interface Violation {
  id: string;
  category: string;
  severity: string;
  title: string;
  description: string;
  evidence_event_ids: string[];
  root_cause: string;
}

export interface AttackPath {
  id: string;
  events: TraceEvent[];
  violation: Violation | null;
  entry_point: string;
  impact: string;
  length: number;
}

export interface DefenseResult {
  defense: {
    id: string;
    name: string;
    description: string;
    code_location: string;
    fix_description: string;
    category: string;
  };
  verdict: string;
  violation_before: Violation | null;
  violation_after: Violation | null;
  explanation: string;
}

export interface RunDetail {
  id: number;
  run_id: string;
  scenario_name: string;
  status: string;
  error: string;
  trace: TraceEvent[];
  violations: Violation[];
  attack_paths: AttackPath[];
  defenses: DefenseResult[];
  latency_ms: number;
  started_at: string;
  finished_at: string;
}

export interface DashboardMetrics {
  total_scenarios: number;
  total_runs: number;
  total_violations: number;
  blocked_by_defense: number;
  bypassed_defense: number;
  avg_latency_ms: number;
  scenarios_by_outcome: Record<string, number>;
  violations_by_category: Record<string, number>;
  violations_by_severity: Record<string, number>;
}

const BASE = '/api';

async function call<T>(path: string, init?: RequestInit): Promise<T | null> {
  try {
    const res = await fetch(`${BASE}${path}`, init);
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

// ── Demo-mode store ──────────────────────────────────────────────────
// Loaded on first fallback, then kept in memory so simulated runs
// accumulate exactly like live ones.

interface DemoStore {
  scenarios: ScenarioItem[];
  runs: RunItem[];
  details: Record<string, RunDetail>;
  metrics: DashboardMetrics;
}

let demoStore: DemoStore | null = null;

async function demo(): Promise<DemoStore> {
  if (!demoStore) {
    const mod = await import('./demoData');
    demoStore = {
      scenarios: [...mod.DEMO_SCENARIOS],
      runs: [...mod.DEMO_RUNS],
      details: { ...mod.DEMO_RUN_DETAILS },
      metrics: { ...mod.DEMO_METRICS },
    };
  }
  return demoStore;
}

function defenseVerdict(defenses: DefenseResult[]): string | null {
  const verdicts = defenses.map((d) => d.verdict);
  if (verdicts.length === 0) return null;
  if (verdicts.every((v) => v === 'blocked')) return 'all_blocked';
  if (verdicts.some((v) => v === 'bypassed')) return 'some_bypassed';
  return verdicts[0];
}

function recomputeDemoMetrics(store: DemoStore): DashboardMetrics {
  const byOutcome: Record<string, number> = {};
  const byCategory: Record<string, number> = {};
  const bySeverity: Record<string, number> = {};
  let totalViolations = 0;
  let blocked = 0;
  let bypassed = 0;
  let latencyTotal = 0;

  for (const run of store.runs) {
    const detail = store.details[run.run_id];
    if (!detail) continue;
    const violations = detail.violations;
    totalViolations += violations.length;
    latencyTotal += run.latency_ms;

    for (const v of violations) {
      byCategory[v.category] = (byCategory[v.category] ?? 0) + 1;
      bySeverity[v.severity] = (bySeverity[v.severity] ?? 0) + 1;
    }
    for (const d of detail.defenses) {
      if (d.verdict === 'blocked') blocked += 1;
      else if (d.verdict === 'bypassed') bypassed += 1;
    }

    const outcome =
      violations.length === 0
        ? 'clean'
        : detail.defenses.length > 0 && detail.defenses.every((d) => d.verdict === 'blocked')
          ? 'defended'
          : 'vulnerable';
    byOutcome[outcome] = (byOutcome[outcome] ?? 0) + 1;
  }

  return {
    total_scenarios: store.scenarios.length,
    total_runs: store.runs.length,
    total_violations: totalViolations,
    blocked_by_defense: blocked,
    bypassed_defense: bypassed,
    avg_latency_ms:
      Math.round((latencyTotal / Math.max(store.runs.length, 1)) * 10) / 10,
    scenarios_by_outcome: byOutcome,
    violations_by_category: byCategory,
    violations_by_severity: bySeverity,
  };
}

/**
 * Simulate executing a scenario offline: clone the captured run for that
 * scenario under a fresh run id so the inspector, metrics and history all
 * behave the way they do against the live API.
 */
function recordDemoRun(store: DemoStore, scenario: ScenarioItem): RunItem {
  const now = new Date().toISOString();
  const id = Math.max(0, ...store.runs.map((r) => r.id)) + 1;
  const runId = `DEMO-${id.toString(16).toUpperCase().padStart(6, '0')}`;
  const templateRun = store.runs.find((r) => r.scenario_name === scenario.name);
  const template = templateRun ? store.details[templateRun.run_id] : null;
  const latency = 1 + Math.floor(Math.random() * 12);

  // Preserve the captured run's status: re-running the failure-and-recovery
  // scenario offline fails again, exactly like the live pipeline.
  const detail: RunDetail = template
    ? { ...template, id, run_id: runId, latency_ms: latency, started_at: now, finished_at: now }
    : {
        id,
        run_id: runId,
        scenario_name: scenario.name,
        status: 'completed',
        error: '',
        trace: [],
        violations: [],
        attack_paths: [],
        defenses: [],
        latency_ms: latency,
        started_at: now,
        finished_at: now,
      };

  store.details[runId] = detail;

  const run: RunItem = {
    id,
    run_id: runId,
    scenario_name: scenario.name,
    status: detail.status,
    error: detail.error ?? '',
    violation_count: detail.violations.length,
    attack_path_count: detail.attack_paths.length,
    defense_verdict: defenseVerdict(detail.defenses),
    latency_ms: latency,
    started_at: now,
    finished_at: now,
  };

  store.runs = [run, ...store.runs];
  store.metrics = recomputeDemoMetrics(store);
  return run;
}

// ── Public API (backend first, demo fallback) ────────────────────────

export async function getScenarios(): Promise<{ data: ScenarioItem[]; live: boolean }> {
  const data = await call<ScenarioItem[]>('/scenarios');
  if (data) return { data, live: true };
  return { data: (await demo()).scenarios, live: false };
}

export async function getRuns(): Promise<{ data: RunItem[]; live: boolean }> {
  const data = await call<RunItem[]>('/runs');
  if (data) return { data, live: true };
  return { data: (await demo()).runs, live: false };
}

export async function getRunDetail(runId: string): Promise<{ data: RunDetail; live: boolean }> {
  const data = await call<RunDetail>(`/runs/${runId}`);
  if (data) return { data, live: true };
  const detail = (await demo()).details[runId];
  if (detail) return { data: detail, live: false };
  const store = await demo();
  const first = Object.values(store.details)[0];
  return { data: first, live: false };
}

export async function runScenario(scenarioId: number): Promise<Record<string, unknown> | null> {
  const live = await call<Record<string, unknown>>(`/runs/execute/${scenarioId}`, {
    method: 'POST',
  });
  if (live) return live;

  // Demo mode: simulate deterministic execution time, then record the run.
  const store = await demo();
  const scenario = store.scenarios.find((s) => s.id === scenarioId);
  if (!scenario) return null;
  await sleep(700 + Math.random() * 500);
  const run = recordDemoRun(store, scenario);
  return { ...run };
}

export async function runAllScenarios(): Promise<Record<string, unknown> | null> {
  const live = await call<Record<string, unknown>>('/runs/execute-all', { method: 'POST' });
  if (live) return live;

  const store = await demo();
  await sleep(1200);
  const runs = store.scenarios.map((s) => recordDemoRun(store, s));
  return { runs, total: runs.length };
}

export async function getDashboardMetrics(): Promise<{ data: DashboardMetrics; live: boolean }> {
  const data = await call<DashboardMetrics>('/dashboard');
  if (data) return { data, live: true };
  return { data: (await demo()).metrics, live: false };
}

// ── Live execution stream ───────────────────────────────────────────
//
// The backend streams a run as newline-delimited JSON: one message per
// trace event as the pipeline produces it, plus phase/finding/defense/
// result markers.  We read the fetch body incrementally so the console
// renders the attack while it happens rather than after it finishes.

export interface StreamMessage {
  type: 'phase' | 'event' | 'finding' | 'defense' | 'scenario' | 'result' | 'error';
  /** phase tag for `event` messages, and the phase name for `phase` messages */
  phase?: string;
  message?: string;
  event?: TraceEvent;
  violation?: Violation;
  defense?: DefenseResult;
  /** `scenario` marker fields */
  index?: number;
  total?: number;
  name?: string;
  /** `result` summary fields */
  run_id?: string;
  scenario_name?: string;
  status?: string;
  error?: string;
  latency_ms?: number;
  violation_count?: number;
  attack_path_count?: number;
  defense_verdict?: string | null;
}

interface StreamOutcome {
  runIds: string[];
  /** false when the API could not be streamed (offline / demo mode) */
  ok: boolean;
}

async function readStream(
  path: string,
  onMessage: (msg: StreamMessage) => void,
  signal?: AbortSignal,
): Promise<StreamOutcome> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { method: 'POST', signal });
  } catch {
    return { runIds: [], ok: false };
  }
  if (!res.ok || !res.body) return { runIds: [], ok: false };

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  const runIds: string[] = [];
  let buffer = '';

  const handle = (line: string) => {
    if (!line) return;
    let msg: StreamMessage;
    try {
      msg = JSON.parse(line) as StreamMessage;
    } catch {
      return;
    }
    if (msg.type === 'result' && msg.run_id) runIds.push(msg.run_id);
    onMessage(msg);
  };

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let newline: number;
      while ((newline = buffer.indexOf('\n')) >= 0) {
        handle(buffer.slice(0, newline).trim());
        buffer = buffer.slice(newline + 1);
      }
    }
  } catch {
    // Aborted by the caller, or the connection dropped mid-stream.
    // Return whatever we managed to receive — `ok` still marks that the
    // API answered, so callers don't fall back to demo data.
  }
  handle(buffer.trim());

  return { runIds, ok: true };
}

/**
 * Stream one scenario's execution.  Returns the run id so the caller can
 * load full detail, or null when the backend is unreachable so the UI can
 * fall back to the simulated demo run.
 */
export async function streamScenarioRun(
  scenarioId: number,
  onMessage: (msg: StreamMessage) => void,
  delayMs = 60,
  signal?: AbortSignal,
): Promise<StreamOutcome> {
  return readStream(`/runs/stream/${scenarioId}?delay_ms=${delayMs}`, onMessage, signal);
}

/** Stream every scenario in sequence, tagged with a `scenario` marker. */
export async function streamAllRuns(
  onMessage: (msg: StreamMessage) => void,
  delayMs = 15,
  signal?: AbortSignal,
): Promise<StreamOutcome> {
  return readStream(`/runs/stream-all?delay_ms=${delayMs}`, onMessage, signal);
}
