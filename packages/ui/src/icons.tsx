type IconProps = { className?: string };

export function EyeIcon({ open, className }: IconProps & { open: boolean }) {
  return open ? (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className={className}>
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" strokeLinejoin="round" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  ) : (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className={className}>
      <path d="M3 3l18 18M10.6 10.6a3 3 0 0 0 4.2 4.2M6.7 6.7C4.1 8.3 2 12 2 12s3.5 7 10 7c1.9 0 3.5-.5 4.9-1.3M17.4 17.4C19.7 15.8 22 12 22 12s-1.2-2.4-3.4-4.3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
