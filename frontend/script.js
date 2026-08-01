/* ── ICON TEMPLATES & SVG ASSETS ── */
const ICONS = {
    sun: '<circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>',
    moon: '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>',
};
const DOWNLOAD_ICON = '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M7 10l5 5 5-5"/><path d="M12 15V3"/>';
const USER_ICON = '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>';
const BOT_ICON = '<rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><path d="M8 16h.01M16 16h.01"/>';
const BOOK_ICON = '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>';
const EDIT_ICON = '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.12 2.12 0 0 1 3 3L12 15l-4 1 1-4z"/>';
const CHAT_ICON = '<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>';
const SOURCE_LABELS = { arxiv: 'ArXiv', semantic_scholar: 'S2', openalex: 'OpenAlex', crossref: 'CrossRef', europepmc: 'EuropePMC' };

/* ── STATE MANAGEMENT ── */
const API = '';
let state = {
    sessionId: null, report: null, papers: [], validatedClaims: [],
    contradictions: [], gaps: [], confidenceScore: 0, confidenceBreakdown: {},
    proposal: null, roadmap: null, experiment: null, domain: 'General',
    critiqueVerdict: '', critiqueFeedback: '', revisionCount: 0,
    lastQuery: '', sortKey: null, sortAsc: true,
};
let selectedPapers = new Set();
let chatScopePaper = null;

/* ── THEME MANAGEMENT ── */
function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    document.getElementById('theme-icon').innerHTML = ICONS[theme === 'dark' ? 'sun' : 'moon'];
    localStorage.setItem('ra-theme', theme);
}
function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    applyTheme(current === 'dark' ? 'light' : 'dark');
}
applyTheme(localStorage.getItem('ra-theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'));

/* ── TOAST NOTIFICATIONS ── */
function toast(message) {
    const el = document.createElement('div');
    el.className = 'toast-item';
    el.textContent = message;
    document.getElementById('toast').appendChild(el);
    setTimeout(() => el.remove(), 6000);
}

/* ── API CALL HANDLER ── */
async function apiCall(path, body, timeoutMs = 240000) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const res = await fetch(API + path, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
            signal: controller.signal,
        });
        clearTimeout(timer);
        if (!res.ok) {
            let detail = `HTTP ${res.status}`;
            try { detail = (await res.json()).detail || detail; } catch (e) {}
            throw new Error(detail);
        }
        return await res.json();
    } catch (e) {
        clearTimeout(timer);
        if (e.name === 'AbortError') throw new Error('Request timed out — pipeline execution took too long. Try again shortly.');
        throw e;
    }
}

/* ── NAVIGATION HANDLER ── */
function switchTab(name) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === name));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.toggle('active', p.id === 'panel-' + name));
}
document.querySelectorAll('.tab-btn').forEach(b => b.addEventListener('click', () => switchTab(b.dataset.tab)));

/* ── MAIN PIPELINE RUNNER ── */
async function runResearch() {
    const query = document.getElementById('query').value.trim();
    if (!query) { toast('Enter a research question first.'); return; }

    const deepMode = document.getElementById('deep-mode').checked;
    document.getElementById('run-btn').disabled = true;
    document.getElementById('loading').style.display = 'flex';
    document.getElementById('loading-text').textContent =
        'Agents are planning, searching, and analyzing' + (deepMode ? ' (deep research active)...' : '...');

    clearChat();
    resetOnDemandPanel('proposal'); resetOnDemandPanel('roadmap'); resetOnDemandPanel('experiment');
    resetOnDemandPanel('review'); resetOnDemandPanel('repro');
    document.getElementById('kg-generate-row').style.display = 'block';
    document.getElementById('kg-regen-row').style.display = 'none';
    document.getElementById('new-papers-banner').innerHTML = '';

    switchTab('dashboard');

    try {
        const data = await apiCall('/research', { query, deep_mode: deepMode }, deepMode ? 400000 : 240000);
        state.sessionId = data.session_id;
        state.report = data.report;
        state.papers = data.papers;
        state.validatedClaims = data.validated_claims;
        state.contradictions = data.contradictions || [];
        state.gaps = data.gaps || [];
        state.confidenceScore = data.confidence_score || 0;
        state.confidenceBreakdown = data.confidence_breakdown || {};
        state.domain = data.domain || 'General';
        state.critiqueVerdict = data.critique_verdict || '';
        state.critiqueFeedback = data.critique_feedback || '';
        state.revisionCount = data.revision_count || 0;
        state.lastQuery = query;
        renderResults();
        saveToHistory();
    } catch (e) {
        toast('Something went wrong: ' + e.message);
    } finally {
        document.getElementById('run-btn').disabled = false;
        document.getElementById('loading').style.display = 'none';
    }
}

