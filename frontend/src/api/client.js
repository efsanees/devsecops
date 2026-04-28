import axios from 'axios';

const http = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? '/api',
  timeout: 120_000,
  headers: { 'Content-Type': 'application/json' },
});

function extractError(err) {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (detail?.message) return detail.message;
  return err?.message ?? 'Bilinmeyen hata';
}

// Repo bilgilerini analiz et (dil, framework, test, docker)
export async function analyzeRepo(repoUrl, token = '') {
  try {
    const { data } = await http.post('/analyze', { repo_url: repoUrl, token });
    return { ok: true, data };
  } catch (err) {
    return { ok: false, error: extractError(err) };
  }
}

// Pipeline üret + kaydet
export async function generatePipeline(repoUrl, token = '', platform = 'github_actions') {
  try {
    const { data } = await http.post('/auto', { repo_url: repoUrl, token, platform });
    return { ok: true, data };
  } catch (err) {
    return { ok: false, error: extractError(err) };
  }
}

// Tam analiz: kod + pipeline + uyum skoru
export async function fullAnalysis(repoUrl, token = '', platform = 'github_actions') {
  try {
    const { data } = await http.post('/full', { repo_url: repoUrl, token, platform });
    return { ok: true, data };
  } catch (err) {
    return { ok: false, error: extractError(err) };
  }
}

// Güvenlik analizi: SAST + SCA + risk raporu
export async function securityAnalysis(repoUrl, token = '') {
  try {
    const { data } = await http.post('/security', { repo_url: repoUrl, token });
    return { ok: true, data };
  } catch (err) {
    return { ok: false, error: extractError(err) };
  }
}

// Geçmiş analizler
export async function getHistory(limit = 30) {
  try {
    const { data } = await http.get('/history', { params: { limit } });
    return { ok: true, data };
  } catch (err) {
    return { ok: false, error: extractError(err) };
  }
}

// Tek analiz detayı
export async function getHistoryDetail(id) {
  try {
    const { data } = await http.get(`/history/${id}`);
    return { ok: true, data };
  } catch (err) {
    return { ok: false, error: extractError(err) };
  }
}

// ── Multi-agent job API ───────────────────────────────────────────────────────

// Orchestrator'ı başlatır, anında job_id döner
export async function startJob(repoUrl, token = '', platform = 'github_actions') {
  try {
    const { data } = await http.post('/job', { repo_url: repoUrl, token, platform });
    return { ok: true, data };
  } catch (err) {
    return { ok: false, error: extractError(err) };
  }
}

// Job durumu ve sonucunu döner
export async function getJob(jobId) {
  try {
    const { data } = await http.get(`/job/${jobId}`);
    return { ok: true, data };
  } catch (err) {
    return { ok: false, error: extractError(err) };
  }
}

// Pipeline YAML URL'i döner (doğrudan href olarak kullanılabilir)
export function getJobYamlUrl(jobId) {
  const base = import.meta.env.VITE_API_URL ?? '/api';
  return `${base}/job/${jobId}/yaml`;
}

// WebSocket bağlantısı kur, event'leri onMessage'a ilet.
// Döner: bağlantıyı kesen close() fonksiyonu.
export function subscribeJobProgress(jobId, onMessage, onClose) {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host  = window.location.host;
  const url   = `${proto}//${host}/ws/${jobId}`;

  const ws = new WebSocket(url);

  ws.onmessage = (e) => {
    try {
      const event = JSON.parse(e.data);
      onMessage(event);
    } catch {
      // JSON değilse yoksay
    }
  };

  ws.onclose = () => onClose?.('closed');
  ws.onerror = () => onClose?.('error');

  return () => ws.close();
}
