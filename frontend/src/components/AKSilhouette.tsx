// 中央 3D AK-47 SVG 轮廓 — 与 preview.html 完全一致的 path
export default function AKSilhouette() {
  return (
    <div
      className="absolute inset-0 flex items-center justify-center pointer-events-none perspective-3d"
      style={{ top: 60 }}
    >
      <div className="float-3d">
        <svg
          width="1000"
          height="320"
          viewBox="0 0 1000 320"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          style={{ filter: "drop-shadow(0 20px 40px rgba(99,102,241,0.15))" }}
        >
          <defs>
            <linearGradient id="akGrad" x1="0" x2="1" y1="0" y2="0">
              <stop offset="0%" stopColor="#6366F1" />
              <stop offset="50%" stopColor="#EC4899" />
              <stop offset="100%" stopColor="#F59E0B" />
            </linearGradient>
            <linearGradient id="akFill" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#6366F1" stopOpacity="0.05" />
              <stop offset="100%" stopColor="#EC4899" stopOpacity="0.02" />
            </linearGradient>
          </defs>

          <path
            d="M 80 175 L 160 175 L 178 158 L 215 158 L 222 145 L 295 145 L 302 132 L 360 132 L 368 118 L 425 118 L 433 105 L 460 105 L 478 88 L 510 88 L 518 105 L 695 105 L 702 118 L 752 118 L 770 138 L 802 138 L 810 125 L 858 125 L 870 138 L 912 138 L 920 152 L 962 152 L 975 168 L 1015 168 L 1028 182 L 1028 200 L 1015 215 L 695 215 L 678 232 L 640 232 L 622 248 L 580 248 L 560 265 L 522 265 L 508 252 L 495 245 L 460 245 L 452 228 L 405 228 L 398 220 L 355 220 L 348 228 L 300 228 L 282 245 L 245 245 L 225 228 L 162 228 L 145 215 L 80 215 Z"
            fill="url(#akFill)"
            stroke="url(#akGrad)"
            strokeWidth="2.5"
            strokeLinejoin="round"
            opacity="0.55"
          />
          <path
            d="M 432 215 L 418 268 L 442 285 L 502 285 L 522 268 L 510 215 Z"
            fill="url(#akFill)"
            stroke="url(#akGrad)"
            strokeWidth="2"
            opacity="0.55"
            strokeLinejoin="round"
          />
          <circle cx="385" cy="245" r="14" stroke="url(#akGrad)" strokeWidth="1.5" fill="none" opacity="0.45" />
          <g style={{ animation: "heartbeatPulse 3s ease-in-out infinite" }}>
            <circle cx="640" cy="95" r="4" fill="url(#akGrad)" opacity="0.8" />
            <circle cx="640" cy="95" r="14" stroke="url(#akGrad)" strokeWidth="1.2" fill="none" opacity="0.5" />
            <circle cx="640" cy="95" r="26" stroke="url(#akGrad)" strokeWidth="0.8" fill="none" opacity="0.3" />
            <line x1="640" y1="60" x2="640" y2="75" stroke="url(#akGrad)" strokeWidth="1.2" opacity="0.6" />
            <line x1="640" y1="115" x2="640" y2="130" stroke="url(#akGrad)" strokeWidth="1.2" opacity="0.6" />
            <line x1="605" y1="95" x2="620" y2="95" stroke="url(#akGrad)" strokeWidth="1.2" opacity="0.6" />
            <line x1="660" y1="95" x2="675" y2="95" stroke="url(#akGrad)" strokeWidth="1.2" opacity="0.6" />
          </g>
          <path
            d="M 1028 190 Q 1100 180 1180 200"
            stroke="url(#akGrad)"
            strokeWidth="1"
            fill="none"
            opacity="0.3"
            strokeDasharray="4 4"
          />
        </svg>
      </div>
    </div>
  );
}