function resetOnDemandPanel(kind) {
    const contentEl = document.getElementById(kind + '-content');
    if (contentEl) contentEl.innerHTML = '';
    const genRow = document.getElementById(kind + '-generate-row');
    if (genRow) genRow.style.display = 'block';
    const regenRow = document.getElementById(kind + '-regen-row');
    if (regenRow) regenRow.style.display = 'none';
    const exportRow = document.getElementById(kind + '-export');
    if (exportRow) exportRow.style.display = 'none';
}

/* ── RENDER RESULTS VIEW ── */
function renderResults() {
    document.getElementById('kpis').style.display = 'grid';
    document.getElementById('tabs-nav').style.display = 'flex';
    document.getElementById('sidebar-empty').style.display = 'none';
    document.getElementById('results-area').style.display = 'block';
    document.getElementById('notes-card').style.display = 'block';
    document.getElementById('chat-bubble').classList.add('visible');
    document.getElementById('share-btn').style.display = 'flex';
    loadNotes();

    if (state.domain && state.domain !== 'General') {
        document.getElementById('domain-badge').style.display = 'inline-flex';
        document.getElementById('domain-text').textContent = state.domain + ' Expert Analysis';
    } else {
        document.getElementById('domain-badge').style.display = 'none';
    }

    document.getElementById('kpi-papers').textContent = state.papers.length;
    document.getElementById('kpi-claims').textContent = state.validatedClaims.length;
    document.getElementById('kpi-contra').textContent = state.contradictions.length;
    document.getElementById('kpi-conf').innerHTML = state.confidenceScore + '<span style="font-size:0.9rem;opacity:.6">/100</span>';
    const confCard = document.getElementById('kpi-conf-card');
    confCard.style.setProperty('--kpi-c', state.confidenceScore >= 70 ? 'var(--success)' : state.confidenceScore >= 40 ? 'var(--warning)' : 'var(--danger)');

    document.getElementById('conf-panel').style.display = 'block';
    const b = state.confidenceBreakdown;
    document.getElementById('conf-reason').textContent = b.reason || 'No breakdown available.';
    document.getElementById('conf-grounding-val').textContent = (b.avg_grounding ?? 0) + '%';
    document.getElementById('conf-grounding-bar').style.width = (b.avg_grounding ?? 0) + '%';
    document.getElementById('conf-coverage-val').textContent = (b.coverage ?? 0) + '%';
    document.getElementById('conf-coverage-bar').style.width = (b.coverage ?? 0) + '%';
    document.getElementById('conf-support-val').textContent = (b.paper_support ?? 0) + '%';
    document.getElementById('conf-support-bar').style.width = (b.paper_support ?? 0) + '%';

    document.getElementById('report-content').innerHTML = marked.parse(state.report || '');

    document.getElementById('claims-content').innerHTML = state.validatedClaims.length
        ? state.validatedClaims.map(c => `<div class="claim-item"><strong>${escapeHtml(c.text)}</strong><div class="claim-source"><svg class="icon icon-sm" viewBox="0 0 24 24">${DOWNLOAD_ICON}</svg><a href="${c.pdf_url || c.source_paper_url}" target="_blank">Open source</a> &middot; confidence: ${c.confidence.toFixed(2)}</div></div>`).join('')
        : '<div class="empty-state">No claims passed the grounding threshold for this query.</div>';

    document.getElementById('contra-content').innerHTML = state.contradictions.length
        ? state.contradictions.map(c => `<div class="contra-item"><strong>Conflict:</strong><br>"${escapeHtml(c.claim_a || '')}"<br>"${escapeHtml(c.claim_b || '')}"<br><span class="muted">Possible reason: ${escapeHtml(c.possible_reason || 'unclear')}</span></div>`).join('')
        : '<div class="empty-state">No disagreements were identified among the retrieved sources for this query.</div>';

    document.getElementById('gaps-content').innerHTML = state.gaps.length
        ? state.gaps.map(g => `<div class="gap-item"><svg class="icon" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg><span>${escapeHtml(g)}</span></div>`).join('')
        : '<div class="empty-state">No explicit research gaps were identified for this query.</div>';

    state.sortKey = null;
    renderPapersTable();
    renderEvalDashboard();
    renderCritiqueStatus();

    document.getElementById('kg-frame').style.display = 'none';
    document.getElementById('kg-empty').style.display = 'none';
}

