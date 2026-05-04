/**
 * CodePulse — Main Application Logic v3.0 (Obsidian Nexus)
 * Handles navigation, file upload, analysis execution, and state management.
 */

const API_URL = '/api/analyze';

// ── State ──────────────────────────────────────────────────────────────────
let currentReport = null;
let currentView = 'auth';
let currentMode = 'code';
let activeProjectPort = null;
let currentFiles = [];
let currentProfile = 'fast';
let currentSession = null;

// ── DOM References ─────────────────────────────────────────────────────────
const statusDot       = document.getElementById('status-dot');
const statusText      = document.getElementById('status-text');
const placeholderEl   = document.getElementById('placeholder-state');
const loadingEl       = document.getElementById('loading-state');
const loadingStage    = document.getElementById('loading-stage');
const reportContent   = document.getElementById('report-content');
const resultsNav      = document.getElementById('results-nav');
const backHomeBtn     = document.getElementById('back-home-btn');
const profileMenu     = document.getElementById('profile-menu');
const profileMenuBtn  = document.getElementById('profile-menu-btn');
const profileDropdown = document.getElementById('profile-dropdown');
const startupSplash   = document.getElementById('startup-splash');
const startupSplashStartedAt = performance.now();

const VIEWS = {
    auth:        document.getElementById('view-auth'),
    selection:   document.getElementById('view-selection'),
    execution:   document.getElementById('view-execution'),
    performance: document.getElementById('view-performance'),
    testing:     document.getElementById('view-testing'),
};

// ── Toasts ─────────────────────────────────────────────────────────────────
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    const iconMap = { error: 'error', success: 'check_circle', info: 'info' };
    const colorMap = { error: 'var(--error)', success: 'var(--success)', info: 'var(--accent)' };
    toast.innerHTML = `
        <span class="material-symbols-outlined" style="font-size:18px; color:${colorMap[type]}; font-variation-settings:'FILL' 1;">${iconMap[type]}</span>
        <span>${message}</span>
    `;
    container.appendChild(toast);
    setTimeout(() => {
        toast.classList.add('toast-exit');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ── Init ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
    console.log('CodePulse initializing...');
    
    try {
        // Start loading Monaco in background to avoid blocking the UI
        initMonacoEditor().catch(err => console.error('Monaco init error:', err));

        // Selection Flow
        const selCode = document.getElementById('select-code');
        if (selCode) {
            selCode.addEventListener('click', () => {
                switchMode('code');
                switchView('execution');
            });
        }

        const selProj = document.getElementById('select-project');
        if (selProj) {
            selProj.addEventListener('click', () => {
                switchMode('project');
                switchView('execution');
            });
        }

        // Hover effect for selection cards — show button
        document.querySelectorAll('.selection-card').forEach(card => {
            const btn = card.querySelector('.btn-primary');
            if (btn) {
                card.addEventListener('mouseenter', () => btn.style.opacity = '1');
                card.addEventListener('mouseleave', () => btn.style.opacity = '0');
            }
        });

        // Analyze Buttons
        document.getElementById('code-analyze-btn')?.addEventListener('click', runAnalysis);
        document.getElementById('project-analyze-btn')?.addEventListener('click', runAnalysis);

        // Tab Switching
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => switchView(btn.dataset.view));
        });

        // Logo / Back to Home
        document.getElementById('logo-home')?.addEventListener('click', goHome);
        if (backHomeBtn) backHomeBtn.addEventListener('click', goHome);

        // Mode Toggle Buttons
        document.querySelectorAll('#mode-toggle .mode-btn').forEach(btn => {
            btn.addEventListener('click', () => switchMode(btn.dataset.mode));
        });

        // Upload Reset
        document.getElementById('upload-reset-btn')?.addEventListener('click', resetUpload);
        document.getElementById('analysis-profile-select')?.addEventListener('change', (event) => {
            currentProfile = event.target.value || 'fast';
        });

        document.getElementById('language-select')?.addEventListener('change', (event) => {
            setEditorLanguage(event.target.value || 'python');
            setTimeout(() => layoutEditor(), 0);
        });

        // Upload Logic
        initUploadLogic();
        
        // Auth Logic
        initAuthLogic();
        initProfileMenu();

        // Initial State - Check Session
        const isLoggedIn = await checkSession();
        if (isLoggedIn) {
            restoreSessionState();
        } else {
            switchView('auth');
        }
    } catch (err) {
        console.error('CodePulse initialization failed:', err);
        // Fallback to auth if everything fails
        switchView('auth');
    } finally {
        hideStartupSplash();
    }
});

