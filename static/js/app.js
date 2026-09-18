// Global Application State
let currentSpaceId = null;
let currentProjectId = null;
let activeConversationId = null;
let currentQuizData = null;

document.addEventListener('DOMContentLoaded', async () => {
    console.log("Initializing AI Study Companion Application...");
    await checkAuthStatus();
    await loadSpacesAndProjects();
    switchTab('dashboard');
});

// Authentication Status
async function checkAuthStatus() {
    try {
        const res = await fetch('/api/auth/me');
        if (res.ok) {
            const data = await res.json();
            document.getElementById('user-name-display').innerText = data.username;
            document.getElementById('user-role-badge').innerText = data.role;
            document.getElementById('modal-auth').style.display = 'none';
            await loadSpacesAndProjects();
            switchTab('dashboard');
        } else {
            showAuthModal();
        }
    } catch (e) {
        showAuthModal();
    }
}

function showAuthModal() {
    document.getElementById('modal-auth').style.display = 'flex';
}

function switchAuthTab(mode) {
    const loginForm = document.getElementById('form-auth-login');
    const regForm = document.getElementById('form-auth-register');
    const loginBtn = document.getElementById('auth-tab-login');
    const regBtn = document.getElementById('auth-tab-register');

    if (mode === 'login') {
        loginForm.style.display = 'block';
        regForm.style.display = 'none';
        loginBtn.className = 'btn btn-primary';
        regBtn.className = 'btn btn-outline';
    } else {
        loginForm.style.display = 'none';
        regForm.style.display = 'block';
        loginBtn.className = 'btn btn-outline';
        regBtn.className = 'btn btn-primary';
    }
}

async function submitAuthLogin(e) {
    e.preventDefault();
    const username = document.getElementById('login-username-input').value.trim();
    const password = document.getElementById('login-password-input').value.trim();
    const errDiv = document.getElementById('login-error-msg');
    errDiv.style.display = 'none';

    try {
        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await res.json();
        if (res.ok) {
            document.getElementById('modal-auth').style.display = 'none';
            await checkAuthStatus();
        } else {
            errDiv.innerText = data.error || 'Invalid credentials';
            errDiv.style.display = 'block';
        }
    } catch (err) {
        errDiv.innerText = 'Login server error';
        errDiv.style.display = 'block';
    }
}

async function submitAuthRegister(e) {
    e.preventDefault();
    const username = document.getElementById('reg-username-input').value.trim();
    const email = document.getElementById('reg-email-input').value.trim();
    const password = document.getElementById('reg-password-input').value.trim();
    const errDiv = document.getElementById('reg-error-msg');
    errDiv.style.display = 'none';

    try {
        const res = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password })
        });
        const data = await res.json();
        if (res.ok) {
            document.getElementById('modal-auth').style.display = 'none';
            await checkAuthStatus();
        } else {
            errDiv.innerText = data.error || 'Registration failed';
            errDiv.style.display = 'block';
        }
    } catch (err) {
        errDiv.innerText = 'Registration server error';
        errDiv.style.display = 'block';
    }
}

async function handleLogout() {
    await fetch('/api/auth/logout', { method: 'POST' });
    document.getElementById('modal-auth').style.display = 'flex';
    document.getElementById('user-name-display').innerText = 'Guest';
}

// Tab Switching Navigation
function switchTab(tabId) {
    document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));

    const targetTab = document.getElementById(`tab-${tabId}`);
    if (targetTab) targetTab.classList.add('active');

    // Highlight active nav item
    const activeNav = Array.from(document.querySelectorAll('.nav-item')).find(el => el.getAttribute('onclick')?.includes(tabId));
    if (activeNav) activeNav.classList.add('active');

    // Scroll main view container to top cleanly
    const mainContent = document.querySelector('.main-content');
    if (mainContent) mainContent.scrollTop = 0;

    // Ensure active project ID before refreshing tab data
    ensureActiveProject().then(() => {
        if (tabId === 'dashboard') loadDashboardData();
        else if (tabId === 'materials') loadMaterialsList();
        else if (tabId === 'tutor') loadTutorMessages();
        else if (tabId === 'mastery') loadMasteryData();
        else if (tabId === 'flashcards') loadFlashcards();
        else if (tabId === 'conceptmap') loadConceptMapAndPlan();
        else if (tabId === 'analytics') loadProjectAnalytics();
    });
    if (tabId === 'admin') loadAdminDashboard();
}

