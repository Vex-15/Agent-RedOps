import type { ReactNode } from 'react';

/**
 * Shared badge atoms.  The console and the live page render the same
 * status vocabulary, so it lives in one place and can't drift.
 */

export function Badge({
  tone,
  children,
}: {
  tone: 'red' | 'green' | 'amber' | 'gray';
  children: ReactNode;
}) {
  const tones = {
    red: 'bg-crimson-faint text-crimson border-crimson/25',
    green: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    amber: 'bg-amber-50 text-amber-700 border-amber-200',
    gray: 'bg-lab text-muted border-line',
  } as const;
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded text-[11px] font-mono font-medium border ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const s = (status || '').toLowerCase();
  if (s === 'failed') return <Badge tone="red">failed</Badge>;
  if (s === 'completed') return <Badge tone="green">completed</Badge>;
  if (s === 'running') return <Badge tone="amber">running</Badge>;
  return <Badge tone="gray">{status || 'unknown'}</Badge>;
}
