import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { getTrends } from '../api/client.js';
import TrendChart from '../components/TrendChart.jsx';

export default function TrendsPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const repoUrl = searchParams.get('repo_url') ?? '';

  const [data, setData]     = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState('');

  useEffect(() => {
    if (!repoUrl) {
      setLoading(false);
      setError('repo_url parametresi eksik');
      return;
    }
    getTrends(repoUrl).then((res) => {
      setLoading(false);
      if (res.ok) setData(res.data);
      else setError(res.error);
    });
  }, [repoUrl]);

  const repoName = repoUrl.replace('https://github.com/', '');

  return (
    <div className="max-w-3xl mx-auto px-4 py-10 space-y-8">
      {/* Başlık */}
      <div>
        <button onClick={() => navigate('/history')}
          className="text-xs text-slate-500 hover:text-slate-300 mb-3 flex items-center gap-1">
          ← Geçmişe Dön
        </button>
        <h1 className="text-xl font-bold text-white break-all">
          📈 Trend: {repoName}
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          DSOMM olgunluk skoru zaman serisi
        </p>
      </div>

      {loading && (
        <div className="flex justify-center py-16">
          <span className="text-slate-500 animate-pulse">Yükleniyor...</span>
        </div>
      )}

      {error && (
        <div className="card border-red-700 text-red-300 text-sm">⚠ {error}</div>
      )}

      {!loading && !error && data.length === 0 && (
        <div className="text-center py-16">
          <p className="text-3xl mb-3">📭</p>
          <p className="text-slate-400">Bu repo için tamamlanmış analiz bulunamadı.</p>
          <button className="btn-primary mt-4" onClick={() => navigate('/')}>
            Yeni Analiz Başlat
          </button>
        </div>
      )}

      {data.length > 0 && (
        <>
          {/* Grafik */}
          <section className="space-y-3">
            <h2 className="text-base font-semibold text-white">DSOMM Skor Değişimi</h2>
            <div className="card">
              <TrendChart dataPoints={data} />
            </div>
          </section>

          {/* Analiz listesi */}
          <section className="space-y-3">
            <h2 className="text-base font-semibold text-white">Analizler ({data.length})</h2>
            <div className="space-y-2">
              {data.map((d, i) => {
                const prevScore = i > 0 ? data[i - 1].dsomm_total : null;
                const diff = prevScore != null && d.dsomm_total != null
                  ? d.dsomm_total - prevScore : null;
                return (
                  <div key={d.job_id}
                    className="card flex items-center justify-between gap-4 py-3">
                    <div className="text-xs text-slate-500 shrink-0">
                      {d.finished_at
                        ? new Date(d.finished_at).toLocaleDateString('tr-TR', { day:'2-digit', month:'short', year:'2-digit' })
                        : '—'}
                    </div>
                    <div className="flex-1 text-slate-400 text-xs">
                      {d.platform?.replace('_', ' ') ?? '—'}
                    </div>
                    <div className="flex items-center gap-2">
                      {d.dsomm_total != null ? (
                        <span className="font-bold text-violet-300">
                          {d.dsomm_total.toFixed(1)}
                        </span>
                      ) : <span className="text-slate-600">—</span>}
                      {diff != null && (
                        <span className={`text-xs font-semibold ${diff > 0 ? 'text-green-400' : diff < 0 ? 'text-red-400' : 'text-slate-500'}`}>
                          {diff > 0 ? `+${diff.toFixed(1)}` : diff.toFixed(1)}
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-slate-500 shrink-0">
                      {d.total_findings} bulgu
                    </div>
                    <button
                      onClick={() => navigate(`/result`, {
                        state: { data: { job_id: d.job_id }, repoUrl: repoUrl }
                      })}
                      className="text-xs text-blue-400 hover:text-blue-300 shrink-0"
                    >
                      #{d.job_id.slice(0, 8)}
                    </button>
                  </div>
                );
              })}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