async function ensureActiveProject() {
    if (currentProjectId) return currentProjectId;
    try {
        const res = await fetch('/api/projects');
        const projects = await res.json();
        if (projects && projects.length > 0) {
            currentProjectId = projects[0].id;
            currentSpaceId = projects[0].space_id;
            const selector = document.getElementById('project-selector');
            if (selector) selector.value = currentProjectId;
            const bcSpace = document.getElementById('bc-space');
            const bcProj = document.getElementById('bc-project');
            if (bcSpace) bcSpace.innerText = projects[0].space_name;
            if (bcProj) bcProj.innerText = projects[0].name;
        }
    } catch (e) {
        console.error("Error ensuring active project:", e);
    }
    return currentProjectId;
}

// Spaces & Projects Management
async function loadSpacesAndProjects() {
    try {
        const resSpaces = await fetch('/api/spaces');
        const spaces = await resSpaces.json();

        const resProjects = await fetch('/api/projects');
        const projects = await resProjects.json();

        const selector = document.getElementById('project-selector');
        selector.innerHTML = '<option value="">Select a Project...</option>';

        projects.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.id;
            opt.innerText = `${p.space_name} → ${p.name}`;
            selector.appendChild(opt);
        });

        if (projects.length > 0) {
            currentProjectId = projects[0].id;
            currentSpaceId = projects[0].space_id;
            selector.value = currentProjectId;
            document.getElementById('bc-space').innerText = projects[0].space_name;
            document.getElementById('bc-project').innerText = projects[0].name;
            loadDashboardData();
        }

        renderSpacesAndProjects(spaces, projects);
    } catch (e) {
        console.error("Failed to load spaces/projects:", e);
    }
}

function renderSpacesAndProjects(spaces, projects) {
    const container = document.getElementById('spaces-list');
    if (!container) return;

    if (!spaces || spaces.length === 0) {
        container.innerHTML = '<p style="color:var(--text-muted); font-size:13px;">No spaces created yet.</p>';
        return;
    }

    container.innerHTML = spaces.map(s => {
        const spaceProjects = projects.filter(p => p.space_id === s.id);
        const projectsHTML = spaceProjects.length > 0 
            ? spaceProjects.map(p => `
                <div class="project-item-chip ${p.id === currentProjectId ? 'active-proj' : ''}" onclick="switchProject(${p.id})">
                    <i class="fa-solid fa-folder-open" style="color:#818cf8;"></i>
                    <div style="flex:1;">
                        <strong style="font-size:13px; display:block;">${p.name}</strong>
                        <span style="font-size:11px; color:var(--text-muted);">${p.learning_goal || 'General Goal'}</span>
                    </div>
                    ${p.id === currentProjectId ? '<span class="badge high">Active</span>' : '<i class="fa-solid fa-chevron-right" style="font-size:11px; color:var(--text-muted);"></i>'}
                </div>
            `).join('')
            : '<p style="font-size:12px; color:var(--text-muted); margin-left:12px;">No projects in this space.</p>';

        return `
            <div class="space-card-box" style="background:rgba(17, 24, 39, 0.6); border:1px solid var(--glass-border); border-radius:14px; padding:16px; margin-bottom:14px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <div style="display:flex; align-items:center; gap:10px;">
                        <i class="fa-solid fa-layer-group" style="color:${s.icon_color || '#6366f1'}; font-size:18px;"></i>
                        <strong style="font-size:15px;">${s.name}</strong>
                    </div>
                    <span class="badge">${spaceProjects.length} Projects</span>
                </div>
                <p style="font-size:12px; color:var(--text-muted); margin-bottom:12px;">${s.description || 'Broad learning space'}</p>
                <div class="projects-flex-container" style="display:flex; flex-direction:column; gap:8px;">
                    ${projectsHTML}
                </div>
            </div>
        `;
    }).join('');
}

