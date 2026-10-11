import type { DefenseResult, StreamMessage, TraceEvent, Violation } from './api';

/**
 * Shared live-stream state machine.
 *
 * Built incrementally from the NDJSON stream so a page can render the
 * attack as it executes.  A `scenario` marker resets the buffer, which is
 * what lets a batch stream push every scenario through the same view.
 *
 * Used by both the console inspector and the dedicated live page, so the
 * two never drift apart in how they interpret the stream.
 */

export interface LiveState {
  scenarioName: string;
  phase: string;
  message: string;
  events: { event: TraceEvent; phase: string }[];
  findings: Violation[];
  defenses: DefenseResult[];
  runIds: string[];
  /** latency of the most recently completed run, in ms */
  latencyMs: number | null;
  index?: number;
  total?: number;
  errored: boolean;
}

export const EMPTY_LIVE: LiveState = {
  scenarioName: '',
  phase: 'start',
  message: 'Connecting to the pipeline…',
  events: [],
  findings: [],
  defenses: [],
  runIds: [],
  latencyMs: null,
  errored: false,
};

export const PHASE_LABEL: Record<string, string> = {
  start: 'connecting',
  insecure: 'insecure pipeline',
  analyze: 'analyzing',
  defend: 'defense verification',
  done: 'complete',
};

export function applyStreamMsg(prev: LiveState, msg: StreamMessage): LiveState {
  switch (msg.type) {
    case 'scenario':
      return {
        ...EMPTY_LIVE,
        scenarioName: msg.name ?? '',
        index: msg.index,
        total: msg.total,
        message: `Running ${msg.name ?? 'scenario'}…`,
      };
    case 'phase':
      return { ...prev, phase: msg.phase ?? prev.phase, message: msg.message ?? prev.message };
    case 'event':
      return msg.event
        ? { ...prev, events: [...prev.events, { event: msg.event, phase: msg.phase ?? 'insecure' }] }
        : prev;
    case 'finding':
      return msg.violation ? { ...prev, findings: [...prev.findings, msg.violation] } : prev;
    case 'defense':
      return msg.defense ? { ...prev, defenses: [...prev.defenses, msg.defense] } : prev;
    case 'result':
      return {
        ...prev,
        phase: 'done',
        message: 'Run complete — persisted and ready to inspect.',
        runIds: msg.run_id ? [...prev.runIds, msg.run_id] : prev.runIds,
        latencyMs: msg.latency_ms ?? prev.latencyMs,
      };
    case 'error':
      return { ...prev, errored: true, message: msg.message ?? 'Stream error' };
    default:
      return prev;
  }
}

/** Convenience counters for the live HUD. */
export function liveCounts(state: LiveState) {
  const insecure = state.events.filter((e) => e.phase === 'insecure').length;
  return {
    total: state.events.length,
    insecure,
    defended: state.events.length - insecure,
    findings: state.findings.length,
    blocked: state.defenses.filter((d) => d.verdict === 'blocked').length,
    bypassed: state.defenses.filter((d) => d.verdict !== 'blocked').length,
  };
}
