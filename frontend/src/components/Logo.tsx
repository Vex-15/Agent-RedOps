export default function Logo({ size = 24 }: { size?: number }) {
  return (
    <span className="inline-flex items-center gap-2">
      <svg width={size} height={size} viewBox="0 0 64 64" fill="none" aria-hidden="true">
        <path
          fill="#d61f26"
          d="M36.9 8 13 21v20l10 10h4l7-4 22-12V17L46 8z"
        />
        <circle cx="25" cy="30" r="4" fill="#fff" />
        <circle cx="43" cy="30" r="4" fill="#fff" />
      </svg>
      <span className="font-bold text-ink tracking-tight text-lg leading-none">
        Red<span className="text-crimson">Ops</span>
      </span>
    </span>
  );
}
