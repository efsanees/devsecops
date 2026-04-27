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