function hideStartupSplash() {
    if (!startupSplash) return;
    const minimumDisplayMs = 4300;
    const elapsed = performance.now() - startupSplashStartedAt;
    const delay = Math.max(0, minimumDisplayMs - elapsed);

    setTimeout(() => {
        startupSplash.classList.add('splash-exit');
        setTimeout(() => startupSplash.remove(), 900);
    }, delay);
}

// ── Auth ───────────────────────────────────────────────────────────────────
async function checkSession() {
    const token = localStorage.getItem('codepulse_auth_token');
    if (!token) return false;

    try {
        const response = await fetch('/api/auth/verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token })
        });
        const data = await response.json();
        if (data.valid) {
            currentSession = { username: data.username, token };
            document.getElementById('status-text').textContent = `Logged in as ${data.username}`;
            updateProfileMenu(data.username);
            return true;
        }
    } catch (err) {
        console.error("Session verification failed", err);
    }
    
    localStorage.removeItem('codepulse_auth_token');
    return false;
}

function initAuthLogic() {
    const form = document.getElementById('auth-form');
    const tabs = document.querySelectorAll('.auth-tab');
    let isLogin = true;

    if(!form) return;

    tabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            tabs.forEach(t => t.classList.remove('active'));
            e.target.classList.add('active');
            isLogin = e.target.dataset.mode === 'login';
            document.getElementById('auth-submit-btn').innerHTML = isLogin ? 'Sign In <div class="btn-shimmer"></div>' : 'Register <div class="btn-shimmer"></div>';
            document.getElementById('auth-error').textContent = '';
        });
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('auth-username').value;
        const password = document.getElementById('auth-password').value;
        const errorEl = document.getElementById('auth-error');
        const submitBtn = document.getElementById('auth-submit-btn');

        errorEl.textContent = '';
        submitBtn.disabled = true;

        const endpoint = isLogin ? '/api/auth/login' : '/api/auth/register';

        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Authentication failed');
            }

            localStorage.setItem('codepulse_auth_token', data.token);
            currentSession = { username: data.username, token: data.token };
            
            document.getElementById('status-text').textContent = `Logged in as ${data.username}`;
            updateProfileMenu(data.username);
            
            showToast(data.message, 'success');
            switchView('selection');
            
        } catch (err) {
            errorEl.textContent = err.message;
        } finally {
            submitBtn.disabled = false;
        }
    });

    document.getElementById('logout-btn')?.addEventListener('click', () => {
        localStorage.removeItem('codepulse_auth_token');
        sessionStorage.removeItem('codepulse_app_state');
        currentSession = null;
        document.getElementById('status-text').textContent = 'Ready';
        updateProfileMenu('');
        
        // Clear forms
        document.getElementById('auth-username').value = '';
        document.getElementById('auth-password').value = '';
        
        switchView('auth');
        closeProfileMenu();
        showToast('Logged out successfully', 'info');
    });
}

function initProfileMenu() {
    if (!profileMenu || !profileMenuBtn) return;

    profileMenuBtn.addEventListener('click', (event) => {
        event.stopPropagation();
        const isOpen = profileMenu.classList.toggle('open');
        profileMenuBtn.setAttribute('aria-expanded', String(isOpen));
    });

    profileDropdown?.addEventListener('click', (event) => {
        if (event.target.closest('.profile-menu-action')) closeProfileMenu();
    });

    document.addEventListener('click', (event) => {
        if (!profileMenu.contains(event.target)) closeProfileMenu();
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') closeProfileMenu();
    });
}

function closeProfileMenu() {
    if (!profileMenu || !profileMenuBtn) return;
    profileMenu.classList.remove('open');
    profileMenuBtn.setAttribute('aria-expanded', 'false');
}

function updateProfileMenu(username) {
    const safeName = username || 'Signed in';
    const initial = (safeName.trim()[0] || 'U').toUpperCase();
    const nameEl = document.getElementById('profile-menu-name');
    const emailEl = document.getElementById('profile-menu-email');
    const avatarEl = document.getElementById('profile-avatar-initial');
    const avatarLargeEl = document.getElementById('profile-avatar-large');

    if (nameEl) nameEl.textContent = safeName;
    if (emailEl) emailEl.textContent = username ? 'CodePulse workspace' : 'Not signed in';
    if (avatarEl) avatarEl.textContent = initial;
    if (avatarLargeEl) avatarLargeEl.textContent = initial;
}

