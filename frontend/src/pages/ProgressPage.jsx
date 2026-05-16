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
    desc:  'OSV.dev + Trivy ile bağımlılık CVE\'lerini tarar.',
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
      <div className="text-center mb-10">
        <div className="text-5xl mb-4">🛡️</div>
        <h1 className="text-2xl font-bold text-white mb-2">Analiz Çalışıyor</h1>
        <p className="text-slate-400 text-sm mb-1">
          5 agent paralel olarak reponuzu tarıyor.
        </p>
        <p className="text-slate-600 text-xs font-mono">{jobId}</p>
      </div>

      {/* İlerleme çubuğu */}
      <div className="mb-8">
        <div className="flex justify-between text-xs text-slate-400 mb-2">
          <span>{message}</span>
          <span>{done}/{total} agent tamamlandı</span>
        </div>
        <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-500 transition-all duration-500 rounded-full"
            style={{ width: `${pct}%` }}
          />
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
      <p className="text-xs text-slate-600 text-center mt-6">
        SAST, SCA, Secret ve Pipeline agent'ları aynı anda çalışır — ortalama 30-90 saniye sürer.
      </p>

      {/* Bağlantı hatası */}
      {(wsState === 'closed' || wsState === 'error') && !jobDoneRef.current && (
        <div className="mt-8 p-4 bg-red-900/30 border border-red-700 rounded-xl text-center space-y-3">
          <p className="text-red-300 text-sm">
            {wsState === 'error' ? 'Bağlantı hatası oluştu.' : 'Bağlantı kesildi.'}
          </p>
          <button onClick={connect} className="btn-primary text-sm px-5 py-2">
            Yeniden Bağlan
          </button>
        </div>
      )}
    </div>
  );
}
