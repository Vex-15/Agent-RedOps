import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from 'react';

/**
 * Motion primitives shared by the landing page, the console and the live
 * stream.  All of them respect `prefers-reduced-motion`: the CSS in
 * index.css collapses the animations, and the tilt hook bails out, so the
 * pages stay fully usable without motion.
 */

const prefersReducedMotion = () =>
  typeof window !== 'undefined' &&
  window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// ── Reveal ──────────────────────────────────────────────────────────

type RevealTag = 'div' | 'section' | 'li' | 'span' | 'article';

export function Reveal({
  children,
  className = '',
  as = 'div',
  stagger = false,
  delay = 0,
  threshold = 0.14,
}: {
  children: ReactNode;
  className?: string;
  as?: RevealTag;
  stagger?: boolean;
  delay?: number;
  threshold?: number;
}) {
  const ref = useRef<HTMLElement | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    // No IntersectionObserver support (or reduced motion): show at once.
    if (prefersReducedMotion() || typeof IntersectionObserver === 'undefined') {
      setVisible(true);
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setVisible(true);
            io.disconnect();
          }
        }
      },
      { threshold, rootMargin: '0px 0px -6% 0px' },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [threshold]);

  const Tag = as as 'div';
  return (
    <Tag
      ref={ref as React.RefObject<HTMLDivElement>}
      className={`${stagger ? 'reveal-stagger' : 'reveal'}${visible ? ' is-visible' : ''} ${className}`}
      style={{ transitionDelay: delay ? `${delay}ms` : undefined }}
    >
      {children}
    </Tag>
  );
}

// ── Tilt ────────────────────────────────────────────────────────────

/**
 * Pointer-driven 3D tilt. The child is rendered inside a `.scene` wrapper
 * (which sets `perspective`), so the rotation reads as depth rather than a
 * flat skew. Tracking is rAF-throttled through state coalescing, and the
 * element eases back to flat on pointer-leave.
 */
export function Tilt({
  children,
  className = '',
  max = 9,
  scale = 1.015,
  glare = true,
}: {
  children: ReactNode;
  className?: string;
  max?: number;
  scale?: number;
  glare?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [transform, setTransform] = useState('');
  const [pointer, setPointer] = useState({ x: 50, y: 50 });
  const frame = useRef<number | null>(null);

  useEffect(
    () => () => {
      if (frame.current !== null) cancelAnimationFrame(frame.current);
    },
    [],
  );

  const onMove = (event: React.PointerEvent<HTMLDivElement>) => {
    if (prefersReducedMotion()) return;
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const px = (event.clientX - rect.left) / rect.width;
    const py = (event.clientY - rect.top) / rect.height;

    if (frame.current !== null) cancelAnimationFrame(frame.current);
    frame.current = requestAnimationFrame(() => {
      setPointer({ x: px * 100, y: py * 100 });
      setTransform(
        `rotateX(${((0.5 - py) * max).toFixed(2)}deg) rotateY(${((px - 0.5) * max).toFixed(
          2,
        )}deg) translateZ(0) scale3d(${scale}, ${scale}, ${scale})`,
      );
    });
  };

  const onLeave = () => {
    if (frame.current !== null) cancelAnimationFrame(frame.current);
    frame.current = requestAnimationFrame(() => setTransform(''));
  };

  const style: CSSProperties = glare
    ? {
        transform: transform || undefined,
        ['--glare-x' as string]: `${pointer.x}%`,
        ['--glare-y' as string]: `${pointer.y}%`,
      }
    : { transform: transform || undefined };

  return (
    <div className={`scene ${className}`}>
      <div
        ref={ref}
        onPointerMove={onMove}
        onPointerLeave={onLeave}
        className="tilt preserve-3d relative"
        style={style}
      >
        {children}
        {glare && (
          <span
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 rounded-[inherit] opacity-0 transition-opacity duration-500 group-hover:opacity-100"
            style={{
              background:
                'radial-gradient(420px circle at var(--glare-x, 50%) var(--glare-y, 50%), rgba(214,31,38,0.10), transparent 62%)',
            }}
          />
        )}
      </div>
    </div>
  );
}

// ── LayerStack ──────────────────────────────────────────────────────

/**
 * The floating 3D sheet stack used to illustrate analyze → find → fix.
 * Each sheet is a translucent plane pushed back in Z and drifting on its
 * own clock, so the stack reads as depth rather than overlapping divs.
 */
const STACK = [
  { label: 'TRACE', note: 'every agent decision', z: 0, x: 0, y: 0, rot: -6, tone: 'crimson' },
  { label: 'FIND', note: 'violations + root cause', z: -46, x: 26, y: 18, rot: -2, tone: 'crimsonSoft' },
  { label: 'FIX', note: 'verified code-level guards', z: -92, x: 52, y: 36, rot: 3, tone: 'ink' },
] as const;

export function LayerStack({ className = '' }: { className?: string }) {
  const toneClass: Record<string, string> = {
    crimson: 'bg-crimson/12 border-crimson/40 text-crimson',
    crimsonSoft: 'bg-crimson/7 border-crimson/30 text-crimson-dark',
    ink: 'bg-ink/7 border-ink/20 text-ink',
  };

  return (
    <div className={`scene ${className}`} aria-hidden="true">
      <div className="relative h-[340px] w-full max-w-[420px] mx-auto preserve-3d">
        {STACK.map((layer, i) => (
          <div
            key={layer.label}
            className={`absolute inset-x-0 top-8 mx-auto h-[220px] w-[76%] rounded-2xl border backdrop-blur-[1px] ${toneClass[layer.tone]} ${i === 1 ? 'float-slow' : i === 2 ? 'float-slower' : ''}`}
            style={{
              transform: `translate3d(${layer.x}px, ${layer.y}px, ${layer.z}px) rotateX(58deg) rotateZ(${layer.rot}deg)`,
            }}
          >
            <div className="h-full w-full rounded-2xl border border-white/40 bg-panel/45 p-5 flex flex-col justify-between">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[11px] font-semibold tracking-[0.22em]">
                  {layer.label}
                </span>
                <span className="w-2 h-2 rounded-full bg-current opacity-70" />
              </div>
              <span className="font-mono text-[10px] opacity-80">{layer.note}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
