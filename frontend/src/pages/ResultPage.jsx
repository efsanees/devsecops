import { useEffect, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import DsommDashboard from '../components/DsommDashboard.jsx';
import FindingsTable from '../components/FindingsTable.jsx';
import OwaspChart from '../components/OwaspChart.jsx';
import PipelineViewer from '../components/PipelineViewer.jsx';
import { getJob, getJobYamlUrl, getJobReportMdUrl, getJobReportPdfUrl } from '../api/client.js';

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

function Section({ icon, title, subtitle, children }) {
  return (
    <section className="space-y-3">
      <div>
        <h2 className="flex items-center gap-2 text-base font-semibold text-white">
          <span>{icon}</span>
          {title}
        </h2>
        {subtitle && <p className="text-xs text-slate-500 mt-0.5 ml-6">{subtitle}</p>}
      </div>
      {children}
    </section>
  );
}

function CopyLinkButton({ jobId }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    const url = `${window.location.origin}/result/${jobId}`;
    navigator.clipboard.writeText(url).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };
  return (
    <button
      onClick={handleCopy}
      className="text-xs px-2.5 py-1 rounded bg-slate-700 text-slate-300 hover:bg-slate-600 transition-colors"
    >
      {copied ? '✓ Kopyalandı' : '🔗 Bağlantıyı Kopyala'}
    </button>
  );
}

function JobResultView({ data, navigate }) {
  const { profile = {}, dsomm, findings = {}, llm_summary, pipeline_yaml, job_id, elapsed_seconds } = data;

  const totalFindings =
    (findings.sast?.length ?? 0) +
    (findings.sca?.length ?? 0) +
    (findings.secret?.length ?? 0);

  return (
    <div className="space-y-8">
      <Section
        icon="🔍"
        title="Proje Profili"
        subtitle="ProjectProfiler agent'ı tarafından GitHub API üzerinden tespit edildi."
      >
        <div className="card">
          <InfoChip label="Dil"              value={profile.language          ?? '—'} />
          <InfoChip label="Framework"        value={profile.framework         ?? '—'} />
          <InfoChip label="Paket Yöneticisi" value={profile.package_manager   ?? '—'} />
          <InfoChip
            label="Test Dosyaları"
            value={profile.has_tests ? 'Var' : 'Yok — DSOMM Testing puanını etkiler'}
            ok={profile.has_tests}
          />
          <InfoChip
            label="Docker"
            value={profile.has_docker ? 'Var' : 'Yok — DSOMM Build & Deployment puanını etkiler'}
            ok={profile.has_docker}
          />
          {elapsed_seconds && (
            <InfoChip label="Toplam Analiz Süresi" value={`${elapsed_seconds} saniye`} />
          )}
        </div>
      </Section>

      {dsomm && (
        <Section
          icon="📊"
          title="Güvenlik Olgunluk Skoru (DSOMM)"
          subtitle="DevSecOps Maturity Model — 5 kategoride 0-100 arası puanlama. Kategori barlarına tıklayarak detaylı kriterleri görebilirsiniz."
        >
          <div className="card">
            <DsommDashboard dsomm={dsomm} />
          </div>
        </Section>
      )}

      {totalFindings > 0 && (
        <Section
          icon="📋"
          title="OWASP Top 10 Haritalama"
          subtitle="Tespit edilen bulgular OWASP Top 10 (2021) güvenlik kategorilerine haritalandı. Bu haritalama hangi tür güvenlik risklerinin yoğun olduğunu gösterir."
        >
          <div className="card">
            <OwaspChart findings={findings} />
          </div>
        </Section>
      )}

      <Section
        icon="🛡️"
        title={`Güvenlik Bulguları ${totalFindings > 0 ? `(${totalFindings})` : ''}`}
        subtitle="SAST (kod), SCA (bağımlılık), Gizli (hardcoded credential) ve Pipeline (CI/CD eksiklikleri) sekmeleri. 🤖 AI Fix butonu olan bulgularda somut düzeltme önerisi var."
      >
        <div className="card">
          <FindingsTable findings={findings} />
        </div>
      </Section>

      {llm_summary && (
        <Section
          icon="🤖"
          title="AI Risk Değerlendirmesi"
          subtitle="Groq (Llama-3.3-70b) tarafından üretildi. Bulgular özetlenerek öncelikli eylem önerileri sunuldu."
        >
          <div className="card">
            <p className="text-sm text-slate-300 whitespace-pre-wrap leading-relaxed">{llm_summary}</p>
          </div>
        </Section>
      )}

      {pipeline_yaml && (
        <Section
          icon="⚙️"
          title="Önerilen CI/CD Pipeline"
          subtitle="Projeye özel oluşturuldu. .github/workflows/ci.yml olarak repo'nuzа ekleyebilirsiniz."
        >
          <PipelineViewer yaml={pipeline_yaml} />
        </Section>
      )}

      {job_id && (
        <Section
          icon="⬇️"
          title="Raporu İndir"
          subtitle="YAML: pipeline dosyası · Markdown: tüm bulgular + özet metin · PDF: baskıya hazır rapor"
        >
          <div className="flex flex-wrap gap-3">
            <a href={getJobYamlUrl(job_id)} download="pipeline.yml"
               className="btn-ghost text-sm flex items-center gap-1.5">
              ⚙️ Pipeline YAML
            </a>
            <a href={getJobReportMdUrl(job_id)} download={`report-${job_id.slice(0,8)}.md`}
               className="btn-ghost text-sm flex items-center gap-1.5">
              📄 Markdown Rapor
            </a>
            <a href={getJobReportPdfUrl(job_id)} target="_blank" rel="noopener noreferrer"
               className="btn-ghost text-sm flex items-center gap-1.5">
              📑 PDF Rapor
            </a>
          </div>
        </Section>
      )}

      <div className="flex gap-3 pt-2">
        <button className="btn-primary flex-1" onClick={() => navigate('/')}>← Yeni Analiz</button>
        <button className="btn-ghost flex-1" onClick={() => navigate('/history')}>Geçmişi Görüntüle</button>
      </div>
    </div>
  );
}