// ── Navigation ─────────────────────────────────────────────────────────────
function switchView(viewId) {
    console.log(`Switching to view: ${viewId}`);
    const targetView = VIEWS[viewId];
    if (!targetView) {
        console.error(`View ${viewId} not found in VIEWS map.`);
        return;
    }
    
    currentView = viewId;

    // Reset scroll
    window.scrollTo({ top: 0, behavior: 'smooth' });

    // Update tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.view === viewId);
    });

    // Update viewports
    Object.keys(VIEWS).forEach(key => {
        const el = VIEWS[key];
        if (!el) return;
        
        if (key === viewId) {
            el.style.display = (key === 'selection' || key === 'auth') ? 'flex' : 'block';
            el.style.opacity = '1';
            el.style.visibility = 'visible';
        } else {
            el.style.display = 'none';
        }
    });

    // Show/hide header elements
    const isSelection = viewId === 'selection';
    const isAuth = viewId === 'auth';
    
    if (resultsNav) resultsNav.style.display = (!isSelection && !isAuth && currentReport) ? 'flex' : 'none';
    if (backHomeBtn) backHomeBtn.style.display = (!isAuth && currentSession) ? 'flex' : 'none';
    
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) logoutBtn.style.display = (!isAuth && currentSession) ? 'flex' : 'none';
    if (profileMenu) profileMenu.style.display = (!isAuth && currentSession) ? 'block' : 'none';
    if (isAuth) closeProfileMenu();

    // If returning to execution view and we have a report, ensure it's shown instead of loader
    if (viewId === 'execution' && currentReport) {
        placeholderEl.style.display = 'none';
        loadingEl.style.display = 'none';
        reportContent.style.display = 'block';
        setTimeout(() => layoutEditor(), 0);
    } else if (viewId === 'execution') {
        setTimeout(() => layoutEditor(), 0);
    }
}

function goHome() {
    switchView('selection');
    resultsNav.style.display = 'none';
}

function switchMode(mode) {
    currentMode = mode;

    const editorContainer = document.getElementById('editor-container');
    const uploadContainer = document.getElementById('upload-container');

    // Update toggle buttons
    document.querySelectorAll('#mode-toggle .mode-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === mode);
    });

    if (mode === 'code') {
        editorContainer.style.display = 'flex';
        uploadContainer.style.display = 'none';
        setTimeout(() => layoutEditor(), 0);
    } else {
        editorContainer.style.display = 'none';
        uploadContainer.style.display = 'flex';
        // If we have files already (from upload or session), ensure tree is shown
        if (currentFiles && currentFiles.length > 0) {
            renderFileTree(currentFiles);
        }
    }
}

// ── Upload Logic ────────────────────────────────────────────────────────────
function initUploadLogic() {
    const dropzone = document.getElementById('upload-dropzone');
    const fileInput = document.getElementById('project-file-input');
    if (!dropzone || !fileInput) return;

    // Click to open file picker
    dropzone.addEventListener('click', (e) => {
        // Don't trigger if already uploaded
        if (activeProjectPort) return;
        fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) uploadProject(e.target.files[0]);
    });

    // Drag & Drop
    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('drag-over');
    });
    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('drag-over');
    });
    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('drag-over');
        const file = e.dataTransfer.files[0];
        if (file && file.name.endsWith('.zip')) {
            uploadProject(file);
        } else {
            showToast('Please upload a .zip file', 'error');
        }
    });
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

