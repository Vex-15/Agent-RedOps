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
        width="320"
        height="320"
        viewBox="0 0 320 320"
        fill="none"
        className="relative drop-shadow-2xl"
      >
        {/* ── Back plate: widest shield silhouette (dark) ── */}
        <path d="M48 112 160 40l112 72-16 112-96 40-96-40z" fill="#3a0407" />

        {/* ── Mid shield (deep red) ── */}
        <path d="M64 116 160 56l96 60-12 96-84 36-84-36z" fill="#7a0f14" />

        {/* ── Front shield (bright red) ── */}
        <path d="M80 120 160 72l80 48-6 84-68 30-80-26v-8z" fill="#c4101a" />

        {/* ── Crown facets (top edge) ── */}
        {/* crown outer (dark) */}
        <path d="M160 20l-18 38-10-26-24 52-.3 10.7 31.3-20.8z" fill="#3a0407" />
        <path d="M160 20l18 38 10-26 24 52 .3 10.7-31.3-20.8z" fill="#5b0d12" />
        {/* crown center highlight */}
        <path d="M160 20l-8 32-7-24-16 42.2 28-17.2z" fill="#8c1418" />
        <path d="M160 20l7 31.7 8-23.5 15 42.7-26-18.7-4 14.8-12-28.9z" fill="#a30f16" />

        {/* ── Shield facet lines ── */}
        <path d="M100 128 160 88l60 40" stroke="#5b0d12" strokeWidth="1.4" opacity="0.9" />
        <path d="M120 128 160 96l40 32" stroke="#5b0d12" strokeWidth="1" opacity="0.7" />
        <path d="M160 88 160 216" stroke="#5b0d12" strokeWidth="1.2" opacity="0.85" />

        {/* ── Face: dark inner mask ── */}
        <path d="M126 124h68l12 52-44 40-44-40z" fill="#260405" />

        {/* ── Glowing eyes (angled, sharp) ── */}
        {/* left eye */}
        <path d="M134 150l24-10-4 18z" fill="#ff5555" />
        {/* right eye */}
        <path d="M186 150l-24-10 4 18z" fill="#ff5555" />
        {/* eye glow */}
        <path d="M134 150l24-10-4 18z" fill="#ffb3b3" opacity="0.85" />
        <path d="M186 150l-24-10 4 18z" fill="#ffb3b3" opacity="0.85" />

        {/* ── Nose ridge (dark slit between eyes) ── */}
        <path d="M156 130h12l6 36-10 12-8-12z" fill="#1a0304" />

        {/* ── Lower beak (sharp angular chin) ── */}
        <path d="M148 192l12-14 12 14-10 30z" fill="#8c1418" />
        <path d="M160 178l10 14-10 30-10-30z" fill="#a30f16" />

        {/* ── Ambient light on cheekbones ── */}
        <path d="M118 178l16 14-2 14z" fill="#e0141f" opacity="0.7" />
        <path d="M202 178l-16 14 2 14z" fill="#a30f16" opacity="0.9" />

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
      <svg width="340" height="300" viewBox="0 0 340 300" fill="none" className="mx-auto">
        {/* back sheet: faint ink plane */}
        <g transform="translate(20,120) skewX(-10) scale(1,0.85)">
          <rect x="0" y="0" width="150" height="120" rx="14" fill="#1a1d21" opacity="0.18" stroke="rgba(26,29,33,0.25)" />
          <text x="16" y="40" fill="#1a1d21" opacity="0.55" fontSize="11" fontFamily="monospace" letterSpacing="2">FIX</text>
          <text x="16" y="62" fill="#1a1d21" opacity="0.4" fontSize="9" fontFamily="monospace" letterSpacing="2">verified code-level guards</text>
        </g>

        {/* mid sheet: soft crimson plane */}
        <g transform="translate(105,92) skewX(-6) scale(1,0.82)">
          <rect x="0" y="0" width="158" height="132" rx="14" fill="#d61f26" opacity="0.22" stroke="rgba(214,31,38,0.45)" />
          <text x="16" y="46" fill="#a30f16" fontSize="12" fontFamily="monospace" letterSpacing="2" fontWeight="700">FIND</text>
          <text x="16" y="66" fill="#a30f16" opacity="0.75" fontSize="9" fontFamily="monospace" letterSpacing="2">violations + root cause</text>
          {/* little red accent dot, top-right */}
          <circle cx="142" cy="22" r="6" fill="#d61f26" />
        </g>

        {/* front sheet: bright crimson plane */}
        <g transform="translate(190,64) skewX(-2) scale(1,0.8) ratate(-4)">
          <rect x="0" y="0" width="164" height="144" rx="14" fill="#d61f26" opacity="0.85" stroke="rgba(255,255,255,0.6)" />
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
