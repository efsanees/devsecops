import { useLocation, useNavigate } from 'react-router-dom';
import ScoreGauge from '../components/ScoreGauge.jsx';
import PipelineViewer from '../components/PipelineViewer.jsx';
import SeverityBadge, { RiskLevelBadge } from '../components/SeverityBadge.jsx';
import DsommDashboard from '../components/DsommDashboard.jsx';
import FindingsTable from '../components/FindingsTable.jsx';
import { getJobYamlUrl } from '../api/client.js';

// --- Küçük yardımcı bileşenler ---

function InfoChip({ label, value, ok }) {
  const color = ok === true ? 'text-green-400' : ok === false ? 'text-red-400' : 'text-slate-300';
  const icon  = ok === true ? '✓' : ok === false ? '✗' : null;
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-slate-700 last:border-0">
      <span className="text-slate-400 text-sm">{label}</span>
      <span className={`text-sm font-medium flex items-center gap-1.5 ${color}`}>
        {icon && <span>{icon}</span>}
        {value}
      </span>
    </div>
  );
}

function Section({ icon, title, children }) {
  return (
    <section className="space-y-3">
      <h2 className="flex items-center gap-2 text-base font-semibold text-white">
        <span>{icon}</span>
        {title}
      </h2>
      {children}
    </section>
  );
}

function SkippedNotice({ reason }) {
  if (!reason) return null;
  return (
    <div className="flex items-start gap-2 p-3 bg-amber-900/20 border border-amber-700/50 rounded-lg text-amber-300 text-xs">
      <span className="shrink-0">ℹ️</span>
      <span>{reason}</span>
    </div>
  );
}

// --- Analiz özet kartı ---
function AnalysisCard({ data, type }) {
  const analysis = data.analysis ?? data;
  return (
    <Section icon="🔍" title="Repo Analizi">
      <div className="card">
        <InfoChip label="Dil" value={analysis.language ?? '—'} />
        <InfoChip label="Framework" value={analysis.framework ?? '—'} />
        <InfoChip label="Test Dosyaları" value={analysis.has_tests ? 'Var' : 'Yok'} ok={analysis.has_tests} />
        <InfoChip label="Docker" value={analysis.has_docker ? 'Var' : 'Yok'} ok={analysis.has_docker} />
        {type === 'security' && (
          <>
            <InfoChip label="Taranan Dosya (SAST)" value={data.sast?.files_scanned ?? 0} />
            <InfoChip label="Kontrol Edilen Paket (SCA)" value={data.sca?.packages_checked ?? 0} />
          </>
        )}
      </div>
    </Section>
  );
}