async function uploadProject(file) {
    const dropzone = document.getElementById('upload-dropzone');
    const uploadIcon = document.getElementById('upload-icon-glyph');
    const uploadText = document.getElementById('upload-text');
    const uploadFileInfo = document.getElementById('upload-file-info');
    const projectInfoCard = document.getElementById('project-info-card');
    const resetBtn = document.getElementById('upload-reset-btn');

    // Show uploading state
    uploadIcon.textContent = 'hourglass_top';
    uploadIcon.style.color = 'var(--accent)';
    uploadText.innerHTML = `
        <p style="color:var(--accent); font-weight:600; font-size:0.9rem;">Uploading...</p>
        <p style="color:var(--text-muted); font-size:0.75rem; margin-top:0.25rem;">${file.name} (${formatFileSize(file.size)})</p>
        <div class="upload-progress-container">
            <div id="upload-progress-bar" class="upload-progress-bar"></div>
        </div>
        <div id="upload-progress-text" class="upload-progress-text">0%</div>
    `;

    const progressBar = document.getElementById('upload-progress-bar');
    const progressText = document.getElementById('upload-progress-text');

    setStatus('Uploading...', 'var(--warning)');

    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        const formData = new FormData();
        formData.append('file', file);

        // 5 minute timeout for large projects
        xhr.timeout = 5 * 60 * 1000;

        let processingInterval = null;

        xhr.upload.onprogress = (event) => {
            if (event.lengthComputable) {
                const percent = Math.round((event.loaded / event.total) * 100);
                if (progressBar) progressBar.style.width = percent + '%';
                if (progressText) progressText.textContent = percent + '%';
                if (percent === 100) {
                    setStatus('Processing...', 'var(--warning)');
                    if (progressText) progressText.textContent = 'Processing archive...';
                    if (progressBar) {
                        progressBar.style.transition = 'none';
                        progressBar.style.background = 'linear-gradient(90deg, #6366f1, #a855f7, #6366f1)';
                        progressBar.style.backgroundSize = '200% 100%';
                        progressBar.style.animation = 'progressPulse 1.5s ease-in-out infinite';
                    }
                    const phases = ['Extracting files...', 'Installing dependencies...', 'Starting server...', 'Running health checks...'];
                    let phaseIdx = 0;
                    processingInterval = setInterval(() => {
                        phaseIdx = (phaseIdx + 1) % phases.length;
                        if (progressText) progressText.textContent = phases[phaseIdx];
                    }, 4000);
                }
            }
        };

        xhr.onload = () => {
            if (processingInterval) clearInterval(processingInterval);
            if (xhr.status >= 200 && xhr.status < 300) {
                const result = JSON.parse(xhr.responseText);
                if (result.success) {
                    activeProjectPort = result.port;
                    dropzone.classList.add('upload-success');
                    uploadIcon.textContent = 'check_circle';
                    uploadIcon.style.color = 'var(--success)';
                    uploadText.style.display = 'none';
                    uploadFileInfo.style.display = 'block';

                    document.getElementById('upload-file-name').textContent = file.name;
                    document.getElementById('upload-file-meta').textContent = `${formatFileSize(file.size)} • ${result.file_count || '?'} files`;

                    projectInfoCard.style.display = 'block';
                    document.getElementById('project-port-display').textContent = `:${result.port}`;
                    document.getElementById('project-file-count').textContent = result.file_count || '—';
                    
                    const typeLabel = result.project_type?.label || (typeof result.project_type === 'string' ? result.project_type : 'Auto-detected');
                    document.getElementById('project-type-display').textContent = typeLabel;

                    resetBtn.style.display = 'inline-flex';
                    currentFiles = result.files || [];
                    renderFileTree(currentFiles);
                    initServerControls(Number(result.port));
                    setStatus(`Live on :${result.port}`, 'var(--success)');
                    showToast('Project uploaded successfully!', 'success');
                    resolve(result);
                } else {
                    handleError(result.error || 'Upload failed');
                }
            } else {
                let msg = 'Upload failed';
                try { msg = JSON.parse(xhr.responseText).detail || msg; } catch(e) {}
                handleError(msg);
            }
        };

        xhr.onerror = () => handleError('Network error during upload');
        xhr.ontimeout = () => handleError('Upload timed out.');

        function handleError(msg) {
            if (processingInterval) clearInterval(processingInterval);
            uploadIcon.textContent = 'cloud_upload';
            uploadIcon.style.color = 'var(--text-muted)';
            uploadText.innerHTML = `
                <p style="color:var(--text-primary); font-weight:600; font-size:0.95rem;">Drop project archive here</p>
                <p style="color:var(--text-muted); font-size:0.75rem; margin-top:0.375rem;">Supports .zip files up to 50MB</p>
            `;
            setStatus('Upload Failed', 'var(--error)');
            showToast(msg, 'error');
            reject(new Error(msg));
        }

        xhr.open('POST', '/api/project/upload');
        xhr.send(formData);
    });
}

