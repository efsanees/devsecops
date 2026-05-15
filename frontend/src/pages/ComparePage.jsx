import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { compareJobs } from '../api/client.js';
import SeverityBadge from '../components/SeverityBadge.jsx';

function FindingCard({ f }) {
  const isSSast = f.type === 'SAST' || f._category === 'sast';
  return (
    <div className="p-3 bg-slate-900 rounded-lg border border-slate-700 text-sm space-y-1">
      <div className="flex items-center gap-2">
        <SeverityBadge severity={f.severity} />
        <span className="text-xs text-slate-500">{f.type ?? f._category?.toUpperCase()}</span>
        {f.cwe_id && (
          <span className="text-xs px-1.5 py-0.5 rounded bg-slate-700 text-slate-300 font-mono">
            {f.cwe_id}
          </span>
        )}
        {f.owasp_category && (
          <span className="text-xs px-1.5 py-0.5 rounded bg-violet-900/50 text-violet-300">
            {f.owasp_category}
          </span>
        )}
      </div>
      <p className="text-slate-200">
        {f.message || f.summary || f.secret_type || f.vuln_id || f.rule_id}
      </p>
      {isSSast && f.file && (
        <p className="text-xs text-slate-500 font-mono">
          {f.file}{f.line ? `:${f.line}` : ''}
        </p>
      )}
      {!isSSast && f.package && (
        <p className="text-xs text-slate-500 font-mono">
          {f.package}@{f.version} — {f.vuln_id}
        </p>
      )}
    </div>
  );
}

function DsommDiff({ diff, totalDiff }) {
  if (!diff || Object.keys(diff).length === 0) return null;
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-sm font-semibold text-white">DSOMM Farkı (B - A)</span>
        {totalDiff != null && (
          <span className={`text-sm font-bold ${totalDiff > 0 ? 'text-green-400' : totalDiff < 0 ? 'text-red-400' : 'text-slate-500'}`}>
            {totalDiff > 0 ? `+${totalDiff}` : totalDiff}
          </span>
        )}
      </div>
      {Object.entries(diff).map(([cat, val]) => (
        <div key={cat} className="flex items-center justify-between">
          <span className="text-xs text-slate-400 capitalize">{cat.replace('_', ' ')}</span>
          <span className={`text-xs font-semibold ${val > 0 ? 'text-green-400' : val < 0 ? 'text-red-400' : 'text-slate-500'}`}>
            {val > 0 ? `+${val}` : val}
          </span>
        </div>
      ))}
    </div>
  );
}

export default function ComparePage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const jobAId = searchParams.get('job_a') ?? '';
  const jobBId = searchParams.get('job_b') ?? '';

  const [result, setResult]   = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState('');

  useEffect(() => {
    if (!jobAId || !jobBId) {
      setLoading(false);
      setError('job_a ve job_b parametreleri gerekli');
      return;
    }
    compareJobs(jobAId, jobBId).then((res) => {
      setLoading(false);
      if (res.ok) setResult(res.data);
      else setError(res.error);
    });
  }, [jobAId, jobBId]);

  return (
    <div className="max-w-4xl mx-auto px-4 py-10 space-y-8">
      {/* Başlık */}
      <div>
        <button onClick={() => navigate('/history')}
          className="text-xs text-slate-500 hover:text-slate-300 mb-3 flex items-center gap-1">
          ← Geçmişe Dön
        </button>
        <h1 className="text-xl font-bold text-white">🔄 Analiz Karşılaştırması</h1>
        {result && !result.repo_match && (
          <p className="text-amber-400 text-xs mt-1">
            ⚠ Bu iki job farklı repolar için — karşılaştırma referans amaçlıdır.
          </p>
        )}
      </div>

      {loading && (
        <div className="flex justify-center py-16">
          <span className="text-slate-500 animate-pulse">Yükleniyor...</span>
        </div>
      )}

      {error && (
        <div className="card border-red-700 text-red-300 text-sm">⚠ {error}</div>
      )}

      {result && (
        <>
          {/* Job özetleri */}
          <div className="grid grid-cols-2 gap-4">
            {[result.job_a, result.job_b].map((j, idx) => (
              <div key={idx} className={`card border ${idx === 0 ? 'border-slate-600' : 'border-blue-700/50'}`}>
                <p className={`text-xs font-semibold mb-2 ${idx === 0 ? 'text-slate-400' : 'text-blue-400'}`}>
                  {idx === 0 ? 'A — Eski Analiz' : 'B — Yeni Analiz'}
                </p>
                <p className="text-white font-medium text-sm break-all">
                  {j.repo_url?.replace('https://github.com/', '') ?? '—'}
                </p>
                <p className="text-slate-500 text-xs mt-1">
                  #{j.job_id?.slice(0, 8)} · {j.finished_at
                    ? new Date(j.finished_at).toLocaleDateString('tr-TR')
                    : '—'}
                </p>
                <div className="flex gap-4 mt-2">
                  <div>
                    <p className="text-xs text-slate-500">DSOMM</p>
                    <p className="font-bold text-violet-300">
                      {j.dsomm_total != null ? j.dsomm_total.toFixed(1) : '—'}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Bulgular</p>
                    <p className="font-bold text-slate-200">{j.total_findings ?? '—'}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Özet sayılar */}
          <div className="grid grid-cols-3 gap-4 text-center">
            <div className="card">
              <p className="text-2xl font-bold text-red-400">{result.added?.length ?? 0}</p>
              <p className="text-xs text-slate-400 mt-1">Yeni Bulgu (B'de eklendi)</p>
            </div>
            <div className="card">
              <p className="text-2xl font-bold text-green-400">{result.removed?.length ?? 0}</p>
              <p className="text-xs text-slate-400 mt-1">Düzeltilen (A'dan kaldırıldı)</p>
            </div>
            <div className="card">
              <p className="text-2xl font-bold text-slate-400">{result.unchanged_count ?? 0}</p>
              <p className="text-xs text-slate-400 mt-1">Değişmeyen</p>
            </div>
          </div>

          {/* DSOMM farkı */}
          {result.dsomm_diff && Object.keys(result.dsomm_diff).length > 0 && (
            <div className="card">
              <DsommDiff diff={result.dsomm_diff} totalDiff={result.dsomm_total_diff} />
            </div>
          )}

          {/* Yeni bulgular */}
          {result.added?.length > 0 && (
            <section className="space-y-3">
              <h2 className="text-base font-semibold text-red-400">
                🔴 Yeni Bulgular ({result.added.length})
              </h2>
              <div className="space-y-2">
                {result.added.map((f, i) => <FindingCard key={i} f={f} />)}
              </div>
            </section>
          )}

          {/* Düzeltilen bulgular */}
          {result.removed?.length > 0 && (
            <section className="space-y-3">
              <h2 className="text-base font-semibold text-green-400">
                ✅ Düzeltilen Bulgular ({result.removed.length})
              </h2>
              <div className="space-y-2">
                {result.removed.map((f, i) => <FindingCard key={i} f={f} />)}
              </div>
            </section>
          )}

          {result.added?.length === 0 && result.removed?.length === 0 && (
            <div className="card text-center py-8">
              <p className="text-2xl mb-2">🎯</p>
              <p className="text-slate-300 font-semibold">Bulgu değişimi yok</p>
              <p className="text-slate-500 text-sm mt-1">İki analiz arasında aynı bulgular mevcut.</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
