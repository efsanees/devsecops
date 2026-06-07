import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { getJob, subscribeJobProgress } from '../api/client.js';
import AgentProgress from '../components/AgentProgress.jsx';

const AGENT_DEFS = [
  {
    key:   'project_profiler',
    label: 'Proje Profili',
    icon:  '🔍',
    desc:  'Dil, framework, paket yöneticisi ve dosya yapısını tespit eder.',
  },
  {
    key:   'sast',
    label: 'Kod Analizi (SAST)',
    icon:  '🔬',
    desc:  'Bandit + Semgrep ile statik kod güvenlik analizi yapar.',
  },
  {
    key:   'sca',
    label: 'Bağımlılık Taraması',
    icon:  '📦',
    desc:  "OSV.dev + Trivy ile bağımlılık CVE'lerini tarar.",
  },
  {
    key:   'secret_detection',
    label: 'Gizli Bilgi Taraması',
    icon:  '🔑',
    desc:  'Gitleaks ile hardcoded API key, şifre ve token arar.',
  },
  {
    key:   'pipeline_analyzer',
    label: 'Pipeline Analizi',
    icon:  '⚙️',
    desc:  'Mevcut CI/CD dosyalarını okur, eksik güvenlik adımlarını tespit eder.',
  },
];

const INITIAL_AGENTS = Object.fromEntries(
  AGENT_DEFS.map(({ key }) => [key, { status: 'pending', data: null, error: null }])
);

function completedCount(agents) {
  return Object.values(agents).filter((a) => a.status === 'completed' || a.status === 'failed').length;
}