export default function ResultPage() {
  const { jobId } = useParams();
  const { state } = useLocation();
  const navigate = useNavigate();

  const [data, setData]       = useState(state?.data ?? null);
  const [repoUrl, setRepoUrl] = useState(state?.repoUrl ?? state?.data?.repo_url ?? '');
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState('');

  // URL'de jobId varsa ve elimizde data yoksa (refresh durumu) backend'den çek
  useEffect(() => {
    if (jobId && !data) {
      setLoading(true);
      getJob(jobId).then((res) => {
        setLoading(false);
        if (!res.ok) {
          setError(res.error);
          return;
        }
        if (res.data?.status !== 'completed' || !res.data.result) {
          setError('Bu job henüz tamamlanmadı veya sonuç bulunamadı.');
          return;
        }
        setData(res.data.result);
        setRepoUrl(res.data.repo_url ?? '');
      });
    }
  }, [jobId, data]);

  if (loading) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-24 text-center">
        <p className="text-slate-500 animate-pulse">Sonuç yükleniyor...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-24 text-center">
        <p className="text-5xl mb-4">⚠️</p>
        <p className="text-red-300 mb-6">{error}</p>
        <button className="btn-primary" onClick={() => navigate('/history')}>Geçmişe Dön</button>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-24 text-center">
        <p className="text-5xl mb-4">🤷</p>
        <p className="text-slate-400 mb-6">Görüntülenecek analiz sonucu yok.</p>
        <button className="btn-primary" onClick={() => navigate('/')}>Yeni Analiz</button>
      </div>
    );
  }

  const repoName = (repoUrl || data?.repo_url || '').replace('https://github.com/', '');
  const displayJobId = jobId ?? data?.job_id;

  return (
    <div className="max-w-2xl mx-auto px-4 py-10">
      <div className="mb-6 flex items-start justify-between gap-3">
        <div>
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-900/40 border border-blue-700/50 text-blue-300 text-xs font-semibold mb-2">
            🤖 Multi-Agent Analiz
          </span>
          <h1 className="text-xl font-bold text-white break-all">{repoName}</h1>
        </div>
        {displayJobId && <CopyLinkButton jobId={displayJobId} />}
      </div>
      <JobResultView data={data} navigate={navigate} />
    </div>
  );
}
