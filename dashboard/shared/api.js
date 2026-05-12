const API_BASE = 'http://localhost:5001/api';

async function apiFetch(endpoint, options = {}) {
  try {
    const res = await fetch(API_BASE + endpoint, {
      headers: { 'Content-Type': 'application/json' },
      ...options
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    return await res.json();
  } catch (e) {
    if (e.message.includes('Failed to fetch') || e.message.includes('Could not connect') || e.message.includes('NetworkError') || e.message.includes('fetch')) {
      throw new Error('API offline — start with: python3 ~/command-center/core/api/app.py');
    }
    throw e;
  }
}

const API = {
  status: () => apiFetch('/status'),

  getTasks: (done) => apiFetch('/tasks' + (done !== undefined ? `?done=${done}` : '')),
  addTask: (text, tag, priority) => apiFetch('/tasks', { method: 'POST', body: JSON.stringify({ text, tag, priority }) }),
  updateTask: (id, fields) => apiFetch(`/tasks/${id}`, { method: 'PATCH', body: JSON.stringify(fields) }),
  deleteTask: (id) => apiFetch(`/tasks/${id}`, { method: 'DELETE' }),

  getTeam: () => apiFetch('/team'),
  updateMember: (id, fields) => apiFetch(`/team/${id}`, { method: 'PATCH', body: JSON.stringify(fields) }),

  getSpoc: (status) => apiFetch('/spoc' + (status ? `?status=${status}` : '')),
  addSpoc: (entry) => apiFetch('/spoc', { method: 'POST', body: JSON.stringify(entry) }),
  updateSpoc: (id, fields) => apiFetch(`/spoc/${id}`, { method: 'PATCH', body: JSON.stringify(fields) }),

  getProjects: () => apiFetch('/projects'),
  updateProject: (id, fields) => apiFetch(`/projects/${id}`, { method: 'PATCH', body: JSON.stringify(fields) }),
  updateMilestone: (id, milestone_text, status) => apiFetch(`/projects/${id}/milestones`, { method: 'PATCH', body: JSON.stringify({ milestone_text, status }) }),

  getReminders: () => apiFetch('/reminders'),
  addReminder: (message, send_at, channel) => apiFetch('/reminders', { method: 'POST', body: JSON.stringify({ message, send_at, channel }) }),

  getWeekly: () => apiFetch('/weekly'),
  addWeekly: (type, content, week) => apiFetch('/weekly', { method: 'POST', body: JSON.stringify({ type, content, week }) }),
};

function startAutoRefresh(refreshFn, intervalMs = 30000) {
  refreshFn();
  return setInterval(refreshFn, intervalMs);
}

function showOfflineBanner() {
  if (document.getElementById('api-banner')) return;
  const banner = document.createElement('div');
  banner.id = 'api-banner';
  banner.style.cssText = 'position:fixed;top:52px;left:0;right:0;background:#d63a2f;color:#fff;font-family:monospace;font-size:11px;padding:8px 40px;z-index:999;display:flex;align-items:center;justify-content:space-between;';
  banner.innerHTML = '⚠ API server offline — data is not live. Start: python3 ~/command-center/core/api/app.py <span style="cursor:pointer;opacity:.7" onclick="this.parentElement.remove()">×</span>';
  document.body.prepend(banner);
}

function hideOfflineBanner() {
  document.getElementById('api-banner')?.remove();
}