async function switchProject(projId) {
    if (!projId) return;
    currentProjectId = parseInt(projId);
    
    const selector = document.getElementById('project-selector');
    if (selector) selector.value = currentProjectId;

    try {
        const res = await fetch(`/api/projects/${currentProjectId}/summary`);
        if (res.ok) {
            const data = await res.json();
            document.getElementById('bc-space').innerText = data.project.space_name || 'Learning Space';
            document.getElementById('bc-project').innerText = data.project.name;
            
            // Reload all space/project chips to reflect active status
            const resSpaces = await fetch('/api/spaces');
            const spaces = await resSpaces.json();
            const resProjects = await fetch('/api/projects');
            const projects = await resProjects.json();
            renderSpacesAndProjects(spaces, projects);

            loadDashboardData();
        }
    } catch (e) {
        console.error("Error switching project:", e);
    }
}

// Dashboard Summary
async function loadDashboardData() {
    if (!currentProjectId) return;
    try {
        const res = await fetch(`/api/projects/${currentProjectId}/summary`);
        if (!res.ok) return;
        const data = await res.json();

        document.getElementById('dash-mastery').innerText = `${data.overall_mastery}%`;
        document.getElementById('dash-materials-cnt').innerText = data.materials_count;
        document.getElementById('dash-weak-cnt').innerText = data.weak_concepts_count;

        if (data.recommendations && data.recommendations.length > 0) {
            const rec = data.recommendations[0];
            document.getElementById('rec-title').innerText = rec.title;
            document.getElementById('rec-desc').innerText = rec.description;
        }
    } catch (e) {
        console.error("Error loading dashboard data:", e);
    }
}