function resetUpload() {
    const dropzone = document.getElementById('upload-dropzone');
    const uploadIcon = document.getElementById('upload-icon-glyph');
    const uploadText = document.getElementById('upload-text');
    const uploadFileInfo = document.getElementById('upload-file-info');
    const projectInfoCard = document.getElementById('project-info-card');
    const resetBtn = document.getElementById('upload-reset-btn');
    const fileInput = document.getElementById('project-file-input');

    activeProjectPort = null;
    dropzone.classList.remove('upload-success');
    uploadIcon.textContent = 'cloud_upload';
    uploadIcon.style.color = 'var(--text-muted)';
    uploadText.style.display = '';
    uploadText.innerHTML = `
        <p style="color:var(--text-primary); font-weight:600; font-size:0.95rem;">Drop project archive here</p>
        <p style="color:var(--text-muted); font-size:0.75rem; margin-top:0.375rem;">Supports .zip files up to 50MB</p>
    `;
    uploadFileInfo.style.display = 'none';
    projectInfoCard.style.display = 'none';
    resetBtn.style.display = 'none';
    fileInput.value = '';
    setStatus('Ready', 'var(--accent)');
}

function setStatus(text, color) {
    if (!statusText || !statusDot) return;
    statusText.textContent = text;
    statusDot.style.background = color;
    statusDot.style.boxShadow = `0 0 10px ${color}`;
}

// ── Analysis Execution ──────────────────────────────────────────────────────
async function runAnalysis() {
    let payload = {};
    if (currentMode === 'code') {
        const code = getEditorCode();
        if (!code.trim()) {
            showToast('Please enter some code first', 'error');
            return;
        }
        payload = {
            code: code,
            language: document.getElementById('language-select').value,
            analysis_options: { profile: currentProfile }
        };
    } else {
        if (!activeProjectPort) {
            showToast('Please upload a project archive first', 'error');
            return;
        }
        payload = {
            code: 'PORT:' + activeProjectPort,
            language: 'project',
            analysis_options: { profile: currentProfile }
        };
    }

    placeholderEl.style.display = 'none';
    reportContent.style.display = 'none';
    loadingEl.style.display = 'flex';
    if (window.Boneyard) {
        window.Boneyard.mount('boneyard-mount');
        window.Boneyard.updateStage(`Initializing ${currentProfile.toUpperCase()} profile`);
    } else {
        loadingStage.textContent = `Initializing ${currentProfile.toUpperCase()} profile`;
    }

    const codeBtn = document.getElementById('code-analyze-btn');
    const projBtn = document.getElementById('project-analyze-btn');
    if (codeBtn) codeBtn.disabled = true;
    if (projBtn) projBtn.disabled = true;

    setStatus('Analyzing...', 'var(--accent)');

    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            const errMsg = errData.detail || 'Analysis request failed';
            if (errMsg.includes('Project server not found')) resetUpload();
            throw new Error(errMsg);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            let parts = buffer.split('\n\n');
            buffer = parts.pop();

            for (const part of parts) {
                const line = part.split('\n').find(l => l.startsWith('data: '));
                if (line) {
                    try {
                        const data = JSON.parse(line.substring(6).trim());
                        if (data.event === 'stage') {
                            if (window.Boneyard) window.Boneyard.updateStage(data.msg);
                            else loadingStage.textContent = data.msg;
                        } else if (data.event === 'complete') {
                            currentReport = data.report;
                            showResults(currentReport);
                            setStatus('Complete', 'var(--success)');
                            showToast(`${currentProfile} analysis complete!`, 'success');
                        } else if (data.event === 'error') {
                            throw new Error(data.msg || 'Analysis error');
                        }
                    } catch (e) {}
                }
            }
        }
    } catch (err) {
        setStatus('Error', 'var(--error)');
        loadingEl.style.display = 'none';
        placeholderEl.style.display = 'flex';
        showToast(err.message || 'Analysis failed', 'error');
    } finally {
        if (codeBtn) codeBtn.disabled = false;
        if (projBtn) projBtn.disabled = false;
    }
}

