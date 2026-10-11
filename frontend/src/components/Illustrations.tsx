/**
 * Faceted red shield emblem, rebuilt after the RedOps reference art:
 * a low-poly crest with a dark eye-slit, glowing eyes and a
 * sharp angular crown — layered back-to-front so it reads as a 3D asset.
 * The wrapper’s `.scene` (perspective) plus `Tilt` in Landing.tsx gives it depth.
 */
export function HeroShield({ className = '' }: { className?: string }) {
  return (
    <div className={`relative flex items-center justify-center ${className}`}>
      {/* soft halo */}
      <div className="absolute w-72 h-72 rounded-full bg-crimson/10 blur-3xl" />
      <div className="absolute w-96 h-96 rounded-full bg-crimson/5 blur-3xl" />

      <svg
        width="420"
        height="420"
        viewBox="0 0 320 320"
        fill="none"
        className="relative drop-shadow-2xl max-w-full h-auto"
      >
        <defs>
          <linearGradient id="shieldRed" x1="70" y1="60" x2="250" y2="250" gradientUnits="userSpaceOnUse">
            <stop stopColor="#ff3b42" />
            <stop offset="0.55" stopColor="#d61f26" />
            <stop offset="1" stopColor="#7c1d1d" />
          </linearGradient>
          <filter id="shieldGlow" x="-40%" y="-40%" width="180%" height="180%">
            <feGaussianBlur stdDeviation="7" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        <path d="M28 72h36M256 72h36M42 252h36M242 252h36M160 8v24M160 288v24" stroke="#d61f26" strokeOpacity=".2" strokeDasharray="2 8" />
        <path d="M38 72v180M282 72v180M48 62h224M48 262h224" stroke="#d61f26" strokeOpacity=".12" strokeDasharray="1 7" />
        {/* ── Back plate: widest shield silhouette (dark) ── */}
        <path d="M160 30 48 112l16 112 96 66 96-66 16-112z" fill="#300306" />

        {/* ── Mid shield (deep red) ── */}
        <path d="M160 48 64 116l-8 100 104 74 104-74-8-100z" fill="#7a0f14" />

        {/* ── Front shield (bright red) ── */}
        <path d="M160 58 80 120l-4 90 84 82 84-82-4-90z" fill="url(#shieldRed)" />

        {/* ── Crown facets (top edge) ── */}
        {/* crown outer (dark) */}
        <path d="M160 20 116 94l44-26 44 26z" fill="#3a0407" />
        <path d="m160 20 44 74-44-26-44 26z" fill="#5b0d12" />
        {/* crown center highlight */}
        <path d="M160 20 144 74l16-6z" fill="#8c1418" />
        <path d="m160 20 16 54-16-6z" fill="#a30f16" />

        {/* ── Shield facet lines ── */}
        <path d="M80 120 160 170l80-50M160 58v112M76 210l84 82 84-82" stroke="#5b0d12" strokeWidth="1.6" opacity="0.9" />

        {/* ── Face: dark inner mask ── */}
        <path d="M112 132 160 162l48-30 12 64-60 58-60-58z" fill="#260405" />

        {/* ── Glowing eyes (angled, sharp) ── */}
        {/* left eye */}
        <path d="m116 174 46-18-18 28z" fill="#ff5555" filter="url(#shieldGlow)" />
        {/* right eye */}
        <path d="m204 174-46-18 18 28z" fill="#ff5555" filter="url(#shieldGlow)" />
        {/* eye glow */}
        <path d="m116 174 46-18-18 28z" fill="#fff1f1" opacity="0.9" />
        <path d="m204 174-46-18 18 28z" fill="#fff1f1" opacity="0.9" />

        {/* ── Nose ridge (dark slit between eyes) ── */}
        <path d="m154 142 6 20 6-20 5 50-11 24-11-24z" fill="#1a0304" />

        {/* ── Lower beak (sharp angular chin) ── */}
        <path d="m149 216 11-26 11 26-11 50z" fill="#8c1418" />
        <path d="m160 190 11 26-11 50-11-50z" fill="#a30f16" />

        {/* ── Ambient light on cheekbones ── */}
        <path d="m104 196 34 20-10 30z" fill="#e0141f" opacity="0.7" />
        <path d="m216 216 34-20-24 50z" fill="#a30f16" opacity="0.9" />

        {/* ── Small accent glints ── */}
        <path d="M70 96 54 80 62 92z" fill="#ff5555" opacity="0.8" />
        <path d="M250 96 266 80 258 92z" fill="#ff5555" opacity="0.8" />
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

/** Layered translucent card stack — the "from vulnerability to resilience" graphic.
 *
 * Three overlapping planes rendered as short inline SVGs so the whole block can sit
 * inside one `.scene`/`.preserve-3d` wrapper and tilt consistently with the rest of the
 * page. Each plane carries its own drift so the stack reads as depth, not stacked divs.
 */
export function LayerPanels({ className = '' }: { className?: string }) {
  return (
    <div className={`relative flex items-center justify-center ${className}`} aria-hidden="true">
      <svg width="460" height="340" viewBox="0 0 460 340" fill="none" className="mx-auto max-w-full h-auto">
        <defs>
          <linearGradient id="layerRed" x1="0" y1="0" x2="1" y2="1">
            <stop stopColor="#ff4a50" stopOpacity=".95" />
            <stop offset="1" stopColor="#d61f26" stopOpacity=".65" />
          </linearGradient>
        </defs>
        <path d="M20 40v250M80 20v300M140 40v250M200 20v300M260 40v250M320 20v300M380 40v250M440 20v300" stroke="#d61f26" strokeOpacity=".08" strokeDasharray="2 10" />
        <path d="M20 70h420M20 140h420M20 210h420M20 280h420" stroke="#1a1d21" strokeOpacity=".06" strokeDasharray="1 8" />
        {/* back sheet: faint ink plane */}
        <g transform="translate(20,120) skewX(-10) scale(1,0.85)">
          <rect x="0" y="0" width="150" height="120" rx="14" fill="#1a1d21" opacity="0.18" stroke="#1a1d21" strokeOpacity=".25" />
          <text x="16" y="40" fill="#1a1d21" opacity="0.55" fontSize="11" fontFamily="monospace" letterSpacing="2">FIX</text>
          <text x="16" y="62" fill="#1a1d21" opacity="0.4" fontSize="9" fontFamily="monospace" letterSpacing="2">verified code-level guards</text>
        </g>

        {/* mid sheet: soft crimson plane */}
        <g transform="translate(105,92) skewX(-6) scale(1,0.82)">
          <rect x="0" y="0" width="158" height="132" rx="14" fill="#d61f26" opacity="0.22" stroke="#d61f26" strokeOpacity=".45" />
          <text x="16" y="46" fill="#a30f16" fontSize="12" fontFamily="monospace" letterSpacing="2" fontWeight="700">FIND</text>
          <text x="16" y="66" fill="#a30f16" opacity="0.75" fontSize="9" fontFamily="monospace" letterSpacing="2">violations + root cause</text>
          {/* little red accent dot, top-right */}
          <circle cx="142" cy="22" r="6" fill="#d61f26" />
        </g>

        {/* front sheet: bright crimson plane */}
        <g transform="translate(190,64) skewX(-2) scale(1,0.8) rotate(-4 82 72)">
          <rect x="0" y="0" width="164" height="144" rx="14" fill="url(#layerRed)" stroke="#ffffff" strokeOpacity=".6" />
          <text x="18" y="52" fill="#fff" fontSize="12" fontFamily="monospace" letterSpacing="2" fontWeight="700">FIND</text>
          <text x="18" y="72" fill="#fff" opacity="0.85" fontSize="9" fontFamily="monospace" letterSpacing="2">violations + root cause</text>
          <circle cx="146" cy="22" r="6" fill="#fff" opacity="0.85" />
        </g>

        {/* ambient tint behind the block */}
        <circle cx="170" cy="150" r="120" fill="#d61f26" opacity="0.06" />
      </svg>

      {/* scattered accent marks */}
      <span className="absolute top-6 right-14 w-3 h-3 bg-crimson" />
      <span className="absolute top-1/2 right-6 w-2 h-2 bg-crimson/80" />
      <span className="absolute bottom-24 left-10 w-2.5 h-2.5 bg-crimson/70" />
      <span className="absolute bottom-12 left-32 w-2 h-2 bg-ink/30" />
      <span className="absolute top-1/3 left-6 w-2 h-2 bg-crimson/40" />
      <span className="absolute bottom-1/3 right-14 w-2.5 h-2.5 bg-ink/20" />
    </div>
  );
}