// Materials Upload & Parsing
async function handleFileUpload(file) {
    if (!file || !currentProjectId) return;
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('project_id', currentProjectId);

    try {
        const res = await fetch('/api/materials/upload', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        if (res.ok) {
            alert(`File '${file.name}' uploaded successfully. Background processing started!`);
            loadMaterialsList();
        } else {
            alert(`Upload error: ${data.error}`);
        }
    } catch (e) {
        console.error("File upload error:", e);
    }
}

async function loadMaterialsList() {
    if (!currentProjectId) return;
    try {
        const res = await fetch(`/api/materials?project_id=${currentProjectId}`);
        const materials = await res.json();
        const tbody = document.getElementById('materials-table-body');
        
        if (!materials || materials.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:var(--text-muted); padding:20px;">No materials uploaded yet. Click above to upload a PDF document.</td></tr>';
            return;
        }

        tbody.innerHTML = materials.map(m => `
            <tr>
                <td><i class="fa-solid fa-file-pdf" style="color:#c084fc; margin-right:8px;"></i> <strong>${m.filename}</strong></td>
                <td><span class="badge ${m.status === 'ready' ? 'high' : ''}">${m.status.toUpperCase()}</span></td>
                <td>${m.chunk_count} chunks</td>
                <td>${(m.file_size / 1024).toFixed(1)} KB</td>
                <td>${new Date(m.uploaded_at).toLocaleDateString()}</td>
                <td>
                    <button class="btn btn-sm btn-outline" onclick="viewMaterialChunks('${m.id}')"><i class="fa-solid fa-eye"></i> View Chunks</button>
                </td>
            </tr>
        `).join('');
    } catch (e) {
        console.error("Error loading materials:", e);
    }
}

async function viewMaterialChunks(matId) {
    try {
        const res = await fetch(`/api/materials/${matId}/chunks`);
        const chunks = await res.json();
        if (!chunks || chunks.length === 0) {
            alert("No processed chunks found for this material yet.");
            return;
        }
        alert(`Extracted Chunks Preview (${chunks.length} total):\n\n` + chunks.slice(0, 3).map(c => `[Page ${c.page_number}]: ${c.content.substring(0, 120)}...`).join("\n\n"));
    } catch (e) {
        console.error("Error fetching chunks:", e);
    }
}

// AI Tutor Chat
async function loadTutorMessages() {
    if (!currentProjectId) return;
    try {
        const resConv = await fetch(`/api/tutor/conversations?project_id=${currentProjectId}`);
        const convs = await resConv.json();
        if (convs.length > 0) {
            activeConversationId = convs[0].id;
            const resMsgs = await fetch(`/api/tutor/messages?conversation_id=${activeConversationId}`);
            const messages = await resMsgs.json();
            renderChatMessages(messages);
        }
    } catch (e) {
        console.error("Error loading tutor messages:", e);
    }
}

function renderChatMessages(messages) {
    const container = document.getElementById('chat-messages');
    container.innerHTML = `
        <div class="chat-bubble assistant">
            <div class="bubble-header"><i class="fa-solid fa-graduation-cap"></i> AI Tutor</div>
            <p>Hello! I am your AI Academic Tutor. Ask me any question grounded in your course materials!</p>
        </div>
    `;

    messages.forEach(m => {
        const div = document.createElement('div');
        div.className = `chat-bubble ${m.role}`;
        
        let citationsHTML = '';
        if (m.citations && m.citations.length > 0) {
            citationsHTML = m.citations.map(c => `<span class="citation-chip"><i class="fa-solid fa-quote-left"></i> ${c.source} — Page ${c.page}</span>`).join(' ');
        }

        div.innerHTML = `
            <div class="bubble-header">${m.role === 'user' ? 'You' : 'AI Tutor'}</div>
            <div>${marked.parse(m.content)}</div>
            ${citationsHTML ? `<div style="margin-top:8px;">${citationsHTML}</div>` : ''}
        `;
        container.appendChild(div);
    });

    container.scrollTop = container.scrollHeight;
}

async function sendChatMessage() {
    const input = document.getElementById('chat-input');
    if (!input) return;
    const query = input.value.trim();
    if (!query) return;

    await ensureActiveProject();
    if (!currentProjectId) {
        alert("Please select or create an active project first!");
        return;
    }

    const container = document.getElementById('chat-messages');
    
    // Append User Message
    const userBubble = document.createElement('div');
    userBubble.className = 'chat-bubble user';
    userBubble.innerHTML = `
        <div class="bubble-header">You</div>
        <div>${marked.parse(query)}</div>
    `;
    container.appendChild(userBubble);
    input.value = '';
    container.scrollTop = container.scrollHeight;

    // Append Loading Indicator
    const loadingBubble = document.createElement('div');
    loadingBubble.className = 'chat-bubble assistant';
    loadingBubble.id = 'tutor-loading-indicator';
    loadingBubble.innerHTML = `
        <div class="bubble-header"><i class="fa-solid fa-graduation-cap"></i> AI Tutor</div>
        <p><i class="fa-solid fa-spinner fa-spin"></i> Analyzing context and generating grounded response...</p>
    `;
    container.appendChild(loadingBubble);
    container.scrollTop = container.scrollHeight;

    try {
        const res = await fetch('/api/tutor/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                project_id: currentProjectId,
                conversation_id: activeConversationId,
                query: query
            })
        });

        const data = await res.json();
        
        const loader = document.getElementById('tutor-loading-indicator');
        if (loader) loader.remove();

        if (res.ok) {
            activeConversationId = data.conversation_id;
            
            const warnBanner = document.getElementById('evidence-warning-banner');
            if (data.insufficient_evidence && warnBanner) {
                warnBanner.style.display = 'flex';
            } else if (warnBanner) {
                warnBanner.style.display = 'none';
            }

            const assistantBubble = document.createElement('div');
            assistantBubble.className = 'chat-bubble assistant';
            
            let citationsHTML = '';
            if (data.citations && data.citations.length > 0) {
                citationsHTML = data.citations.map(c => `<span class="citation-chip"><i class="fa-solid fa-quote-left"></i> ${c.source} — Page ${c.page}</span>`).join(' ');
            }

            assistantBubble.innerHTML = `
                <div class="bubble-header" style="display:flex; justify-content:space-between; align-items:center;">
                    <span><i class="fa-solid fa-graduation-cap"></i> AI Tutor</span>
                    <button class="btn btn-sm btn-outline" style="padding:2px 8px; font-size:11px;" onclick="speakText(this.parentElement.nextElementSibling.innerText)"><i class="fa-solid fa-volume-high" style="color:#818cf8;"></i> Listen</button>
                </div>
                <div>${marked.parse(data.answer)}</div>
                ${citationsHTML ? `<div style="margin-top:8px;">${citationsHTML}</div>` : ''}
            `;
            container.appendChild(assistantBubble);
            container.scrollTop = container.scrollHeight;
        } else {
            alert(`Tutor Error: ${data.error || 'Failed to process question'}`);
        }
    } catch (e) {
        console.error("Error sending tutor message:", e);
        const loader = document.getElementById('tutor-loading-indicator');
        if (loader) loader.remove();
        alert("Network error communicating with AI Tutor.");
    }
}