export default function ProgressPage() {
  const { jobId }  = useParams();
  const navigate   = useNavigate();

  const [agents,   setAgents]   = useState(INITIAL_AGENTS);
  const [message,  setMessage]  = useState('Analiz başlatılıyor…');
  const [wsState,  setWsState]  = useState('connecting');
  const closeWsRef  = useRef(null);
  const jobDoneRef  = useRef(false);

  const goToResult = (repoUrl, result) => {
    navigate(`/result/${jobId}`, { state: { type: 'job', data: result, repoUrl } });
  };

  const checkJobAlready = async () => {
    const { ok, data } = await getJob(jobId);
    if (ok && data?.status === 'completed' && data?.result) {
      jobDoneRef.current = true;
      goToResult(data.repo_url, data.result);
      return true;
    }
    if (ok && data?.status === 'failed') {
      setMessage(`Analiz başarısız: ${data.error ?? 'Bilinmeyen hata'}`);
      setWsState('error');
      return true;
    }
    return false;
  };

  const connect = () => {
    setWsState('connecting');
    closeWsRef.current = subscribeJobProgress(
      jobId,
      handleEvent,
      (reason) => {
        if (jobDoneRef.current) return;
        setWsState(reason === 'error' ? 'error' : 'closed');
      },
    );
    setWsState('open');
  };

  useEffect(() => {
    checkJobAlready().then((done) => { if (!done) connect(); });
    return () => closeWsRef.current?.();
  }, [jobId]);

  const handleEvent = (event) => {
    const { type, agent, data, error, message: msg } = event;
    if (type === 'agent_started') {
      setAgents((prev) => ({ ...prev, [agent]: { ...prev[agent], status: 'running' } }));
    }
    if (type === 'agent_completed') {
      setAgents((prev) => ({ ...prev, [agent]: { status: 'completed', data: data ?? null, error: null } }));
    }
    if (type === 'agent_failed') {
      setAgents((prev) => ({ ...prev, [agent]: { status: 'failed', data: null, error: error ?? 'Hata oluştu' } }));
    }
    if (type === 'job_status' && msg) setMessage(msg);
    if (type === 'job_completed') {
      jobDoneRef.current = true;
      setMessage('Analiz tamamlandı! Rapora yönlendiriliyorsunuz…');
      getJob(jobId).then(({ ok, data: jobData }) => {
        if (ok && jobData?.result) goToResult(jobData.repo_url, jobData.result);
      });
    }
    if (type === 'job_failed') {
      setMessage(`Analiz başarısız: ${error ?? 'Bilinmeyen hata'}`);
      setWsState('error');
    }
  };

  const done  = completedCount(agents);
  const total = AGENT_DEFS.length;
  const pct   = Math.round((done / total) * 100);

  return (
    <div className="max-w-xl mx-auto px-4 py-16">
      {/* Başlık */}
      <div className="text-center mb-12">
        <div
          className="text-5xl mb-5 inline-block"
          style={{
            filter: 'drop-shadow(0 0 20px rgba(99,102,241,0.6))',
            animation: 'float 4s ease-in-out infinite',
          }}
        >
          🛡️
        </div>
        <h1 className="text-2xl font-bold mb-2" style={{ color: '#e2e8f0' }}>Analiz Çalışıyor</h1>
        <p className="text-sm mb-2" style={{ color: '#64748b' }}>
          5 agent paralel olarak reponuzu tarıyor.
        </p>
        <p className="text-xs font-mono" style={{ color: '#334155' }}>{jobId}</p>
      </div>

      {/* İlerleme çubuğu */}
      <div
        className="mb-8 p-5 rounded-2xl"
        style={{
          background: 'rgba(10,16,34,0.75)',
          backdropFilter: 'blur(16px)',
          border: '1px solid rgba(99,102,241,0.12)',
          boxShadow: '0 4px 24px rgba(0,0,0,0.3)',
        }}
      >
        <div className="flex justify-between text-xs mb-3">
          <span style={{ color: '#94a3b8' }}>{message}</span>
          <span style={{ color: '#6366f1', fontWeight: 600 }}>{done}/{total} agent</span>
        </div>
        <div
          className="h-2 rounded-full overflow-hidden"
          style={{ background: 'rgba(30,45,74,0.8)' }}
        >
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{
              width: `${pct}%`,
              background: 'linear-gradient(90deg, #4f46e5, #7c3aed, #6366f1)',
              boxShadow: pct > 0 ? '0 0 12px rgba(99,102,241,0.5)' : 'none',
            }}
          />
        </div>
        <div className="flex justify-between mt-2">
          <span className="text-[11px]" style={{ color: '#334155' }}>0%</span>
          <span className="text-[11px] font-semibold" style={{ color: pct === 100 ? '#4ade80' : '#6366f1' }}>
            {pct}%
          </span>
          <span className="text-[11px]" style={{ color: '#334155' }}>100%</span>
        </div>
      </div>

      {/* Agent kartları */}
      <div className="space-y-3">
        {AGENT_DEFS.map(({ key, label, icon, desc }) => (
          <AgentProgress
            key={key}
            name={key}
            label={label}
            icon={icon}
            desc={desc}
            status={agents[key].status}
            data={agents[key].data}
            error={agents[key].error}
          />
        ))}
      </div>

      {/* Bilgi notu */}
      <p className="text-xs text-center mt-8" style={{ color: '#334155' }}>
        SAST, SCA, Secret ve Pipeline agent'ları aynı anda çalışır — ortalama 30-90 saniye sürer.
      </p>

      {/* Bağlantı hatası */}
      {(wsState === 'closed' || wsState === 'error') && !jobDoneRef.current && (
        <div
          className="mt-8 p-5 rounded-2xl text-center space-y-4"
          style={{
            background: 'rgba(239,68,68,0.07)',
            border: '1px solid rgba(239,68,68,0.2)',
          }}
        >
          <p className="text-sm" style={{ color: '#fca5a5' }}>
            {wsState === 'error' ? 'Bağlantı hatası oluştu.' : 'Bağlantı kesildi.'}
          </p>
          <button onClick={connect} className="btn-primary text-sm px-6 py-2.5 rounded-xl">
            Yeniden Bağlan
          </button>
        </div>
      )}

      <style>{`
        @keyframes float {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-8px); }
        }
      `}</style>
    </div>
  );
}
