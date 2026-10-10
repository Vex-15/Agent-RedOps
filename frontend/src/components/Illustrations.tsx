/**
 * Angular hooded-face mask, rebuilt after the RedOps reference art:
 * a faceted crimson cloak with a dark eye-slit, glowing eyes and a
 * sharp lower beak — layered from dark back plate to bright front
 * so it reads as a 3D low-poly asset rather than a blob.
 */
export function HeroShield({ className = '' }: { className?: string }) {
  return (
    <div className={`relative flex items-center justify-center ${className}`}>
      {/* soft halo */}
      <div className="absolute w-72 h-72 rounded-full bg-crimson/10 blur-3xl" />
      <div className="absolute w-96 h-96 rounded-full bg-crimson/5 blur-3xl" />

      <svg
        width="320"
        height="320"
        viewBox="0 0 320 320"
        fill="none"
        className="relative drop-shadow-2xl"
      >
        {/* ── Back plate: widest cloak silhouette (dark) ── */}
        <path d="M64 96 160 44l96 52-12 130-84 42-84-42z" fill="#5b0d12" />

        {/* ── Mid cloak (deep red) ── */}
        <path d="M78 100 160 56l82 44-10 120-72 36-72-36z" fill="#8c1418" />

        {/* ── Front cloak (bright red) ── */}
        <path d="M92 104 160 68l68 36-8 108-60 30-60-30z" fill="#c4101a" />

        {/* ── Hood facets (top) ── */}
        {/* left hood slope */}
        <path d="M92 104 160 44l-16 60z" fill="#e0141f" />
        {/* right hood slope */}
        <path d="M228 104 160 44l16 60z" fill="#a30f16" />
        {/* hood ridge highlight */}
        <path d="M160 44l-16 60 16 14 16-14z" fill="#ff2222" />

        {/* ── Hood drape covering the brow ── */}
        {/* left drape */}
        <path d="M104 128c14-10 38-14 56-14l-24 38c-14-2-26-10-32-24z" fill="#7a1015" />
        {/* right drape */}
        <path d="M216 128c-14-10-38-14-56-14l24 38c14-2 26-10 32-24z" fill="#8c1418" />

        {/* ── Face: dark inner mask ── */}
        <path d="M128 122h64l10 56-42 44-42-44z" fill="#3a0708" />

        {/* ── Glowing eyes (angled, sharp) ── */}
        {/* left eye */}
        <path d="M136 148l22-8-4 16z" fill="#ff5555" />
        {/* right eye */}
        <path d="M184 148l-22-8 4 16z" fill="#ff5555" />
        {/* eye glow */}
        <path d="M136 148l22-8-4 16z" fill="#ffb3b3" opacity="0.7" />
        <path d="M184 148l-22-8 4 16z" fill="#ffb3b3" opacity="0.7" />

        {/* ── Nose ridge (dark slit between eyes) ── */}
        <path d="M158 132h8l4 34-8 10-8-10z" fill="#2b0505" />

        {/* ── Lower beak (sharp angular chin) ── */}
        <path d="M150 190l10-14 10 14-10 32z" fill="#8c1418" />
        <path d="M160 176l10 14-10 32-10-32z" fill="#a30f16" />

        {/* ── Ambient light on cheekbones ── */}
        <path d="M122 176l14 12-2 12z" fill="#e0141f" opacity="0.6" />
        <path d="M198 176l-14 12 2 12z" fill="#a30f16" opacity="0.8" />
      </svg>

      {/* floating deco blocks */}
      <span className="absolute top-8 right-16 w-3 h-3 bg-crimson" />
      <span className="absolute top-1/2 right-8 w-2 h-2 bg-crimson/80" />
      <span className="absolute bottom-20 left-8 w-2.5 h-2.5 bg-crimson/70" />
      <span className="absolute bottom-10 left-24 w-2 h-2 bg-ink/30" />
      <span className="absolute top-1/3 left-4 w-2 h-2 bg-crimson/40" />
      <span className="absolute bottom-1/3 right-12 w-2.5 h-2.5 bg-ink/20" />
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
