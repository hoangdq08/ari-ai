export default function BrandMark({ className = "" }) {
  return (
    <svg className={className} viewBox="0 0 64 64" fill="none" aria-hidden="true">
      <defs>
        <linearGradient id="nong-tri-brand-mark" x1="12" y1="6" x2="54" y2="58" gradientUnits="userSpaceOnUse">
          <stop stopColor="#34d399" />
          <stop offset=".55" stopColor="#10b981" />
          <stop offset="1" stopColor="#0f766e" />
        </linearGradient>
      </defs>
      <rect width="64" height="64" rx="18" fill="#07111f" />
      <path
        d="M45.8 14.4c-12.7 1.2-22.1 6.8-27.1 16.8-3.1 6.3-2.9 12.7.4 17.1 2.4 3.1 6.1 4.7 10.4 4.2 8.5-1 14.9-8.9 15.7-19.5.3-4.4-.2-10.4.6-18.6Z"
        stroke="url(#nong-tri-brand-mark)"
        strokeWidth="4.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M20.1 45.4c5.8-8.3 12.6-14.6 21.4-19.3" stroke="#d1fae5" strokeWidth="3.7" strokeLinecap="round" />
      <circle cx="47" cy="18" r="3.5" fill="#a7f3d0" />
    </svg>
  );
}
