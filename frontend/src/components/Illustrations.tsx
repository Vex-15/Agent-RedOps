
/** Chunky shield over a soft crimson halo — the hero graphic. */
export function HeroShield({ className = '' }: { className?: string }) {
  return (
    <div className={`relative flex items-center justify-center ${className}`}>
      {/* halo */}
      <div className="absolute w-72 h-72 rounded-full bg-crimson/10 blur-3xl" />
      <div className="absolute w-96 h-96 rounded-full bg-crimson/5 blur-3xl" />

      <svg width="260" height="260" viewBox="0 0 260 260" fill="none" className="relative drop-shadow-2xl">
        {/* back shield plate */}
        <path d="M70 60 130 30l60 30-4 92-56 34-56-34z" fill="#7c1d1d" />
        {/* mid shield */}
        <path d="M78 58 130 34l52 24-4 84-48 30-48-30z" fill="#a30f16" />
        {/* front shield */}
        <path d="M86 56 130 38l44 18-4 76-40 26-40-26z" fill="#d61f26" />
        {/* face slit */}
        <path d="M104 96q8-10 26-10t26 10q-6 10-26 10t-26-10z" fill="#fff" />
        <path d="M96 112q10 12 34 12t34-12q-4 16-34 16t-34-16z" fill="#7c1d1d" />
      </svg>

      {/* floating deco blocks */}
      <span className="absolute top-6 right-16 w-3 h-3 bg-crimson" />
      <span className="absolute bottom-16 left-8 w-2.5 h-2.5 bg-crimson/70" />
      <span className="absolute bottom-8 right-24 w-2 h-2 bg-ink/30" />
      <span className="absolute top-1/3 left-4 w-2 h-2 bg-crimson/40" />
    </div>
  );
}

/** Layered translucent panels — the "from vulnerability to resilience" graphic. */
export function LayerPanels({ className = '' }: { className?: string }) {
  const panels = [
    { x: 0, fill: '#d61f26', opacity: 0.9 },
    { x: 28, fill: '#e35d61', opacity: 0.6 },
    { x: 56, fill: '#f0a4a6', opacity: 0.45 },
    { x: 84, fill: '#c9c9c9', opacity: 0.5 },
    { x: 112, fill: '#8a8a8a', opacity: 0.55 },
  ];
  return (
    <div className={`relative flex items-center justify-center ${className}`}>
      <svg width="360" height="300" viewBox="0 0 360 300" fill="none">
        <g transform="translate(40,30) skewY(-8)">
          {panels.map((p, i) => (
            <rect
              key={i}
              x={p.x}
              y={0}
              width={72}
              height={210}
              rx={4}
              fill={p.fill}
              opacity={p.opacity}
              stroke="rgba(255,255,255,0.55)"
            />
          ))}
        </g>
      </svg>
      <span className="absolute top-4 right-10 w-2.5 h-2.5 bg-crimson" />
      <span className="absolute bottom-8 left-6 w-2 h-2 bg-crimson/50" />
    </div>
  );
}
