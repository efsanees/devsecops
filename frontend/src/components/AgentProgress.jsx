const STATUS_CONFIG = {
  pending:   {
    icon: '○',
    color: '#475569',
    bg: 'rgba(10,16,34,0.5)',
    border: 'rgba(30,45,74,0.6)',
    dot: '#334155',
    label: 'Bekliyor',
  },
  running:   {
    icon: '◌',
    color: '#818cf8',
    bg: 'rgba(99,102,241,0.07)',
    border: 'rgba(99,102,241,0.3)',
    dot: '#6366f1',
    label: 'Çalışıyor',
  },
  completed: {
    icon: '✓',
    color: '#4ade80',
    bg: 'rgba(34,197,94,0.06)',
    border: 'rgba(34,197,94,0.2)',
    dot: '#4ade80',
    label: 'Tamamlandı',
  },
  failed:    {
    icon: '✗',
    color: '#f87171',
    bg: 'rgba(239,68,68,0.07)',
    border: 'rgba(239,68,68,0.2)',
    dot: '#f87171',
    label: 'Hata',
  },
};

function FindingSummary({ data }) {
  if (!data) return null;
  const total = data.total_count ?? data.total ?? null;
  if (total === null) return null;
  return (
    <span style={{ color: total === 0 ? '#4ade80' : '#fbbf24', fontSize: '0.7rem', fontWeight: 500 }}>
      {total === 0 ? '· Bulgu yok' : `· ${total} bulgu`}
    </span>
  );
}

export default function AgentProgress({ name, label, icon, desc, status = 'pending', data = null, error = null }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.pending;

  return (
    <div
      className="flex items-center gap-4 p-4 rounded-xl transition-all duration-400"
      style={{
        background: cfg.bg,
        border: `1px solid ${cfg.border}`,
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        boxShadow: status === 'running'
          ? `0 0 16px ${cfg.border}, inset 0 1px 0 rgba(255,255,255,0.03)`
          : 'inset 0 1px 0 rgba(255,255,255,0.02)',
      }}
    >
      {/* Sol: araç ikonu */}
      <div className="text-2xl w-8 text-center select-none flex-shrink-0">
        {icon}
      </div>

      {/* Orta: isim + açıklama + durum */}
      <div className="flex-1 min-w-0">
        <div className="font-semibold text-sm truncate" style={{ color: '#e2e8f0' }}>{label}</div>
        {desc && status === 'pending' && (
          <div className="text-[11px] truncate mt-0.5" style={{ color: '#334155' }}>{desc}</div>
        )}
        <div className="text-xs mt-0.5 flex items-center gap-1.5" style={{ color: cfg.color }}>
          <span
            style={status === 'running' ? { animation: 'spin 1s linear infinite', display: 'inline-block' } : {}}
          >
            {cfg.icon}
          </span>
          <span style={{ fontWeight: 500 }}>{cfg.label}</span>
          {status === 'completed' && <FindingSummary data={data} />}
          {status === 'failed' && error && (
            <span className="truncate max-w-[180px]" style={{ color: '#f87171' }}>{error}</span>
          )}
        </div>
      </div>

      {/* Sağ: durum göstergesi */}
      <div className="flex-shrink-0 flex items-center">
        <div
          className="w-2.5 h-2.5 rounded-full"
          style={{
            background: cfg.dot,
            boxShadow: `0 0 6px ${cfg.dot}`,
            animation: status === 'running' ? 'pulse-dot 1.5s ease-in-out infinite' : 'none',
          }}
        />
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes pulse-dot {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.5; transform: scale(0.8); }
        }
      `}</style>
    </div>
  );
}
