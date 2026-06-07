import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getJobsHistory } from '../api/client.js';

const STATUS_CONFIG = {
  completed: { color: '#4ade80', bg: 'rgba(34,197,94,0.1)',  border: 'rgba(34,197,94,0.25)',  label: 'completed' },
  failed:    { color: '#f87171', bg: 'rgba(239,68,68,0.1)',  border: 'rgba(239,68,68,0.25)',  label: 'failed' },
  running:   { color: '#fbbf24', bg: 'rgba(251,191,36,0.1)', border: 'rgba(251,191,36,0.25)', label: 'running' },
  pending:   { color: '#64748b', bg: 'rgba(100,116,139,0.1)',border: 'rgba(100,116,139,0.2)', label: 'pending' },
};

function timeAgo(iso) {
  if (!iso) return '—';
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return 'Az önce';
  if (m < 60) return `${m} dk önce`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h} sa önce`;
  return `${Math.floor(h / 24)} gün önce`;
}

function DsommChip({ score }) {
  if (score == null) return <span style={{ color: '#334155' }}>—</span>;
  const color = score >= 70 ? '#4ade80' : score >= 40 ? '#fbbf24' : '#f87171';
  return (
    <span className="font-bold text-sm" style={{ color }}>
      {score.toFixed(1)}
    </span>
  );
}

function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.pending;
  return (
    <span
      className="text-[10px] font-semibold uppercase tracking-wide px-2 py-0.5 rounded-full"
      style={{ color: cfg.color, background: cfg.bg, border: `1px solid ${cfg.border}` }}
    >
      {cfg.label}
    </span>
  );
}

export default function HistoryPage() {
  const [records, setRecords]   = useState([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState('');
  const [selected, setSelected] = useState([]);
  const [search, setSearch]     = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    getJobsHistory(50).then((res) => {
      setLoading(false);
      if (res.ok) setRecords(res.data);
      else setError(res.error);
    });
  }, []);

  const toggleSelect = (jobId) => {
    setSelected((prev) => {
      if (prev.includes(jobId)) return prev.filter((id) => id !== jobId);
      if (prev.length >= 2) return prev;
      return [...prev, jobId];
    });
  };

  const handleCompare = () => {
    if (selected.length === 2) {
      navigate(`/compare?job_a=${selected[0]}&job_b=${selected[1]}`);
    }
  };

  const handleTrends = (repoUrl) => {
    navigate(`/trends?repo_url=${encodeURIComponent(repoUrl)}`);
  };

  const filtered = records.filter((r) =>
    !search.trim() || r.repo_url.toLowerCase().includes(search.trim().toLowerCase())
  );

  return (
    <div className="max-w-5xl mx-auto px-4 py-10">
      {/* Header */}
      <div className="flex items-center justify-between mb-8 flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: '#e2e8f0' }}>Analiz Geçmişi</h1>
          <p className="text-sm mt-1" style={{ color: '#475569' }}>
            {records.length} analiz
            {selected.length === 1 && ' · 1 seçildi — 1 tane daha seçin'}
          </p>
        </div>
        <div className="flex gap-3">
          {selected.length === 2 && (
            <button className="btn-primary text-sm px-4 py-2 rounded-lg" onClick={handleCompare}>
              🔄 Karşılaştır ({selected.length}/2)
            </button>
          )}
          <button
            className="text-sm px-4 py-2 rounded-lg font-medium transition-all duration-200"
            style={{
              background: 'rgba(99,102,241,0.1)',
              border: '1px solid rgba(99,102,241,0.25)',
              color: '#818cf8',
            }}
            onClick={() => navigate('/')}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(99,102,241,0.2)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'rgba(99,102,241,0.1)'; }}
          >
            + Yeni Analiz
          </button>
        </div>
      </div>

      {/* Arama kutusu */}
      {records.length > 0 && (
        <div className="mb-5">
          <input
            type="text"
            className="input text-sm"
            placeholder="🔍  Repo adına göre ara..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-24 gap-4">
          <div
            className="w-8 h-8 rounded-full border-2 border-indigo-500/30 border-t-indigo-500"
            style={{ animation: 'spin 0.8s linear infinite' }}
          />
          <span style={{ color: '#475569', fontSize: '0.875rem' }}>Yükleniyor...</span>
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      )}

      {/* Hata */}
      {error && (
        <div
          className="p-4 rounded-xl text-sm"
          style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', color: '#fca5a5' }}
        >
          ⚠ {error}
        </div>
      )}

      {/* Boş durum */}
      {!loading && !error && records.length === 0 && (
        <div className="text-center py-24">
          <p className="text-5xl mb-4">📭</p>
          <p className="mb-6" style={{ color: '#475569' }}>Henüz analiz yapılmamış.</p>
          <button className="btn-primary px-6 py-2.5 rounded-xl" onClick={() => navigate('/')}>
            İlk Analizi Başlat
          </button>
        </div>
      )}

      {/* Tablo */}
      {filtered.length > 0 && (
        <div
          className="overflow-x-auto rounded-2xl"
          style={{ border: '1px solid rgba(99,102,241,0.12)', boxShadow: '0 4px 24px rgba(0,0,0,0.3)' }}
        >
          <table className="w-full text-sm">
            <thead>
              <tr
                style={{
                  background: 'rgba(10,16,34,0.9)',
                  borderBottom: '1px solid rgba(99,102,241,0.1)',
                }}
              >
                <th className="px-3 py-3.5 w-8" />
                <th className="text-left px-4 py-3.5 text-[11px] font-semibold uppercase tracking-widest" style={{ color: '#475569' }}>Repo</th>
                <th className="text-left px-4 py-3.5 text-[11px] font-semibold uppercase tracking-widest" style={{ color: '#475569' }}>Dil</th>
                <th className="text-center px-4 py-3.5 text-[11px] font-semibold uppercase tracking-widest" style={{ color: '#475569' }}>DSOMM</th>
                <th className="text-center px-4 py-3.5 text-[11px] font-semibold uppercase tracking-widest" style={{ color: '#475569' }}>Bulgular</th>
                <th className="text-center px-4 py-3.5 text-[11px] font-semibold uppercase tracking-widest" style={{ color: '#475569' }}>Platform</th>
                <th className="text-right px-4 py-3.5 text-[11px] font-semibold uppercase tracking-widest" style={{ color: '#475569' }}>Tarih</th>
                <th className="px-3 py-3.5 w-20" />
              </tr>
            </thead>
            <tbody>
              {filtered.map((r, i) => {
                const isSelected = selected.includes(r.job_id);
                const isDisabled = selected.length === 2 && !isSelected;
                return (
                  <tr
                    key={r.job_id}
                    style={{
                      borderTop: '1px solid rgba(30,45,74,0.5)',
                      background: isSelected
                        ? 'rgba(99,102,241,0.08)'
                        : i % 2 === 0 ? 'rgba(10,16,34,0.5)' : 'rgba(14,22,40,0.3)',
                      opacity: isDisabled ? 0.4 : 1,
                      transition: 'background 0.15s ease',
                      ...(isSelected ? { borderLeft: '2px solid rgba(99,102,241,0.6)' } : {}),
                    }}
                    onMouseEnter={e => { if (!isDisabled && !isSelected) e.currentTarget.style.background = 'rgba(99,102,241,0.04)'; }}
                    onMouseLeave={e => { if (!isDisabled && !isSelected) e.currentTarget.style.background = i % 2 === 0 ? 'rgba(10,16,34,0.5)' : 'rgba(14,22,40,0.3)'; }}
                  >
                    <td className="px-3 py-3.5 text-center">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        disabled={isDisabled}
                        onChange={() => toggleSelect(r.job_id)}
                        className="w-4 h-4 cursor-pointer"
                        style={{ accentColor: '#6366f1' }}
                      />
                    </td>
                    <td className="px-4 py-3.5 max-w-xs">
                      <button
                        onClick={() => handleTrends(r.repo_url)}
                        className="font-medium truncate block max-w-[220px] text-left transition-colors duration-150"
                        style={{ color: '#818cf8' }}
                        title="Trend grafiğini görüntüle"
                        onMouseEnter={e => e.currentTarget.style.color = '#a5b4fc'}
                        onMouseLeave={e => e.currentTarget.style.color = '#818cf8'}
                      >
                        {r.repo_url.replace('https://github.com/', '')}
                      </button>
                      <div className="mt-0.5">
                        <StatusBadge status={r.status} />
                      </div>
                    </td>
                    <td className="px-4 py-3.5" style={{ color: '#94a3b8' }}>{r.language ?? '—'}</td>
                    <td className="px-4 py-3.5 text-center">
                      <DsommChip score={r.dsomm_total} />
                    </td>
                    <td className="px-4 py-3.5 text-center" style={{ color: '#94a3b8' }}>
                      {r.total_findings ?? '—'}
                    </td>
                    <td className="px-4 py-3.5 text-center text-xs" style={{ color: '#64748b' }}>
                      {r.platform?.replace('_', ' ') ?? '—'}
                    </td>
                    <td className="px-4 py-3.5 text-right text-xs whitespace-nowrap" style={{ color: '#475569' }}>
                      {timeAgo(r.finished_at ?? r.created_at)}
                    </td>
                    <td className="px-3 py-3.5 text-right">
                      <div className="flex gap-2 justify-end">
                        {r.status === 'completed' && (
                          <button
                            onClick={() => navigate(`/result/${r.job_id}`)}
                            className="text-sm transition-all duration-150 px-2 py-1 rounded-lg"
                            style={{ color: '#64748b' }}
                            title="Sonucu görüntüle"
                            onMouseEnter={e => { e.currentTarget.style.color = '#818cf8'; e.currentTarget.style.background = 'rgba(99,102,241,0.1)'; }}
                            onMouseLeave={e => { e.currentTarget.style.color = '#64748b'; e.currentTarget.style.background = 'transparent'; }}
                          >
                            🔍
                          </button>
                        )}
                        <button
                          onClick={() => handleTrends(r.repo_url)}
                          className="text-sm transition-all duration-150 px-2 py-1 rounded-lg"
                          style={{ color: '#64748b' }}
                          title="Trend"
                          onMouseEnter={e => { e.currentTarget.style.color = '#818cf8'; e.currentTarget.style.background = 'rgba(99,102,241,0.1)'; }}
                          onMouseLeave={e => { e.currentTarget.style.color = '#64748b'; e.currentTarget.style.background = 'transparent'; }}
                        >
                          📈
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
