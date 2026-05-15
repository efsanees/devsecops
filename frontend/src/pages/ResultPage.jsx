import { useLocation, useNavigate } from 'react-router-dom';
import DsommDashboard from '../components/DsommDashboard.jsx';
import FindingsTable from '../components/FindingsTable.jsx';
import OwaspChart from '../components/OwaspChart.jsx';
import PipelineViewer from '../components/PipelineViewer.jsx';
import { getJobYamlUrl } from '../api/client.js';

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
          <InfoChip label="Dil"              value={profile.language          ?? '—'} />
          <InfoChip label="Framework"        value={profile.framework         ?? '—'} />
          <InfoChip label="Paket Yöneticisi" value={profile.package_manager   ?? '—'} />
          <InfoChip label="Test Dosyaları"   value={profile.has_tests ? 'Var' : 'Yok'} ok={profile.has_tests} />
          <InfoChip label="Docker"           value={profile.has_docker ? 'Var' : 'Yok'} ok={profile.has_docker} />
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

      {/* OWASP Top 10 dağılım grafiği */}
      {totalFindings > 0 && (
        <Section icon="📋" title="OWASP Top 10 Haritalama">
          <div className="card">
            <OwaspChart findings={findings} />
          </div>
        </Section>
      )}

      {/* Bulgular */}
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

  const repoName = (state.repoUrl ?? state.data?.repo_url ?? '').replace('https://github.com/', '');

  return (
    <div className="max-w-2xl mx-auto px-4 py-10">
      <div className="mb-6">
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-900/40 border border-blue-700/50 text-blue-300 text-xs font-semibold mb-2">
          🤖 Multi-Agent Analiz
        </span>
        <h1 className="text-xl font-bold text-white break-all">{repoName}</h1>
      </div>
      <JobResultView data={state.data} navigate={navigate} />
    </div>
  );
}
