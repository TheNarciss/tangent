/**
 * The Tangent mark: a line grazing a circle, rising. Same drawing as /favicon.svg.
 */
export function Logo({ size = 24, className }: { size?: number; className?: string }) {
  return (
    <svg
      viewBox="0 0 64 64"
      width={size}
      height={size}
      className={className}
      aria-hidden="true"
      focusable="false"
    >
      <rect width="64" height="64" rx="15" fill="#2a78d6" />
      <circle cx="37" cy="42" r="13" fill="none" stroke="#ffffff" strokeWidth="8" />
      <path
        d="M 11 49.6 L 53 7.6"
        fill="none"
        stroke="#ffffff"
        strokeWidth="8"
        strokeLinecap="round"
      />
    </svg>
  );
}