// Voice Learning (Speech Recognition & Speech Synthesis)
let isListening = false;

function startVoiceRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        alert("Speech Recognition is not supported by your browser. Please use Google Chrome or Microsoft Edge.");
        return;
    }

    const input = document.getElementById('chat-input');
    const micBtn = document.querySelector('.chat-input-box .btn-outline');

    if (isListening) return;

    try {
        const recognition = new SpeechRecognition();
        recognition.lang = 'en-US';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        recognition.onstart = function() {
            isListening = true;
            if (input) input.placeholder = "🎙️ Listening... Speak your question now...";
            if (micBtn) {
                micBtn.style.background = 'rgba(244, 63, 94, 0.3)';
                micBtn.style.borderColor = '#f43f5e';
            }
        };

        recognition.onresult = function(event) {
            isListening = false;
            const transcript = event.results[0][0].transcript;
            if (input) {
                input.value = transcript;
                input.placeholder = "Ask a question or click microphone to speak...";
            }
            if (micBtn) {
                micBtn.style.background = '';
                micBtn.style.borderColor = '';
            }
            // Auto-send voice query after recognition
            setTimeout(() => {
                sendChatMessage();
            }, 300);
        };

        recognition.onerror = function(event) {
            isListening = false;
            console.warn("Speech recognition error:", event.error);
            if (input) input.placeholder = "Ask a question or click microphone to speak...";
            if (micBtn) {
                micBtn.style.background = '';
                micBtn.style.borderColor = '';
            }
            if (event.error === 'not-allowed') {
                alert("Microphone access denied. Please allow microphone permissions in your browser address bar.");
            }
        };

        recognition.onend = function() {
            isListening = false;
            if (input) input.placeholder = "Ask a question or click microphone to speak...";
            if (micBtn) {
                micBtn.style.background = '';
                micBtn.style.borderColor = '';
            }
        };

        recognition.start();
    } catch (e) {
        console.error("Speech recognition start failed:", e);
        alert("Could not access microphone. Please check browser permissions.");
    }
}

