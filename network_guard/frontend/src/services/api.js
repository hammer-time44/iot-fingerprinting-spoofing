// API service layer for Network Defense Lab

const API_BASE = '/api';

export async function checkBackendHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    return { status: 'offline', error: err.message };
  }
}

export async function getModelInfo() {
  const res = await fetch(`${API_BASE}/model/info`);
  if (!res.ok) throw new Error('Failed to load model info');
  return await res.json();
}

export async function getTopology() {
  const res = await fetch(`${API_BASE}/topology`);
  if (!res.ok) throw new Error('Failed to load topology');
  return await res.json();
}

export async function getHosts() {
  const res = await fetch(`${API_BASE}/hosts`);
  if (!res.ok) throw new Error('Failed to load hosts state');
  return await res.json();
}

export async function startSimulation(scenario, params = {}, speed = 1.0) {
  const res = await fetch(`${API_BASE}/sim/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario, params, speed })
  });
  if (!res.ok) throw new Error('Failed to start simulation');
  return await res.json();
}

export async function stopSimulation() {
  const res = await fetch(`${API_BASE}/sim/stop`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to stop simulation');
  return await res.json();
}

export async function resetSimulation() {
  const res = await fetch(`${API_BASE}/sim/reset`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to reset simulation');
  return await res.json();
}

export async function setSpeed(speed) {
  const res = await fetch(`${API_BASE}/sim/speed`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ speed })
  });
  if (!res.ok) throw new Error('Failed to set speed');
  return await res.json();
}

export async function updateTau(tau) {
  const res = await fetch(`${API_BASE}/config/tau`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tau })
  });
  if (!res.ok) throw new Error('Failed to update tau');
  return await res.json();
}

export async function getEvents(limit = 100, hostId = null) {
  const url = hostId ? `${API_BASE}/events?limit=${limit}&host_id=${hostId}` : `${API_BASE}/events?limit=${limit}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to load events');
  return await res.json();
}

export async function runBenchmark(nTrials = 20, maxTicks = 15, tau = null) {
  const res = await fetch(`${API_BASE}/benchmark/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ n_trials: nTrials, max_ticks_per_trial: maxTicks, tau })
  });
  if (!res.ok) throw new Error('Failed to run benchmark');
  return await res.json();
}

export async function getBenchmarkResults() {
  const res = await fetch(`${API_BASE}/benchmark/results`);
  if (!res.ok) throw new Error('Failed to load benchmark results');
  return await res.json();
}

export async function getFullReport() {
  const res = await fetch(`${API_BASE}/report`);
  if (!res.ok) throw new Error('Failed to load report');
  return await res.json();
}