/* ── PAPERS TABLE RENDER & SELECTION ── */
function sortPapers(key) {
    if (state.sortKey === key) { state.sortAsc = !state.sortAsc; } else { state.sortKey = key; state.sortAsc = false; }
    renderPapersTable();
}

function paperKey(title) {
    return 'ra-annot-' + btoa(unescape(encodeURIComponent(title))).slice(0, 40);
}

function renderPapersTable() {
    const el = document.getElementById('papers-content');
    if (!state.papers.length) { el.innerHTML = '<div class="empty-state">No papers retrieved yet.</div>'; return; }

    let papers = [...state.papers];
    if (state.sortKey) {
        papers.sort((a, b) => {
            let av = a[state.sortKey] ?? 0, bv = b[state.sortKey] ?? 0;
            return state.sortAsc ? (av > bv ? 1 : -1) : (av < bv ? 1 : -1);
        });
    }

    const rows = papers.map((p, i) => {
        const authors = p.authors.slice(0, 3).join(', ') + (p.authors.length > 3 ? ' et al.' : '');
        const abstractText = (p.abstract || 'No abstract available.').slice(0, 500) + ((p.abstract || '').length > 500 ? '...' : '');
        const pdfLink = p.pdf_url || p.url;
        const hasPdf = p.has_pdf === true;
        const savedNote = localStorage.getItem(paperKey(p.title)) || '';
        const checked = selectedPapers.has(p.title) ? 'checked' : '';
        return `
        <tr class="paper-row">
            <td onclick="event.stopPropagation()"><input type="checkbox" class="paper-checkbox" ${checked} onchange="toggleSelection('${escapeJs(p.title)}', this.checked)"></td>
            <td onclick="toggleAbstract(${i})">${escapeHtml(p.title)}</td>
            <td onclick="toggleAbstract(${i})">${escapeHtml(authors)}</td>
            <td onclick="toggleAbstract(${i})">${p.year || '-'}</td>
            <td onclick="toggleAbstract(${i})"><span class="source-badge ${p.source}">${SOURCE_LABELS[p.source] || p.source}</span></td>
            <td onclick="toggleAbstract(${i})" title="Total citations according to source database.">${p.citation_count ?? '-'}</td>
            <td>
                <div class="row-actions">
                    <a class="row-action" href="${pdfLink}" target="_blank"><svg class="icon icon-sm" viewBox="0 0 24 24">${DOWNLOAD_ICON}</svg>${hasPdf ? 'Open PDF' : 'Source'}</a>
                    ${hasPdf ? `<button class="row-action" onclick="readPdf('${escapeJs(p.title)}', '${escapeJs(pdfLink)}')"><svg class="icon icon-sm" viewBox="0 0 24 24">${BOOK_ICON}</svg>Read</button>` : ''}
                    <button class="row-action" onclick="chatAboutPaper('${escapeJs(p.title)}')"><svg class="icon icon-sm" viewBox="0 0 24 24">${CHAT_ICON}</svg>Chat</button>
                </div>
                ${!hasPdf ? '<div class="muted" style="font-size:0.72rem; margin-top:0.3rem;">No open-access PDF found.</div>' : ''}
            </td>
        </tr>
        <tr class="paper-abstract-row" id="abs-row-${i}"><td colspan="7">
            <div class="paper-abstract-text">${escapeHtml(abstractText)}</div>
            <div class="annotation-box">
                <div class="muted" style="margin-bottom:0.4rem; display:flex; align-items:center; gap:0.35rem;"><svg class="icon icon-sm" viewBox="0 0 24 24">${EDIT_ICON}</svg>Your notes on this paper</div>
                <textarea placeholder="Annotate this paper..." onclick="event.stopPropagation()" oninput="saveAnnotation('${escapeJs(p.title)}', this.value)">${escapeHtml(savedNote)}</textarea>
            </div>
        </td></tr>`;
    }).join('');

    const arrow = (key) => state.sortKey === key ? (state.sortAsc ? ' \u25B2' : ' \u25BC') : '';
    el.innerHTML = `<table class="papers-table"><thead><tr>
        <th></th>
        <th>Title</th><th>Authors</th>
        <th onclick="sortPapers('year')">Year${arrow('year')}</th>
        <th>Source</th>
        <th onclick="sortPapers('citation_count')">Citations${arrow('citation_count')}</th>
        <th>Actions</th>
    </tr></thead><tbody>${rows}</tbody></table><p class="muted" style="margin-top:0.8rem;">Select papers to compare. Click rows to view abstracts & annotations.</p>`;
}