function speakText(text) {
    if (!('speechSynthesis' in window)) {
        alert("Speech synthesis is not supported by your browser.");
        return;
    }
    
    // Stop any ongoing speech
    window.speechSynthesis.cancel();

    const cleanText = text.replace(/\[Source:.*?\]/g, '').replace(/[\*#_`]/g, '');
    const utterance = new SpeechSynthesisUtterance(cleanText.substring(0, 400));
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    window.speechSynthesis.speak(utterance);
}

// 3D Flashcards & Spaced Repetition
let activeDeck = [];
let currentDeckIndex = 0;
let isFlipped = false;

async function loadFlashcards() {
    await ensureActiveProject();
    if (!currentProjectId) return;
    try {
        const res = await fetch('/api/flashcards/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ project_id: currentProjectId })
        });
        const data = await res.json();
        activeDeck = data.flashcards || [];
        currentDeckIndex = 0;
        isFlipped = false;
        showFlashcard();
    } catch (e) {
        console.error("Error loading flashcards:", e);
    }
}

function showFlashcard() {
    if (!activeDeck || activeDeck.length === 0) return;
    const card = activeDeck[currentDeckIndex];
    const textEl = document.getElementById('card-text');
    if (textEl) {
        textEl.innerText = isFlipped ? card.back : card.front;
    }
}

function flipFlashcard() {
    if (activeDeck.length === 0) return;
    isFlipped = !isFlipped;
    showFlashcard();
}

function rateFlashcard(rating) {
    if (activeDeck.length === 0) return;
    currentDeckIndex = (currentDeckIndex + 1) % activeDeck.length;
    isFlipped = false;
    showFlashcard();
}

async function loadConceptMapAndPlan() {
    await ensureActiveProject();
    if (!currentProjectId) return;

    const timelineSelect = document.getElementById('plan-timeline-select');
    const hoursSelect = document.getElementById('plan-hours-select');
    const numWeeks = timelineSelect ? parseInt(timelineSelect.value) : 4;
    const hoursPerDay = hoursSelect ? parseInt(hoursSelect.value) : 2;

    const badge = document.getElementById('plan-timeline-badge');
    if (badge) badge.innerText = `${numWeeks} Weeks Timeline (${hoursPerDay}h/day)`;

    try {
        const resMap = await fetch(`/api/concepts/map/${currentProjectId}`);
        const mapData = await resMap.json();

        const canvas = document.getElementById('concept-map-canvas');
        if (mapData.nodes && mapData.nodes.length > 0) {
            canvas.innerHTML = mapData.nodes.map(n => `
                <div style="padding:16px 20px; background:linear-gradient(135deg, rgba(99, 102, 241, 0.25), rgba(168, 85, 247, 0.25)); border:1px solid var(--accent-indigo); border-radius:14px; text-align:center; min-width:140px; box-shadow:0 4px 12px rgba(0,0,0,0.3);">
                    <strong style="display:block; font-size:14px;">${n.label}</strong>
                    <span class="badge" style="margin-top:6px;">${n.mastery}% Mastery</span>
                </div>
            `).join('<i class="fa-solid fa-arrow-right" style="color:var(--text-muted); font-size:18px;"></i>');
        }

        const resPlan = await fetch('/api/learning-plan/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                project_id: currentProjectId,
                num_weeks: numWeeks,
                hours_per_day: hoursPerDay
            })
        });
        const planData = await resPlan.json();

        const listEl = document.getElementById('learning-plan-list');
        if (planData.weeks) {
            listEl.innerHTML = planData.weeks.map(w => `
                <div style="padding:16px; background:rgba(31, 41, 55, 0.4); border:1px solid var(--glass-border); border-radius:12px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:flex-start; gap:16px;">
                    <div style="flex:1;">
                        <strong style="font-size:15px; color:#818cf8; display:block;">Week ${w.week}: ${w.topic}</strong>
                        <p style="font-size:13px; color:var(--text-secondary); margin-top:6px; line-height:1.5;">${w.target}</p>
                    </div>
                    <span class="badge high" style="white-space:nowrap;"><i class="fa-solid fa-clock"></i> ${w.hours} Hrs/wk</span>
                </div>
            `).join('');
        }
    } catch (e) {
        console.error("Error loading concept map & plan:", e);
    }
}

// Adaptive Quiz & Assessment
async function generateNewQuiz() {
    if (!currentProjectId) return;
    const container = document.getElementById('quiz-container');
    container.innerHTML = '<div style="padding:40px; text-align:center;"><i class="fa-solid fa-spinner fa-spin" style="font-size:32px; color:var(--accent-indigo);"></i><p style="margin-top:12px;">Generating adaptive questions based on weak concepts...</p></div>';

    try {
        const res = await fetch('/api/quizzes/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ project_id: currentProjectId })
        });

        currentQuizData = await res.json();
        renderQuizForm(currentQuizData);
    } catch (e) {
        console.error("Error generating quiz:", e);
        container.innerHTML = '<p>Failed to generate quiz. Please try again.</p>';
    }
}

