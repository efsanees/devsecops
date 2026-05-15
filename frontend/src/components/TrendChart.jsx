const CATEGORY_COLORS = {
  'build_deploy':      '#818cf8',
  'test':              '#34d399',
  'monitoring':        '#f59e0b',
  'secret_management': '#f87171',
  'hardening':         '#60a5fa',
};

const CATEGORY_LABELS = {
  'build_deploy':      'Build & Deploy',
  'test':              'Test',
  'monitoring':        'Monitoring',
  'secret_management': 'Secrets',
  'hardening':         'Hardening',
};

function formatDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return `${d.getDate().toString().padStart(2,'0')}/${(d.getMonth()+1).toString().padStart(2,'0')}`;
}

export default function TrendChart({ dataPoints = [] }) {
  if (dataPoints.length < 2) {
    return (
      <div className="py-10 text-center text-slate-500 text-sm">
        Grafik için en az 2 analiz gereklidir. ({dataPoints.length}/2)
      </div>
    );
  }

  const W = 560, H = 200, PAD = { top: 16, right: 16, bottom: 32, left: 40 };
  const chartW = W - PAD.left - PAD.right;
  const chartH = H - PAD.top - PAD.bottom;

  const allScores = dataPoints.flatMap((d) => {
    const cats = Object.values(d.dsomm_categories || {}).map(Number).filter(Boolean);
    return [d.dsomm_total, ...cats].filter((v) => v != null);
  });
  const minY = Math.max(0, Math.min(...allScores) - 5);
  const maxY = Math.min(100, Math.max(...allScores) + 5);

  const xScale = (i) => PAD.left + (i / (dataPoints.length - 1)) * chartW;
  const yScale = (v) => PAD.top + chartH - ((v - minY) / (maxY - minY)) * chartH;

  const categories = dataPoints[0]?.dsomm_categories
    ? Object.keys(dataPoints[0].dsomm_categories)
    : [];

  const makeLinePath = (getter) => {
    return dataPoints
      .map((d, i) => {
        const v = getter(d);
        if (v == null) return null;
        return `${i === 0 ? 'M' : 'L'}${xScale(i).toFixed(1)},${yScale(v).toFixed(1)}`;
      })
      .filter(Boolean)
      .join(' ');
  };

  return (
    <div className="w-full overflow-x-auto">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" style={{ minWidth: 320 }}>
        {/* Y axis grid */}
        {[0, 25, 50, 75, 100].map((v) => {
          if (v < minY || v > maxY) return null;
          const y = yScale(v).toFixed(1);
          return (
            <g key={v}>
              <line x1={PAD.left} y1={y} x2={PAD.left + chartW} y2={y}
                stroke="#334155" strokeWidth="0.5" strokeDasharray="4,4" />
              <text x={PAD.left - 4} y={y} textAnchor="end" fill="#64748b"
                fontSize="9" dominantBaseline="middle">{v}</text>
            </g>
          );
        })}

        {/* Category lines */}
        {categories.map((cat) => (
          <path
            key={cat}
            d={makeLinePath((d) => d.dsomm_categories?.[cat])}
            fill="none"
            stroke={CATEGORY_COLORS[cat] ?? '#94a3b8'}
            strokeWidth="1.5"
            strokeOpacity="0.6"
            strokeDasharray="4,3"
          />
        ))}

        {/* Total score line */}
        <path
          d={makeLinePath((d) => d.dsomm_total)}
          fill="none"
          stroke="#a78bfa"
          strokeWidth="2.5"
        />

        {/* Data points for total */}
        {dataPoints.map((d, i) => {
          if (d.dsomm_total == null) return null;
          return (
            <circle
              key={i}
              cx={xScale(i).toFixed(1)}
              cy={yScale(d.dsomm_total).toFixed(1)}
              r="4"
              fill="#a78bfa"
              stroke="#1e293b"
              strokeWidth="1.5"
            >
              <title>{`${formatDate(d.finished_at)}: ${d.dsomm_total?.toFixed(1)}`}</title>
            </circle>
          );
        })}

        {/* X axis labels */}
        {dataPoints.map((d, i) => (
          <text key={i} x={xScale(i).toFixed(1)} y={H - 6}
            textAnchor="middle" fill="#64748b" fontSize="9">
            {formatDate(d.finished_at)}
          </text>
        ))}
      </svg>

      {/* Legend */}
      <div className="flex flex-wrap gap-3 mt-2">
        <div className="flex items-center gap-1.5">
          <div className="w-5 h-0.5 bg-violet-400 rounded" />
          <span className="text-xs text-slate-300">Toplam</span>
        </div>
        {categories.map((cat) => (
          <div key={cat} className="flex items-center gap-1.5">
            <div className="w-5 h-0 border-t border-dashed"
              style={{ borderColor: CATEGORY_COLORS[cat] ?? '#94a3b8' }} />
            <span className="text-xs text-slate-400">
              {CATEGORY_LABELS[cat] ?? cat}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