function toggleSelection(title, checked) {
    if (checked) selectedPapers.add(title); else selectedPapers.delete(title);
    document.getElementById('compare-bar').style.display = selectedPapers.size >= 1 ? 'flex' : 'none';
    document.getElementById('compare-count').textContent = selectedPapers.size;
}
function clearSelection() {
    selectedPapers.clear();
    document.getElementById('compare-bar').style.display = 'none';
    document.getElementById('comparison-result').innerHTML = '';
    renderPapersTable();
}
async function comparePapers() {
    if (selectedPapers.size < 2) { toast('Select at least 2 papers to compare.'); return; }
    const btn = document.getElementById('compare-btn');
    btn.disabled = true; btn.textContent = 'Comparing...';
    try {
        const data = await apiCall('/compare-papers', { session_id: state.sessionId, paper_titles: [...selectedPapers] }, 90000);
        document.getElementById('comparison-result').innerHTML = `<div class="comparison-box">${marked.parse(data.comparison)}</div>`;
    } catch (e) {
        toast('Comparison failed: ' + e.message);
    } finally {
        btn.disabled = false; btn.innerHTML = `Compare selected (<span id="compare-count">${selectedPapers.size}</span>)`;
    }
}

function toggleAbstract(i) {
    const row = document.getElementById('abs-row-' + i);
    const wasOpen = row.classList.contains('open');
    document.querySelectorAll('.paper-abstract-row.open').forEach(r => r.classList.remove('open'));
    if (!wasOpen) row.classList.add('open');
}

function saveAnnotation(title, value) {
    localStorage.setItem(paperKey(title), value);
}

/* ── PDF READER MODAL ── */
function readPdf(title, url) {
    document.getElementById('pdf-modal-title').textContent = title;
    const frame = document.getElementById('pdf-modal-frame');
    frame.src = url;
    document.getElementById('pdf-modal').classList.add('open');
}
function closePdfModal() {
    document.getElementById('pdf-modal').classList.remove('open');
    document.getElementById('pdf-modal-frame').src = '';
}

/* ── GRAPH & ON-DEMAND GENERATIVE TOOLS ── */
async function buildGraph() {
    const btn = document.getElementById('kg-btn');
    const wasRegen = document.getElementById('kg-regen-row').style.display !== 'none';
    if (!wasRegen) { btn.disabled = true; btn.textContent = 'Building...'; }
    try {
        const data = await apiCall('/knowledge-graph', { query: state.lastQuery, session_id: state.sessionId }, 60000);
        if (data.papers_found === 0) {
            document.getElementById('kg-empty').style.display = 'block';
            document.getElementById('kg-frame').style.display = 'none';
        } else {
            const frame = document.getElementById('kg-frame');
            frame.src = '/download?path=' + encodeURIComponent(data.graph_path);
            frame.style.display = 'block';
            document.getElementById('kg-empty').style.display = 'none';
            document.getElementById('kg-generate-row').style.display = 'none';
            document.getElementById('kg-regen-row').style.display = 'block';
        }
    } catch (e) {
        toast('Something went wrong: ' + e.message);
    } finally {
        btn.disabled = false; btn.textContent = 'Build knowledge graph';
    }
}