function renderQuizForm(quiz) {
    const container = document.getElementById('quiz-container');
    
    let html = `<h3><i class="fa-solid fa-list-check" style="color:#818cf8; margin-right:8px;"></i> ${quiz.title}</h3><form id="quiz-form" onsubmit="submitQuizForm(event)">`;
    
    quiz.questions.forEach((q, idx) => {
        html += `
            <div style="margin-top:20px; padding:20px; background:rgba(17, 24, 39, 0.7); border:1px solid var(--glass-border); border-radius:14px;">
                <p style="font-size:15px; font-weight:600;">Q${idx + 1} (${q.question_type.toUpperCase()}): ${q.question_text}</p>
        `;

        if (q.question_type === 'mcq') {
            q.options.forEach(opt => {
                html += `
                    <label style="display:flex; align-items:center; gap:10px; margin-top:10px; cursor:pointer; padding:8px 12px; border-radius:8px; background:rgba(31, 41, 55, 0.4);">
                        <input type="radio" name="q_${q.id}" value="${opt}" required>
                        <span style="font-size:14px;">${opt}</span>
                    </label>
                `;
            });
        } else if (q.question_type === 'open_ended') {
            html += `
                <textarea name="q_${q.id}" placeholder="Type your full answer here explaining the concept..." style="width:100%; margin-top:10px; padding:12px; border-radius:10px; background:rgba(31, 41, 55, 0.6); border:1px solid var(--glass-border); color:white; font-size:14px;" rows="3" required></textarea>
            `;
        }

        html += `</div>`;
    });

    html += `<button type="submit" class="btn btn-primary" style="margin-top:24px;"><i class="fa-solid fa-check"></i> Submit Assessment</button></form>`;
    container.innerHTML = html;
}

