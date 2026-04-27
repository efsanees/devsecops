// SVG stroke-dasharray gaugesi — SQLAlchemy veya harici kutuphanesi gerekmez
function gradeColor(grade) {
  return { A: '#22c55e', B: '#3b82f6', C: '#f59e0b', D: '#ef4444' }[grade] ?? '#94a3b8';
}

function gradeBg(grade) {
  return { A: 'bg-green-900/40 text-green-300 border-green-700', B: 'bg-blue-900/40 text-blue-300 border-blue-700',
           C: 'bg-amber-900/40 text-amber-300 border-amber-700', D: 'bg-red-900/40 text-red-300 border-red-700' }[grade]
    ?? 'bg-slate-700 text-slate-300 border-slate-600';
}

export default function ScoreGauge({ score = 0, grade = 'D' }) {
  const r = 52;
  const cx = 68;
  const cy = 68;
  const sw = 10;
  const circumference = Math.PI * r; // yaricember yay uzunlugu
  const dashOffset = circumference * (1 - Math.min(score, 100) / 100);
  const color = gradeColor(grade);

  return (
    <div className="flex flex-col items-center gap-3">
      <svg width="136" height="80" viewBox="0 0 136 80" className="overflow-visible">
        {/* Arkaplan yay */}
        <path
          d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
          fill="none" stroke="#334155" strokeWidth={sw} strokeLinecap="round"
        />
        {/* Skor yay */}
        <path
          d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
          fill="none" stroke={color} strokeWidth={sw} strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          style={{ transition: 'stroke-dashoffset 0.8s ease' }}
        />
        {/* Skor metni */}
        <text x={cx} y={cy - 8} textAnchor="middle" fill="white" fontSize="22" fontWeight="700">
          {score}
        </text>
        <text x={cx} y={cy + 10} textAnchor="middle" fill="#64748b" fontSize="11">
          / 100
        </text>
      </svg>
      <span className={`px-3 py-1 rounded-lg text-lg font-bold border ${gradeBg(grade)}`}>
        {grade} Notu
      </span>
    </div>
  );
}