async function generateProposal() {
    const btn = document.getElementById('proposal-btn');
    btn.disabled = true; btn.textContent = 'Drafting...';
    try {
        const data = await apiCall('/research-proposal', { session_id: state.sessionId }, 120000);
        state.proposal = data.proposal;
        document.getElementById('proposal-content').innerHTML = marked.parse(state.proposal);
        document.getElementById('proposal-export').style.display = 'block';
        document.getElementById('proposal-generate-row').style.display = 'none';
    } catch (e) {
        toast('Something went wrong: ' + e.message);
    } finally {
        btn.disabled = false; btn.textContent = 'Generate research proposal';
    }
}

async function generateRoadmap() {
    const btn = document.getElementById('roadmap-btn');
    const wasRegen = document.getElementById('roadmap-regen-row').style.display !== 'none';
    if (!wasRegen) { btn.disabled = true; btn.textContent = 'Building roadmap...'; }
    try {
        const data = await apiCall('/research-roadmap', { session_id: state.sessionId }, 120000);
        state.roadmap = data.roadmap;
        document.getElementById('roadmap-content').innerHTML = marked.parse(state.roadmap);
        document.getElementById('roadmap-generate-row').style.display = 'none';
        document.getElementById('roadmap-regen-row').style.display = 'block';
    } catch (e) {
        toast('Something went wrong: ' + e.message);
    } finally {
        btn.disabled = false; btn.textContent = 'Generate roadmap';
    }
}

async function generateExperiment() {
    const btn = document.getElementById('experiment-btn');
    const wasRegen = document.getElementById('experiment-regen-row').style.display !== 'none';
    if (!wasRegen) { btn.disabled = true; btn.textContent = 'Designing...'; }
    try {
        const data = await apiCall('/experiment-design', { session_id: state.sessionId }, 120000);
        state.experiment = data.experiment_design;
        document.getElementById('experiment-content').innerHTML = marked.parse(state.experiment);
        document.getElementById('experiment-generate-row').style.display = 'none';
        document.getElementById('experiment-regen-row').style.display = 'block';
    } catch (e) {
        toast('Something went wrong: ' + e.message);
    } finally {
        btn.disabled = false; btn.textContent = 'Design experiment';
    }
}

async function generatePeerReview() {
    const btn = document.getElementById('review-btn');
    const wasRegen = document.getElementById('review-regen-row').style.display !== 'none';
    if (!wasRegen) { btn.disabled = true; btn.textContent = 'Reviewing...'; }
    try {
        const data = await apiCall('/peer-review', { session_id: state.sessionId }, 120000);
        document.getElementById('review-content').innerHTML = marked.parse(data.review);
        document.getElementById('review-generate-row').style.display = 'none';
        document.getElementById('review-regen-row').style.display = 'block';
    } catch (e) {
        toast('Something went wrong: ' + e.message);
    } finally {
        btn.disabled = false; btn.textContent = 'Run peer review';
    }
}

async function generateReproducibility() {
    const btn = document.getElementById('repro-btn');
    const wasRegen = document.getElementById('repro-regen-row').style.display !== 'none';
    if (!wasRegen) { btn.disabled = true; btn.textContent = 'Checking...'; }
    try {
        const data = await apiCall('/reproducibility-check', { session_id: state.sessionId }, 120000);
        document.getElementById('repro-content').innerHTML = marked.parse(data.reproducibility_check);
        document.getElementById('repro-generate-row').style.display = 'none';
        document.getElementById('repro-regen-row').style.display = 'block';
    } catch (e) {
        toast('Something went wrong: ' + e.message);
    } finally {
        btn.disabled = false; btn.textContent = 'Check reproducibility';
    }
}