function showResults(data) {
    loadingEl.style.display = 'none';
    reportContent.style.display = 'block';
    resultsNav.style.display = 'flex';
    reportContent.innerHTML = Report.renderOverview(data);

    // Performance
    const perfDash = document.getElementById('performance-dashboard');
    if (perfDash) perfDash.innerHTML = Report.renderPerformance(data.performance);

    // Testing
    const testBlocksContainer = document.getElementById('test-blocks-container');
    if (testBlocksContainer) {
        testBlocksContainer.innerHTML = Report.renderTesting(data);
        testBlocksContainer.onclick = (e) => {
            const row = e.target.closest('.test-row');
            if (!row) return;
            testBlocksContainer.querySelectorAll('.test-row').forEach(r => r.classList.remove('active'));
            row.classList.add('active');
            const index = parseInt(row.dataset.index);
            const testCase = data.testing.test_cases[index];
            const detailsContainer = document.getElementById('test-details-container');
            if (detailsContainer && testCase) detailsContainer.innerHTML = Report.renderTestDetails(testCase);
        };
    }

    if (data.testing) {
        const total = document.getElementById('test-total-count');
        const passed = document.getElementById('test-passed-count');
        const failed = document.getElementById('test-failed-count');
        const stab = document.getElementById('test-stability-score');
        if (total) total.textContent = data.testing.total_tests || 0;
        if (passed) passed.textContent = data.testing.passed || 0;
        if (failed) failed.textContent = data.testing.failed || 0;
        if (stab) stab.textContent = (data.testing.total_tests > 0) ? Math.round((data.testing.passed / data.testing.total_tests) * 100) + '%' : '0%';
    }

    switchView('execution');

    document.querySelectorAll('.test-cat-tab').forEach(tab => {
        tab.onclick = () => {
            document.querySelectorAll('.test-cat-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            const category = tab.dataset.category;
            const rows = testBlocksContainer?.querySelectorAll('.test-row') || [];
            rows.forEach(row => {
                row.style.display = (category === 'all' || row.dataset.category === category) ? '' : 'none';
            });
        };
    });
}

function restoreSessionState() {
    switchMode('code');
    switchView('selection');
}

function renderFileTree(files) {
    const treeEl = document.getElementById('project-file-tree');
    const listEl = document.getElementById('file-tree-list');
    const countEl = document.getElementById('file-tree-count');
    if (!treeEl || !listEl) return;
    if (!files || files.length === 0) {
        treeEl.style.display = 'none';
        return;
    }
    treeEl.style.display = 'block';
    if (countEl) countEl.textContent = `${files.length} files`;

    function getFileIcon(path) {
        const ext = path.split('.').pop().toLowerCase();
        const iconMap = { js: 'javascript', jsx: 'javascript', ts: 'javascript', tsx: 'javascript', py: 'code', php: 'php', html: 'html', css: 'css', json: 'data_object', md: 'description', zip: 'folder_zip' };
        return iconMap[ext] || 'description';
    }

    const sorted = [...files].sort((a, b) => a.path.localeCompare(b.path));
    listEl.innerHTML = sorted.slice(0, 100).map(f => `
        <div class="file-tree-item">
            <span class="material-symbols-outlined ft-icon-file">${getFileIcon(f.path)}</span>
            <span title="${f.path}">${f.path}</span>
            <span class="ft-size">${f.size_kb} KB</span>
        </div>
    `).join('');
}

function initServerControls(port) {
    const openBtn = document.getElementById('server-open-btn');
    const stopBtn = document.getElementById('server-stop-btn');
    const startBtn = document.getElementById('server-start-btn');
    const statusDotEl = document.getElementById('server-status-dot');
    const statusLabel = document.getElementById('server-status-label');

    if (openBtn) openBtn.onclick = () => window.open(`http://127.0.0.1:${port}`, '_blank');
    
    if (stopBtn) {
        stopBtn.onclick = async () => {
            try {
                stopBtn.disabled = true;
                const res = await fetch(`/api/project/${port}`, { method: 'DELETE' });
                if (res.ok) {
                    serverRunning = false;
                    stopBtn.style.display = 'none';
                    startBtn.style.display = 'inline-flex';
                    if (statusDotEl) statusDotEl.style.background = 'var(--accent-rose)';
                    if (statusLabel) statusLabel.textContent = 'Server Stopped';
                    setStatus('Server Stopped', 'var(--error)');
                }
            } catch (err) {
                showToast('Failed to stop server', 'error');
            } finally {
                stopBtn.disabled = false;
            }
        };
    }

    if (startBtn) {
        startBtn.onclick = async () => {
            try {
                startBtn.disabled = true;
                const res = await fetch(`/api/project/restart/${port}`, { method: 'POST' });
                if (res.ok) {
                    serverRunning = true;
                    startBtn.style.display = 'none';
                    stopBtn.style.display = 'inline-flex';
                    if (statusDotEl) statusDotEl.style.background = 'var(--accent-emerald)';
                    if (statusLabel) statusLabel.textContent = 'Server Live';
                    setStatus(`Live on :${port}`, 'var(--success)');
                }
            } catch (err) {
                showToast('Failed to restart server', 'error');
            } finally {
                startBtn.disabled = false;
            }
        };
    }
}
