const API = '/api';
let currentProjectId = null;
let currentProjectName = null;

// ---------------------------------------------------------------------------
// Routing
// ---------------------------------------------------------------------------

function navigate(path) {
  window.location.hash = path;
}

window.addEventListener('hashchange', handleRoute);
window.addEventListener('load', handleRoute);

function handleRoute() {
  const hash = window.location.hash.slice(1) || 'projects';
  const parts = hash.split('/');

  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));

  if (hash === 'projects' || !hash) {
    document.getElementById('view-projects').classList.add('active');
    loadProjects();
  } else if (parts[0] === 'project' && parts[1]) {
    currentProjectId = parts[1];
    document.getElementById('view-project').classList.add('active');
    loadProjectDetail(currentProjectId);
  } else if (parts[0] === 'answer' && parts[1]) {
    document.getElementById('view-answer').classList.add('active');
    loadAnswer(parts[1]);
  }
}

// ---------------------------------------------------------------------------
// Projects
// ---------------------------------------------------------------------------

async function loadProjects() {
  const list = document.getElementById('project-list');
  list.innerHTML = '<div class="loading"><span class="spinner"></span>Loading...</div>';
  try {
    const res = await fetch(`${API}/projects`);
    const projects = await res.json();
    if (!projects.length) {
      list.innerHTML = '<div class="empty-state"><div class="icon">📂</div><div>No projects yet. Create one above.</div></div>';
      return;
    }
    list.innerHTML = projects.map(p => `
      <div class="card project-link" onclick="navigate('project/${p.id}')">
        <strong>${esc(p.name)}</strong>
        ${p.description ? `<div style="color:#6b7280;font-size:0.85rem">${esc(p.description)}</div>` : ''}
        <div style="font-size:0.75rem;color:#9ca3af;margin-top:4px">${fmtDate(p.created_at)}</div>
      </div>
    `).join('');
  } catch (e) {
    list.innerHTML = `<div class="error-box">Failed to load projects: ${esc(e.message)}</div>`;
  }
}

async function createProject() {
  const name = document.getElementById('new-project-name').value.trim();
  if (!name) { alert('Project name is required'); return; }
  const desc = document.getElementById('new-project-desc').value.trim();

  const res = await fetch(`${API}/projects`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, description: desc || null }),
  });
  if (res.ok) {
    document.getElementById('new-project-name').value = '';
    document.getElementById('new-project-desc').value = '';
    loadProjects();
  } else {
    const err = await res.json();
    alert('Error: ' + (err.detail?.message || JSON.stringify(err)));
  }
}

// ---------------------------------------------------------------------------
// Project Detail
// ---------------------------------------------------------------------------

async function loadProjectDetail(projectId) {
  try {
    const res = await fetch(`${API}/projects/${projectId}`);
    if (!res.ok) { navigate('projects'); return; }
    const project = await res.json();
    document.getElementById('project-title').textContent = project.name;
    currentProjectName = project.name;
    document.getElementById('back-to-project').onclick = () => navigate(`project/${projectId}`);
    loadDocuments(projectId);
  } catch (e) {
    console.error(e);
  }
}

function showTab(tab) {
  document.querySelectorAll('.tab').forEach((t, i) => t.classList.remove('active'));
  ['tab-documents', 'tab-ask'].forEach(id => {
    document.getElementById(id).style.display = 'none';
  });
  if (tab === 'documents') {
    document.getElementById('tab-documents').style.display = 'block';
    document.querySelectorAll('.tab')[0].classList.add('active');
    loadDocuments(currentProjectId);
  } else {
    document.getElementById('tab-ask').style.display = 'block';
    document.querySelectorAll('.tab')[1].classList.add('active');
  }
}

async function loadDocuments(projectId) {
  const list = document.getElementById('document-list');
  try {
    const res = await fetch(`${API}/projects/${projectId}/documents`);
    const docs = await res.json();
    if (!docs.length) {
      list.innerHTML = '<div class="empty-state"><div>No documents uploaded yet.</div></div>';
      return;
    }
    list.innerHTML = docs.map(d => `
      <div class="card">
        <strong>${esc(d.title)}</strong>
        <span style="margin-left:8px;font-size:0.75rem;color:#6b7280">${esc(d.source_type)}</span>
        <div style="font-size:0.75rem;color:#9ca3af;margin-top:4px">${fmtDate(d.created_at)}</div>
      </div>
    `).join('');
  } catch (e) {
    list.innerHTML = `<div class="error-box">${esc(e.message)}</div>`;
  }
}

function handleFileSelect(event) {
  const file = event.target.files[0];
  if (file) uploadFile(file);
}