async function checkNewPapers() {
    const btn = document.getElementById('new-papers-btn');
    btn.disabled = true; btn.textContent = 'Checking...';
    try {
        const data = await apiCall('/check-new-papers', { session_id: state.sessionId }, 90000);
        const banner = document.getElementById('new-papers-banner');
        if (data.new_count > 0) {
            state.papers = state.papers.concat(data.new_papers);
            banner.innerHTML = `<div class="new-papers-banner">Found ${data.new_count} new paper(s) — added to the table below.</div>`;
            renderPapersTable();
            renderEvalDashboard();
        } else {
            banner.innerHTML = `<div class="new-papers-banner">No new papers found since your last check.</div>`;
        }
    } catch (e) {
        toast('Something went wrong: ' + e.message);
    } finally {
        btn.disabled = false; btn.textContent = 'Check for new papers';
    }
}

/* ── DASHBOARD SECONDARY STATS + SOURCE BREAKDOWN ──
   Papers/Claims/Disagreements/Confidence already live in the KPI cards
   at the top of the Dashboard — this only covers what ISN'T shown there. */
function renderEvalDashboard() {
    const avgCitations = state.papers.length
        ? Math.round(state.papers.reduce((s, p) => s + (p.citation_count || 0), 0) / state.papers.length)
        : 0;

    document.getElementById('eval-stats').innerHTML = `
        <div class="eval-stat"><div class="eval-stat-label">Avg. Citations / Paper</div><div class="eval-stat-value">${avgCitations}</div></div>
        <div class="eval-stat"><div class="eval-stat-label">Research Gaps Found</div><div class="eval-stat-value">${state.gaps.length}</div></div>
    `;

    const sourceCounts = {};
    state.papers.forEach(p => { sourceCounts[p.source] = (sourceCounts[p.source] || 0) + 1; });
    const sourceColors = { arxiv: 'var(--primary)', semantic_scholar: 'var(--success)', openalex: 'var(--warning)', crossref: 'var(--danger)', europepmc: 'var(--success)' };
    const maxCount = Math.max(1, ...Object.values(sourceCounts));

    document.getElementById('eval-sources').innerHTML = Object.entries(sourceCounts).map(([src, count]) => `
        <div class="eval-source-row">
            <span style="width:90px;">${SOURCE_LABELS[src] || src}</span>
            <div class="eval-source-bar-track"><div class="eval-source-bar-fill" style="width:${(count / maxCount) * 100}%; background:${sourceColors[src] || 'var(--primary)'}"></div></div>
            <span style="width:24px; text-align:right;">${count}</span>
        </div>
    `).join('') || '<div class="empty-state">No papers available.</div>';
}

/* ── SELF-CRITIQUE (REFLECTION LOOP) STATUS ──
   Shows what the critique agent decided about the finished report,
   compared against the ORIGINAL question — and whether it triggered a
   revision. Makes the autonomous Plan→Write→Critique→Revise loop
   visible instead of purely internal. */
function renderCritiqueStatus() {
    const el = document.getElementById('critique-status');
    const verdict = state.critiqueVerdict;
    const revisions = state.revisionCount || 0;

    if (!verdict) {
        el.textContent = 'No critique data for this run.';
        return;
    }

    if (verdict === 'pass' && revisions === 0) {
        el.textContent = 'The report passed self-critique on the first draft — it directly answered the original question with adequate grounding.';
    } else if (revisions > 0) {
        el.textContent = `The report was revised ${revisions} time(s) after self-critique found the writing didn't fully address the original question. Feedback used: "${state.critiqueFeedback || 'n/a'}"`;
    } else if (verdict === 'research_gap') {
        el.textContent = `Self-critique found the underlying evidence too thin to fully answer the question (retry budget reached). Feedback: "${state.critiqueFeedback || 'n/a'}"`;
    } else {
        el.textContent = 'The report passed self-critique.';
    }
}