// --- Uyum skoru kartı ---
function ComplianceCard({ data }) {
  const { score, grade, checks = {}, issues = [] } = data;
  return (
    <Section icon="📊" title="Uyum Skoru">
      <div className="card flex flex-col gap-5">
        <div className="flex items-center justify-center py-2">
          <ScoreGauge score={score} grade={grade} />
        </div>
        {Object.keys(checks).length > 0 && (
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Kontroller</p>
            {Object.entries(checks).map(([key, val]) => (
              <InfoChip
                key={key}
                label={key.replace(/_/g, ' ')}
                value={val ? 'Geçti' : 'Başarısız'}
                ok={val}
              />
            ))}
          </div>
        )}
        {issues.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Düzeltilmesi Gerekenler</p>
            {issues.map((issue, i) => (
              <div key={i} className="flex items-start gap-2 text-sm text-amber-300">
                <span className="mt-0.5 shrink-0">⚠</span>
                <span>{issue}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </Section>
  );
}

// --- Risk raporu kartı ---
function RiskCard({ data }) {
  const { risk_score, risk_level, total_findings, by_severity, sast, sca, top_findings = [] } = data;

  const sastSkipped = sast?.files_scanned === 0 ? sast?.skipped_reason : null;
  const scaSkipped  = sca?.packages_checked === 0 ? sca?.skipped_reason : null;

  return (
    <Section icon="🛡️" title="Güvenlik Risk Raporu">
      <div className="space-y-4">
        {/* Skor özeti */}
        <div className="card space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-xs mb-1">Risk Skoru</p>
              <p className="text-3xl font-bold text-white">
                {risk_score}<span className="text-base text-slate-500">/100</span>
              </p>
            </div>
            <RiskLevelBadge level={risk_level} />
          </div>
          <div className="grid grid-cols-4 gap-3">
            {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((sev) => (
              <div key={sev} className="text-center">
                <p className="text-xl font-bold text-white">{by_severity?.[sev] ?? 0}</p>
                <SeverityBadge severity={sev} />
              </div>
            ))}
          </div>
        </div>

        {/* SAST/SCA özeti */}
        <div className="grid grid-cols-2 gap-3">
          <div className="card space-y-1">
            <p className="text-slate-400 text-xs">SAST (Bandit)</p>
            <p className="text-lg font-semibold text-white">{sast?.findings_count ?? 0} bulgu</p>
            <p className="text-slate-500 text-xs">{sast?.files_scanned ?? 0} dosya tarandı</p>
            <SkippedNotice reason={sastSkipped} />
          </div>
          <div className="card space-y-1">
            <p className="text-slate-400 text-xs">SCA (OSV.dev)</p>
            <p className="text-lg font-semibold text-white">{sca?.findings_count ?? 0} CVE</p>
            <p className="text-slate-500 text-xs">{sca?.packages_checked ?? 0} paket kontrol edildi</p>
            <SkippedNotice reason={scaSkipped} />
          </div>
        </div>

        {/* Bulgular listesi */}
        {top_findings.length > 0 && (
          <div className="card space-y-3">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              En Kritik Bulgular ({top_findings.length})
            </p>
            {top_findings.map((f, i) => (
              <div key={i} className="p-3 bg-slate-900 rounded-lg border border-slate-700">
                <div className="flex items-start justify-between gap-3 mb-2">
                  <SeverityBadge severity={f.severity} />
                  <span className="text-xs text-slate-500 shrink-0">{f.type}</span>
                </div>
                <p className="text-sm text-slate-200 font-medium">{f.summary}</p>
                {f.type === 'SAST' && (
                  <div className="mt-1.5 space-y-0.5">
                    <p className="text-xs text-slate-500">
                      📄 {f.file}{f.line ? `:${f.line}` : ''} — {f.issue_id}
                    </p>
                    {f.owasp && <p className="text-xs text-violet-400">{f.owasp}</p>}
                  </div>
                )}
                {f.type === 'SCA' && (
                  <div className="mt-1.5 space-y-0.5">
                    <p className="text-xs text-slate-500">
                      📦 {f.package} {f.version} — {f.vuln_id}
                      {f.cvss_score && <span className="ml-1 text-amber-400">CVSS {f.cvss_score}</span>}
                    </p>
                    {f.fixed_in && f.fixed_in !== 'bilinmiyor' && (
                      <p className="text-xs text-green-400">✓ Düzeltme: {f.fixed_in}</p>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {total_findings === 0 && !sastSkipped && !scaSkipped && (
          <div className="card text-center py-6">
            <p className="text-3xl mb-2">🎉</p>
            <p className="text-green-400 font-semibold">Zafiyet tespit edilmedi</p>
            <p className="text-slate-500 text-sm mt-1">SAST ve SCA taramaları temiz çıktı.</p>
          </div>
        )}
      </div>
    </Section>
  );
}

const PLATFORM_LABELS = {
  github_actions: { label: 'GitHub Actions', icon: '🐙' },
  gitlab_ci:      { label: 'GitLab CI',      icon: '🦊' },
  jenkins:        { label: 'Jenkins',         icon: '☕' },
};

// ── Multi-agent job sonucu görünümü ──────────────────────────────────────────

function JobResultView({ data, navigate }) {
  const { profile = {}, dsomm, findings = {}, llm_summary, pipeline_yaml, job_id, elapsed_seconds } = data;

  const totalFindings =
    (findings.sast?.length ?? 0) +
    (findings.sca?.length ?? 0) +
    (findings.secret?.length ?? 0);

  return (
    <div className="space-y-8">
      {/* Profil özeti */}
      <Section icon="🔍" title="Proje Profili">
        <div className="card">
          <InfoChip label="Dil"            value={profile.language    ?? '—'} />
          <InfoChip label="Framework"      value={profile.framework   ?? '—'} />
          <InfoChip label="Paket Yöneticisi" value={profile.package_manager ?? '—'} />
          <InfoChip label="Test Dosyaları" value={profile.has_tests ? 'Var' : 'Yok'} ok={profile.has_tests} />
          <InfoChip label="Docker"         value={profile.has_docker ? 'Var' : 'Yok'} ok={profile.has_docker} />
          {elapsed_seconds && (
            <InfoChip label="Analiz Süresi" value={`${elapsed_seconds}s`} />
          )}
        </div>
      </Section>

      {/* DSOMM güvenlik olgunluk skoru */}
      {dsomm && (
        <Section icon="📊" title="Güvenlik Olgunluk Skoru (DSOMM)">
          <div className="card">
            <DsommDashboard dsomm={dsomm} />
          </div>
        </Section>
      )}

      {/* Bulgular — 4 sekme */}
      <Section icon="🛡️" title={`Güvenlik Bulguları ${totalFindings > 0 ? `(${totalFindings})` : ''}`}>
        <div className="card">
          <FindingsTable findings={findings} />
        </div>
      </Section>

      {/* LLM yorumu */}
      {llm_summary && (
        <Section icon="🤖" title="AI Risk Değerlendirmesi">
          <div className="card">
            <p className="text-sm text-slate-300 whitespace-pre-wrap leading-relaxed">{llm_summary}</p>
          </div>
        </Section>
      )}

      {/* Pipeline YAML */}
      {pipeline_yaml && (
        <Section icon="⚙️" title="Önerilen CI/CD Pipeline">
          <PipelineViewer yaml={pipeline_yaml} />
          {job_id && (
            <a
              href={getJobYamlUrl(job_id)}
              download="pipeline.yml"
              className="btn-ghost text-sm mt-2 inline-flex items-center gap-2"
            >
              ⬇ YAML'ı İndir
            </a>
          )}
        </Section>
      )}

      {/* İndirme butonları */}
      {job_id && (
        <Section icon="⬇️" title="Raporu İndir">
          <div className="flex flex-wrap gap-3">
            <a href={getJobYamlUrl(job_id)} download="pipeline.yml"
               className="btn-ghost text-sm flex items-center gap-1.5">
              ⚙️ Pipeline YAML
            </a>
            <a href={`/api/job/${job_id}/report.md`} download={`report-${job_id.slice(0,8)}.md`}
               className="btn-ghost text-sm flex items-center gap-1.5">
              📄 Markdown Rapor
            </a>
            <a href={`/api/job/${job_id}/report.pdf`} target="_blank" rel="noopener noreferrer"
               className="btn-ghost text-sm flex items-center gap-1.5">
              📑 PDF Rapor
            </a>
          </div>
        </Section>
      )}

      {/* Alt butonlar */}
      <div className="flex gap-3 pt-2">
        <button className="btn-primary flex-1" onClick={() => navigate('/')}>← Yeni Analiz</button>
        <button className="btn-ghost flex-1" onClick={() => navigate('/history')}>Geçmişi Görüntüle</button>
      </div>
    </div>
  );
}

// --- Ana ResultPage ---
export default function ResultPage() {
  const { state } = useLocation();
  const navigate = useNavigate();

  if (!state?.data) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-24 text-center">
        <p className="text-5xl mb-4">🤷</p>
        <p className="text-slate-400 mb-6">Görüntülenecek analiz sonucu yok.</p>
        <button className="btn-primary" onClick={() => navigate('/')}>Yeni Analiz</button>
      </div>
    );
  }

  const { type, data, repoUrl, platform } = state;
  const repoName = repoUrl?.replace('https://github.com/', '');

  // Multi-agent job sonucu ayrı görünümde
  if (type === 'job') {
    const repoName = (state.repoUrl ?? data.repo_url ?? '').replace('https://github.com/', '');
    return (
      <div className="max-w-2xl mx-auto px-4 py-10">
        <div className="mb-6">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-900/40 border border-blue-700/50 text-blue-300 text-xs font-semibold mb-2">
            🤖 Multi-Agent Analiz
          </span>
          <h1 className="text-xl font-bold text-white break-all">{repoName}</h1>
        </div>
        <JobResultView data={data} navigate={navigate} />
      </div>
    );
  }

  const TYPE_LABELS = {
    analyze:  { icon: '🔍', label: 'Hızlı Analiz' },
    auto:     { icon: '⚙️', label: 'Pipeline Üretimi' },
    full:     { icon: '📊', label: 'Tam Analiz' },
    security: { icon: '🛡️', label: 'Güvenlik Taraması' },
  };
  const tl = TYPE_LABELS[type] ?? { icon: '📋', label: 'Analiz' };
  const pl = platform ? PLATFORM_LABELS[platform] : null;

  return (
    <div className="max-w-2xl mx-auto px-4 py-10 space-y-8">
      {/* Başlık */}
      <div>
        <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-700 text-slate-300 text-xs font-semibold">
              {tl.icon} {tl.label}
            </span>
            {pl && (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-violet-900/40 border border-violet-700/50 text-violet-300 text-xs font-semibold">
                {pl.icon} {pl.label}
              </span>
            )}
          </div>
          <span className="text-xs text-slate-500">
            {data.analysis_id ? `#${data.analysis_id}` : ''}
          </span>
        </div>
        <h1 className="text-xl font-bold text-white break-all">{repoName}</h1>
      </div>

      {/* Analiz özeti — tüm modlarda göster */}
      {(data.analysis || data.language || data.has_tests !== undefined) && (
        <AnalysisCard data={data} type={type} />
      )}

      {/* Uyum skoru — full modunda */}
      {data.score !== undefined && <ComplianceCard data={data} />}

      {/* Risk raporu — security modunda */}
      {data.risk_score !== undefined && <RiskCard data={data} />}

      {/* Pipeline — auto veya full modunda */}
      {data.pipeline && (
        <Section icon="⚙️" title="Üretilen CI/CD Pipeline">
          <PipelineViewer yaml={data.pipeline} />
        </Section>
      )}

      {/* Alt butonlar */}
      <div className="flex gap-3 pt-2">
        <button className="btn-primary flex-1" onClick={() => navigate('/')}>
          ← Yeni Analiz
        </button>
        <button className="btn-ghost flex-1" onClick={() => navigate('/history')}>
          Geçmişi Görüntüle
        </button>
      </div>
    </div>
  );
}