async function submitQuizForm(e) {
    e.preventDefault();
    if (!currentQuizData) return;

    const form = document.getElementById('quiz-form');
    const formData = new FormData(form);
    const answers = {};

    currentQuizData.questions.forEach(q => {
        answers[q.id] = formData.get(`q_${q.id}`);
    });

    try {
        const res = await fetch(`/api/quizzes/${currentQuizData.quiz_id}/submit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                project_id: currentProjectId,
                answers: answers
            })
        });

        const result = await res.json();
        renderQuizResults(result);
    } catch (err) {
        console.error("Submit quiz error:", err);
    }
}

function renderQuizResults(result) {
    const container = document.getElementById('quiz-container');
    let html = `
        <div style="text-align:center; padding:24px; background:rgba(17, 24, 39, 0.5); border-radius:16px;">
            <i class="fa-solid fa-award" style="font-size:52px; color:var(--accent-amber); margin-bottom:12px;"></i>
            <h2>Assessment Completed! Score: ${result.score_percent}%</h2>
            <p style="color:var(--text-muted); margin-top:6px;">${result.correct_questions} of ${result.total_questions} questions answered correctly.</p>
        </div>
        <div style="margin-top:24px; display:flex; flex-direction:column; gap:14px;">
    `;

    result.evaluations.forEach((item, idx) => {
        html += `
            <div style="padding:16px 20px; border-radius:12px; background:${item.is_correct ? 'rgba(16, 185, 129, 0.08)' : 'rgba(244, 63, 94, 0.08)'}; border:1px solid ${item.is_correct ? 'var(--accent-green)' : 'var(--accent-rose)'}">
                <p style="font-weight:600; font-size:14px;">Q${idx + 1}: ${item.question_text}</p>
                <p style="font-size:13px; margin-top:6px; color:var(--text-muted);">Your Answer: <em style="color:white;">${item.user_answer}</em></p>
                <p style="font-size:13px; margin-top:6px;"><strong>AI Feedback:</strong> ${item.feedback}</p>
            </div>
        `;
    });

    html += `</div><button class="btn btn-primary" onclick="generateNewQuiz()" style="margin-top:24px;"><i class="fa-solid fa-rotate"></i> Take Another Quiz</button>`;
    container.innerHTML = html;
}

// Concept Mastery & Growth
async function loadMasteryData() {
    if (!currentProjectId) return;
    try {
        const res = await fetch(`/api/mastery/${currentProjectId}`);
        const data = await res.json();

        const container = document.getElementById('mastery-cards-container');
        if (!data || data.length === 0) {
            container.innerHTML = '<p style="color:var(--text-muted); font-size:13px;">No concepts recorded yet for this project.</p>';
            return;
        }

        container.innerHTML = data.map(m => `
            <div class="mastery-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <strong style="font-size:15px;">${m.name}</strong>
                    <span class="badge ${m.trend === 'improving' ? 'high' : ''}">${m.trend.toUpperCase()}</span>
                </div>
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill" style="width: ${m.mastery_level}%"></div>
                </div>
                <div style="display:flex; justify-content:space-between; font-size:12px; color:var(--text-muted);">
                    <span>Category: ${m.category}</span>
                    <strong style="color:white;">${m.mastery_level}% Mastery</strong>
                </div>
            </div>
        `).join('');
    } catch (e) {
        console.error("Error loading mastery data:", e);
    }
}

// Project Analytics
async function loadProjectAnalytics() {
    if (!currentProjectId) return;
    try {
        const res = await fetch(`/api/analytics/project/${currentProjectId}`);
        const data = await res.json();

        document.getElementById('analytics-msgs').innerText = data.total_messages;
        document.getElementById('analytics-quizzes').innerText = data.total_quizzes;
        document.getElementById('analytics-score').innerText = `${data.average_score}%`;
        document.getElementById('analytics-cost').innerText = `$${data.total_cost_usd.toFixed(4)}`;
    } catch (e) {
        console.error("Error loading analytics:", e);
    }
}

// Admin Dashboard & AI Observability
async function loadAdminDashboard() {
    try {
        const resOverview = await fetch('/api/admin/overview');
        if (!resOverview.ok) {
            alert("Admin access restricted. Please log in as admin.");
            return;
        }
        const data = await resOverview.json();

        document.getElementById('admin-users').innerText = data.total_users;
        document.getElementById('admin-ai-reqs').innerText = data.total_ai_requests;
        document.getElementById('admin-latency').innerText = `${data.avg_latency_ms} ms`;
        document.getElementById('admin-jobs').innerText = data.active_background_jobs;

        const resLogs = await fetch('/api/admin/ai-logs');
        const logs = await resLogs.json();

        const tbody = document.getElementById('ai-logs-table-body');
        if (!logs || logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; color:var(--text-muted); padding:20px;">No AI logs recorded yet.</td></tr>';
            return;
        }

        tbody.innerHTML = logs.map(l => `
            <tr>
                <td><span class="badge">${l.feature}</span></td>
                <td><code>${l.model}</code></td>
                <td>${l.total_tokens}</td>
                <td>${l.latency_ms} ms</td>
                <td>$${(l.cost_usd || 0).toFixed(5)}</td>
                <td><span class="badge ${l.status === 'success' ? 'high' : ''}">${l.status.toUpperCase()}</span></td>
                <td>${new Date(l.timestamp).toLocaleTimeString()}</td>
            </tr>
        `).join('');
    } catch (e) {
        console.error("Error loading admin dashboard:", e);
    }
}

async function runAIEvaluations() {
    try {
        const res = await fetch('/api/admin/run-evaluations', { method: 'POST' });
        const data = await res.json();
        alert("Automated AI Evaluation Run Complete:\n\n" + data.evaluations.map(e => `[${e.feature}]: Groundedness=${e.groundedness_score}, Feedback: ${e.feedback}`).join("\n\n"));
    } catch (e) {
        console.error("Error running AI evaluations:", e);
    }
}

// Modal Helpers
function openCreateSpaceModal() {
    document.getElementById('modal-space').style.display = 'flex';
}

function openCreateProjectModal() {
    fetch('/api/spaces').then(r => r.json()).then(spaces => {
        const select = document.getElementById('project-space-select');
        select.innerHTML = spaces.map(s => `<option value="${s.id}">${s.name}</option>`).join('');
    });
    document.getElementById('modal-project').style.display = 'flex';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

async function submitCreateSpace() {
    const name = document.getElementById('space-name-input').value.trim();
    const desc = document.getElementById('space-desc-input').value.trim();
    if (!name) return;

    await fetch('/api/spaces', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description: desc })
    });

    closeModal('modal-space');
    loadSpacesAndProjects();
}

async function submitCreateProject() {
    const spaceId = document.getElementById('project-space-select').value;
    const name = document.getElementById('project-name-input').value.trim();
    const goal = document.getElementById('project-goal-input').value.trim();
    if (!name || !spaceId) return;

    await fetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ space_id: parseInt(spaceId), name, learning_goal: goal })
    });

    closeModal('modal-project');
    loadSpacesAndProjects();
}