/* ── DOCUMENT EXPORTER ── */
async function exportDoc(kind, fmt) {
    const text = kind === 'report' ? state.report : state.proposal;
    const queryLabel = kind === 'report' ? state.lastQuery : (state.lastQuery + ' - Research Proposal');
    try {
        const expData = await apiCall('/export', { report: text, query: queryLabel, format: fmt }, 60000);
        const url = '/download?path=' + encodeURIComponent(expData.path);
        const a = document.createElement('a');
        a.href = url; a.download = expData.path.split('/').pop();
        document.body.appendChild(a); a.click(); a.remove();
    } catch (e) {
        toast(fmt.toUpperCase() + ' export failed: ' + e.message);
    }
}

/* ── CHAT BOT HANDLER ── */
function toggleChatWidget() {
    document.getElementById('chat-widget').classList.toggle('open');
}
function clearChat() {
    chatScopePaper = null;
    renderChatScopeChip();
    document.getElementById('chat-box').innerHTML = '<div class="chat-empty-hint">Run a research query, then ask follow-up questions grounded in the papers found.</div>';
}
function chatAboutPaper(title) {
    chatScopePaper = title;
    renderChatScopeChip();
    document.getElementById('chat-widget').classList.add('open');
    document.getElementById('chat-input').focus();
    toast('Chat scoped to paper: ' + (title.length > 40 ? title.slice(0, 40) + '...' : title));
}
function clearChatScope() {
    chatScopePaper = null;
    renderChatScopeChip();
}
function renderChatScopeChip() {
    const existing = document.getElementById('chat-scope-chip');
    if (existing) existing.remove();
    if (chatScopePaper) {
        const chip = document.createElement('div');
        chip.id = 'chat-scope-chip';
        chip.style.cssText = 'display:inline-flex; align-items:center; gap:0.5rem; background:var(--primary-soft); color:var(--primary-ink); border-radius:999px; padding:0.4rem 0.8rem; font-size:0.78rem; font-weight:600; margin:0 1rem 0.8rem;';
        chip.innerHTML = `Chatting about: ${escapeHtml(chatScopePaper.length > 35 ? chatScopePaper.slice(0, 35) + '...' : chatScopePaper)} <button style="background:none; border:none; color:inherit; cursor:pointer; font-weight:700;" onclick="clearChatScope()">&times;</button>`;
        document.getElementById('chat-box').before(chip);
    }
}
async function sendChat() {
    if (!state.sessionId) { toast('Run a research query first.'); return; }
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message) return;
    input.value = '';

    const emptyHint = document.querySelector('.chat-empty-hint');
    if (emptyHint) emptyHint.remove();

    appendChatMsg('user', escapeHtml(message));
    const thinkingRow = appendTyping();
    try {
        const body = { session_id: state.sessionId, message };
        if (chatScopePaper) body.paper_title = chatScopePaper;
        const data = await apiCall('/chat', body, 60000);
        replaceTypingWithAnswer(thinkingRow, data.answer);
    } catch (e) {
        replaceTypingWithAnswer(thinkingRow, 'Something went wrong: ' + e.message);
    }
}

function appendChatMsg(role, htmlContent) {
    const box = document.getElementById('chat-box');
    const row = document.createElement('div');
    row.className = 'msg-row ' + role;
    row.innerHTML = `
        <div class="avatar ${role}"><svg class="icon icon-sm" viewBox="0 0 24 24">${role === 'user' ? USER_ICON : BOT_ICON}</svg></div>
        <div class="msg ${role}">${htmlContent}</div>`;
    box.appendChild(row);
    box.scrollTop = box.scrollHeight;
    return row;
}
function appendTyping() {
    return appendChatMsg('assistant', '<div style="display:inline-flex; gap:3px; align-items:center;"><span>.</span><span>.</span><span>.</span></div>');
}
function replaceTypingWithAnswer(row, answerText) {
    const msgEl = row.querySelector('.msg');
    msgEl.innerHTML = marked.parse(answerText || '');
    document.getElementById('chat-box').scrollTop = document.getElementById('chat-box').scrollHeight;
}