async function uploadFile(file) {
  const status = document.getElementById('upload-status');
  status.innerHTML = '<span class="spinner"></span>Uploading...';

  const form = new FormData();
  form.append('file', file);

  try {
    const res = await fetch(`${API}/projects/${currentProjectId}/documents`, {
      method: 'POST',
      body: form,
    });
    if (res.ok) {
      status.innerHTML = '<span style="color:green">✓ Uploaded successfully</span>';
      loadDocuments(currentProjectId);
    } else {
      const err = await res.json();
      status.innerHTML = `<span style="color:red">✗ ${esc(err.detail?.message || 'Upload failed')}</span>`;
    }
  } catch (e) {
    status.innerHTML = `<span style="color:red">✗ ${esc(e.message)}</span>`;
  }
}

async function buildIndex() {
  const status = document.getElementById('index-status');
  status.innerHTML = '<span class="spinner"></span>Building index (this may take a while)...';
  try {
    const res = await fetch(`${API}/projects/${currentProjectId}/index`, { method: 'POST' });
    if (res.ok) {
      status.innerHTML = '<span style="color:green">✓ Index built successfully</span>';
    } else {
      const err = await res.json();
      status.innerHTML = `<span style="color:red">✗ ${esc(err.detail?.message || 'Index build failed')}</span>`;
    }
  } catch (e) {
    status.innerHTML = `<span style="color:red">✗ ${esc(e.message)}</span>`;
  }
}

// ---------------------------------------------------------------------------
// Q&A
// ---------------------------------------------------------------------------

async function submitQuestion() {
  const question = document.getElementById('question-input').value.trim();
  if (!question) return;

  const area = document.getElementById('answer-area');
  area.innerHTML = '<div class="loading"><span class="spinner"></span>Processing your question...</div>';

  try {
    const res = await fetch(`${API}/projects/${currentProjectId}/queries`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });
    const data = await res.json();

    if (!res.ok) {
      area.innerHTML = `<div class="error-box"><strong>Error:</strong> ${esc(data.detail?.message || JSON.stringify(data.detail))}</div>`;
      return;
    }

    area.innerHTML = renderAnswer(data);
  } catch (e) {
    area.innerHTML = `<div class="error-box">${esc(e.message)}</div>`;
  }
}

async function loadAnswer(queryId) {
  const detail = document.getElementById('answer-detail');
  detail.innerHTML = '<div class="loading"><span class="spinner"></span>Loading...</div>';
  try {
    const res = await fetch(`${API}/queries/${queryId}`);
    const data = await res.json();
    detail.innerHTML = `<h3 style="margin-bottom:16px">${esc(data.question)}</h3>` + renderAnswer(data);
  } catch (e) {
    detail.innerHTML = `<div class="error-box">${esc(e.message)}</div>`;
  }
}

function renderAnswer(data) {
  if (data.verification_status === 'fail' || data.error) {
    return `
      <div class="verification-banner fail">
        <span>✗ Verification Failed</span>
      </div>
      <div class="error-box">
        ${esc(data.error || 'The answer could not be verified against the source text.')}
        <br><br>
        <a href="${esc(data.debug_url)}" style="color:#991b1b">View debug info →</a>
      </div>
    `;
  }

  const statusClass = data.verification_status === 'pass' ? 'pass' : 'warn';
  const statusLabel = data.verification_status === 'pass' ? '✓ Verified' : '⚠ Verified with warnings';

  let warnings = '';
  if (data.verification_warnings && data.verification_warnings.length) {
    warnings = `<ul class="warning-list">${data.verification_warnings.filter(Boolean).map(w => `<li>${esc(w)}</li>`).join('')}</ul>`;
  }

  const citations = (data.citations || []).map((c, i) => `
    <div class="citation-item" onclick="toggleCitation(this)">
      <div class="citation-label">[${i+1}] ${c.section_title ? esc(c.section_title) : 'Citation'}</div>
      ${c.quote ? `<div class="citation-quote">"${esc(c.quote)}"</div>` : ''}
      <div class="citation-section">${esc(c.passage_id)}</div>
      <div class="citation-full-text">${esc(c.passage_text || '')}</div>
    </div>
  `).join('');

  const objections = (data.objections || []).map(o => `
    <div class="objection-item">${esc(o)}</div>
  `).join('');

  return `
    <div class="verification-banner ${statusClass}">
      <span>${statusLabel}</span>
      ${warnings}
    </div>
    <div class="answer-box">
      <div class="answer-text">${esc(data.final_answer)}</div>
      ${data.confidence_notes ? `<div style="font-size:0.85rem;color:#6b7280;font-style:italic">${esc(data.confidence_notes)}</div>` : ''}
    </div>
    ${citations ? `
      <div class="card citations-section">
        <h3>Citations</h3>
        ${citations}
      </div>
    ` : ''}
    ${objections ? `
      <div class="card objections-section">
        <h3>Objections Raised</h3>
        ${objections}
      </div>
    ` : ''}
    <div class="debug-link">
      <a href="${esc(data.debug_url)}" target="_blank">View retrieval debug →</a>
    </div>
  `;
}

function toggleCitation(el) {
  el.classList.toggle('expanded');
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function esc(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function fmtDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}