/* ── WORKSPACE NOTES LOCAL STORAGE ── */
function notesKey() {
    return 'ra-notes-' + btoa(unescape(encodeURIComponent(state.lastQuery))).slice(0, 40);
}
function saveNotes() {
    localStorage.setItem(notesKey(), document.getElementById('notes-area').value);
    document.getElementById('notes-status').textContent = 'Saved locally · ' + new Date().toLocaleTimeString();
}
function loadNotes() {
    const saved = localStorage.getItem(notesKey());
    document.getElementById('notes-area').value = saved || '';
    document.getElementById('notes-status').textContent = saved ? 'Loaded from last session for this query' : 'Not saved yet';
}

/* ── HISTORY DRAWER HANDLERS ── */
function toggleHistory() {
    document.getElementById('history-panel').classList.toggle('open');
    renderHistoryList();
}
function saveToHistory() {
    const history = JSON.parse(localStorage.getItem('ra-history') || '[]');
    history.unshift({
        query: state.lastQuery,
        timestamp: Date.now(),
        confidence: state.confidenceScore,
        papersFound: state.papers.length,
        snapshot: { ...state },
    });
    localStorage.setItem('ra-history', JSON.stringify(history.slice(0, 20)));
}
function renderHistoryList() {
    const history = JSON.parse(localStorage.getItem('ra-history') || '[]');
    const el = document.getElementById('history-list');
    if (!history.length) { el.innerHTML = '<div class="empty-state">No past queries yet.</div>'; return; }
    el.innerHTML = history.map((h, i) => `
        <div class="history-item" onclick="restoreHistory(${i})">
            <div class="history-item-query">${escapeHtml(h.query)}</div>
            <div class="history-item-meta">${new Date(h.timestamp).toLocaleString()} &middot; ${h.papersFound} papers &middot; confidence ${h.confidence}/100</div>
        </div>
    `).join('');
}
function restoreHistory(i) {
    const history = JSON.parse(localStorage.getItem('ra-history') || '[]');
    const entry = history[i];
    if (!entry) return;
    state = { ...entry.snapshot };
    document.getElementById('query').value = state.lastQuery;
    renderResults();
    switchTab('dashboard');
    toggleHistory();
    toast('Restored session from history.');
}

/* ── UTILITY FUNCTIONS ── */
function escapeHtml(str) {
    const d = document.createElement('div'); d.textContent = str; return d.innerHTML;
}
function escapeJs(str) {
    return String(str).replace(/\\/g, '\\\\').replace(/'/g, "\\'");
}

/* ── SHARE WITH A TEAMMATE ── */
function shareSession() {
    if (!state.sessionId) { toast('Run a research query first.'); return; }
    const url = `${window.location.origin}${window.location.pathname}?share=${state.sessionId}`;
    navigator.clipboard.writeText(url).then(() => {
        toast('Share link copied to clipboard.');
    }).catch(() => {
        toast('Link: ' + url);
    });
}

async function loadSharedSessionIfPresent() {
    const params = new URLSearchParams(window.location.search);
    const sharedId = params.get('share');
    if (!sharedId) return;

    try {
        const res = await fetch('/session/' + sharedId);
        if (!res.ok) {
            const body = await res.json().catch(() => ({}));
            throw new Error(body.detail || `HTTP ${res.status}`);
        }
        const data = await res.json();

        state.sessionId = data.session_id;
        state.report = data.report;
        state.papers = data.papers;
        state.validatedClaims = data.validated_claims;
        state.contradictions = data.contradictions || [];
        state.gaps = data.gaps || [];
        state.confidenceScore = data.confidence_score || 0;
        state.confidenceBreakdown = data.confidence_breakdown || {};
        state.domain = data.domain || 'General';
        state.critiqueVerdict = data.critique_verdict || '';
        state.critiqueFeedback = data.critique_feedback || '';
        state.revisionCount = data.revision_count || 0;
        state.lastQuery = data.query;
        document.getElementById('query').value = data.query;
        renderResults();
        toast('Loaded shared research session.');
    } catch (e) {
        toast('Could not load shared session: ' + e.message);
    }
}

loadSharedSessionIfPresent();
