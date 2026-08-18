/**
 * CareerMate AI — Resume Builder Client-Side Logic
 * Handles: multi-step navigation, dynamic entries, live preview,
 * AI generation/suggestions, template switching, PDF download
 */

// ===== State ===== 
let currentStep = 0;
let currentTemplate = 'classic';
let previewDebounceTimer = null;

const STEPS = [
    'personal', 'education', 'experience', 'internships',
    'projects', 'skills', 'certifications', 'achievements', 'courses'
];

// ===== Initialization =====
document.addEventListener('DOMContentLoaded', () => {
    initStepNavigation();
    initDynamicEntries();
    initTagInputs();
    initLivePreview();
    initTemplateSwitch();
    initAIButtons();
    initDownloadButton();
    showStep(0);
    triggerPreviewUpdate();
});

// ===== Step Navigation =====
function initStepNavigation() {
    document.querySelectorAll('.rb-step-btn').forEach((btn, index) => {
        btn.addEventListener('click', () => showStep(index));
    });
}

function showStep(index) {
    currentStep = index;
    document.querySelectorAll('.rb-section').forEach((sec, i) => {
        sec.classList.toggle('active', i === index);
    });
    document.querySelectorAll('.rb-step-btn').forEach((btn, i) => {
        btn.classList.toggle('active', i === index);
    });
}

function nextStep() {
    if (currentStep < STEPS.length - 1) showStep(currentStep + 1);
}

function prevStep() {
    if (currentStep > 0) showStep(currentStep - 1);
}

// ===== Dynamic Entries (Education, Experience, etc.) =====
function initDynamicEntries() {
    document.querySelectorAll('[data-add-entry]').forEach(btn => {
        btn.addEventListener('click', () => {
            const section = btn.getAttribute('data-add-entry');
            addEntry(section);
        });
    });

    // Event delegation for remove buttons
    document.addEventListener('click', (e) => {
        if (e.target.closest('.rb-entry-remove')) {
            const entry = e.target.closest('.rb-dynamic-entry');
            if (entry) {
                entry.style.animation = 'fadeOut 0.2s ease';
                setTimeout(() => {
                    entry.remove();
                    renumberEntries(entry.closest('[data-entries]'));
                    triggerPreviewUpdate();
                }, 200);
            }
        }
    });
}

function addEntry(section) {
    const container = document.querySelector(`[data-entries="${section}"]`);
    if (!container) return;

    const templates = {
        education: `
            <div class="rb-dynamic-entry">
                <div class="rb-entry-number">Education #${container.children.length + 1}</div>
                <button type="button" class="rb-btn rb-btn-danger rb-entry-remove">✕</button>
                <div class="rb-form-row">
                    <div class="rb-form-group">
                        <label class="rb-label">Degree</label>
                        <input type="text" class="rb-input" data-field="degree" placeholder="B.Tech in Computer Science" oninput="triggerPreviewUpdate()">
                    </div>
                    <div class="rb-form-group">
                        <label class="rb-label">University</label>
                        <input type="text" class="rb-input" data-field="university" placeholder="MIT, Stanford..." oninput="triggerPreviewUpdate()">
                    </div>
                </div>
                <div class="rb-form-row-3">
                    <div class="rb-form-group">
                        <label class="rb-label">CGPA</label>
                        <input type="text" class="rb-input" data-field="cgpa" placeholder="9.2" oninput="triggerPreviewUpdate()">
                    </div>
                    <div class="rb-form-group">
                        <label class="rb-label">Start Year</label>
                        <input type="text" class="rb-input" data-field="year_start" placeholder="2020" oninput="triggerPreviewUpdate()">
                    </div>
                    <div class="rb-form-group">
                        <label class="rb-label">End Year</label>
                        <input type="text" class="rb-input" data-field="year_end" placeholder="2024" oninput="triggerPreviewUpdate()">
                    </div>
                </div>
            </div>`,
        experience: `
            <div class="rb-dynamic-entry">
                <div class="rb-entry-number">Experience #${container.children.length + 1}</div>
                <button type="button" class="rb-btn rb-btn-danger rb-entry-remove">✕</button>
                <div class="rb-form-row">
                    <div class="rb-form-group">
                        <label class="rb-label">Job Title</label>
                        <input type="text" class="rb-input" data-field="title" placeholder="Software Engineer" oninput="triggerPreviewUpdate()">
                    </div>
                    <div class="rb-form-group">
                        <label class="rb-label">Company</label>
                        <input type="text" class="rb-input" data-field="company" placeholder="Google, Amazon..." oninput="triggerPreviewUpdate()">
                    </div>
                </div>
                <div class="rb-form-group">
                    <label class="rb-label">Duration</label>
                    <input type="text" class="rb-input" data-field="duration" placeholder="Jan 2023 - Present" oninput="triggerPreviewUpdate()">
                </div>
                <div class="rb-form-group">
                    <label class="rb-label">Description</label>
                    <div style="display:flex;gap:8px;align-items:start;">
                        <textarea class="rb-textarea" data-field="description" placeholder="Describe your role and achievements..." oninput="triggerPreviewUpdate()"></textarea>
                        <button type="button" class="rb-btn rb-btn-ai" onclick="aiGenerate(this, 'experience')">✨ Generate</button>
                    </div>
                </div>
            </div>`,
        internships: `
            <div class="rb-dynamic-entry">
                <div class="rb-entry-number">Internship #${container.children.length + 1}</div>
                <button type="button" class="rb-btn rb-btn-danger rb-entry-remove">✕</button>
                <div class="rb-form-row">
                    <div class="rb-form-group">
                        <label class="rb-label">Title</label>
                        <input type="text" class="rb-input" data-field="title" placeholder="ML Intern" oninput="triggerPreviewUpdate()">
                    </div>
                    <div class="rb-form-group">
                        <label class="rb-label">Company</label>
                        <input type="text" class="rb-input" data-field="company" placeholder="Company name" oninput="triggerPreviewUpdate()">
                    </div>
                </div>
                <div class="rb-form-group">
                    <label class="rb-label">Duration</label>
                    <input type="text" class="rb-input" data-field="duration" placeholder="May 2023 - Aug 2023" oninput="triggerPreviewUpdate()">
                </div>
                <div class="rb-form-group">
                    <label class="rb-label">Description</label>
                    <div style="display:flex;gap:8px;align-items:start;">
                        <textarea class="rb-textarea" data-field="description" placeholder="Describe your internship responsibilities..." oninput="triggerPreviewUpdate()"></textarea>
                        <button type="button" class="rb-btn rb-btn-ai" onclick="aiGenerate(this, 'internship')">✨ Generate</button>
                    </div>
                </div>
            </div>`,
        projects: `
            <div class="rb-dynamic-entry">
                <div class="rb-entry-number">Project #${container.children.length + 1}</div>
                <button type="button" class="rb-btn rb-btn-danger rb-entry-remove">✕</button>
                <div class="rb-form-row">
                    <div class="rb-form-group">
                        <label class="rb-label">Project Name</label>
                        <input type="text" class="rb-input" data-field="name" placeholder="CareerMate AI" oninput="triggerPreviewUpdate()">
                    </div>
                    <div class="rb-form-group">
                        <label class="rb-label">Tech Stack</label>
                        <input type="text" class="rb-input" data-field="tech_stack" placeholder="Python, Flask, Gemini API" oninput="triggerPreviewUpdate()">
                    </div>
                </div>
                <div class="rb-form-group">
                    <label class="rb-label">Project Link</label>
                    <input type="text" class="rb-input" data-field="link" placeholder="https://github.com/..." oninput="triggerPreviewUpdate()">
                </div>
                <div class="rb-form-group">
                    <label class="rb-label">Description</label>
                    <div style="display:flex;gap:8px;align-items:start;">
                        <textarea class="rb-textarea" data-field="description" placeholder="Brief description of the project..." oninput="triggerPreviewUpdate()"></textarea>
                        <button type="button" class="rb-btn rb-btn-ai" onclick="aiGenerate(this, 'project')">✨ Generate</button>
                    </div>
                </div>
            </div>`,
        certifications: `
            <div class="rb-dynamic-entry">
                <div class="rb-entry-number">Certification #${container.children.length + 1}</div>
                <button type="button" class="rb-btn rb-btn-danger rb-entry-remove">✕</button>
                <div class="rb-form-row-3">
                    <div class="rb-form-group">
                        <label class="rb-label">Name</label>
                        <input type="text" class="rb-input" data-field="name" placeholder="AWS Solutions Architect" oninput="triggerPreviewUpdate()">
                    </div>
                    <div class="rb-form-group">
                        <label class="rb-label">Issuer</label>
                        <input type="text" class="rb-input" data-field="issuer" placeholder="Amazon Web Services" oninput="triggerPreviewUpdate()">
                    </div>
                    <div class="rb-form-group">
                        <label class="rb-label">Year</label>
                        <input type="text" class="rb-input" data-field="year" placeholder="2024" oninput="triggerPreviewUpdate()">
                    </div>
                </div>
            </div>`,
        achievements: `
            <div class="rb-dynamic-entry">
                <div class="rb-entry-number">Achievement #${container.children.length + 1}</div>
                <button type="button" class="rb-btn rb-btn-danger rb-entry-remove">✕</button>
                <div class="rb-form-group">
                    <input type="text" class="rb-input" data-field="text" placeholder="Won 1st place at XYZ Hackathon 2024" oninput="triggerPreviewUpdate()">
                </div>
            </div>`,
        courses: `
            <div class="rb-dynamic-entry">
                <div class="rb-entry-number">Course #${container.children.length + 1}</div>
                <button type="button" class="rb-btn rb-btn-danger rb-entry-remove">✕</button>
                <div class="rb-form-group">
                    <input type="text" class="rb-input" data-field="text" placeholder="Machine Learning by Andrew Ng (Coursera)" oninput="triggerPreviewUpdate()">
                </div>
            </div>`
    };

    if (templates[section]) {
        container.insertAdjacentHTML('beforeend', templates[section]);
    }
}

function renumberEntries(container) {
    if (!container) return;
    container.querySelectorAll('.rb-entry-number').forEach((num, i) => {
        const label = num.textContent.split('#')[0].trim();
        num.textContent = `${label} #${i + 1}`;
    });
}

// ===== Tag Inputs (Skills) =====
function initTagInputs() {
    document.querySelectorAll('.rb-tag-input-container').forEach(container => {
        const input = container.querySelector('.rb-tag-input');
        if (!input) return;

        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ',') {
                e.preventDefault();
                const value = input.value.trim().replace(',', '');
                if (value) {
                    addTag(container, value);
                    input.value = '';
                    triggerPreviewUpdate();
                }
            } else if (e.key === 'Backspace' && !input.value) {
                const tags = container.querySelectorAll('.rb-tag');
                if (tags.length) {
                    tags[tags.length - 1].remove();
                    triggerPreviewUpdate();
                }
            }
        });

        container.addEventListener('click', () => input.focus());
    });

    // Event delegation for tag removal
    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('rb-tag-remove')) {
            e.target.closest('.rb-tag').remove();
            triggerPreviewUpdate();
        }
    });
}

function addTag(container, value) {
    const input = container.querySelector('.rb-tag-input');
    const tag = document.createElement('span');
    tag.className = 'rb-tag';
    tag.innerHTML = `${value}<span class="rb-tag-remove">×</span>`;
    container.insertBefore(tag, input);
}

// ===== Live Preview =====
function initLivePreview() {
    // Listen for all input changes
    document.querySelectorAll('.rb-form-panel').forEach(panel => {
        panel.addEventListener('input', () => triggerPreviewUpdate());
    });
}

function triggerPreviewUpdate() {
    clearTimeout(previewDebounceTimer);
    previewDebounceTimer = setTimeout(updatePreview, 400);
}

async function updatePreview() {
    const data = collectFormData();
    try {
        const response = await fetch('/resume/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ template: currentTemplate, data: data })
        });

        const result = await response.json();
        if (result.html) {
            const previewContent = document.getElementById('preview-content');
            if (previewContent) {
                let iframe = previewContent.querySelector('iframe');
                if (!iframe) {
                    iframe = document.createElement('iframe');
                    iframe.style.width = '100%';
                    iframe.style.border = 'none';
                    iframe.style.minHeight = '1050px';
                    iframe.style.backgroundColor = '#ffffff';
                    previewContent.appendChild(iframe);
                }

                iframe.onload = () => {
                    try {
                        const body = iframe.contentWindow.document.body;
                        const html = iframe.contentWindow.document.documentElement;
                        const height = Math.max(body.scrollHeight, body.offsetHeight, html.clientHeight, html.scrollHeight, html.offsetHeight, 1050);
                        iframe.style.height = height + 'px';
                        previewContent.style.minHeight = height + 'px';
                    } catch (e) {
                        iframe.style.height = '1050px';
                    }
                };

                iframe.srcdoc = result.html;

                // Hide empty state
                const empty = document.getElementById('preview-empty') || document.querySelector('.rb-preview-empty');
                if (empty) empty.style.display = 'none';
                previewContent.style.display = 'block';
            }
        }
    } catch (err) {
        console.error('Preview update failed:', err);
    }
}

function escapeAttr(str) {
    return str.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// ===== Template Switching =====
function initTemplateSwitch() {
    document.querySelectorAll('.rb-template-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            currentTemplate = btn.getAttribute('data-template');
            document.querySelectorAll('.rb-template-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            triggerPreviewUpdate();
        });
    });
}

// ===== Form Data Collection =====
function collectFormData() {
    const data = {
        personal: {},
        summary: '',
        education: [],
        experience: [],
        internships: [],
        projects: [],
        skills: { technical: [], soft: [], tools: [] },
        certifications: [],
        achievements: [],
        courses: []
    };

    // Personal & Summary
    document.querySelectorAll('#step-personal [data-field]').forEach(input => {
        const fieldName = input.getAttribute('data-field');
        if (fieldName === 'summary') {
            data.summary = input.value.trim();
        } else {
            data.personal[fieldName] = input.value.trim();
        }
    });

    // Dynamic sections
    ['education', 'experience', 'internships', 'projects', 'certifications'].forEach(section => {
        const container = document.querySelector(`[data-entries="${section}"]`);
        if (!container) return;
        container.querySelectorAll('.rb-dynamic-entry').forEach(entry => {
            const obj = {};
            entry.querySelectorAll('[data-field]').forEach(input => {
                obj[input.getAttribute('data-field')] = input.value.trim();
            });
            data[section].push(obj);
        });
    });

    // Skills (tag inputs)
    ['technical', 'soft', 'tools'].forEach(category => {
        const container = document.querySelector(`[data-skill-category="${category}"]`);
        if (!container) return;
        container.querySelectorAll('.rb-tag').forEach(tag => {
            const text = tag.childNodes[0].textContent.trim();
            if (text) data.skills[category].push(text);
        });
    });

    // Achievements & Courses (text entries)
    ['achievements', 'courses'].forEach(section => {
        const container = document.querySelector(`[data-entries="${section}"]`);
        if (!container) return;
        container.querySelectorAll('.rb-dynamic-entry').forEach(entry => {
            const input = entry.querySelector('[data-field="text"]');
            if (input && input.value.trim()) {
                data[section].push(input.value.trim());
            }
        });
    });

    return data;
}

// ===== AI Features =====
function initAIButtons() {
    // Suggest buttons are handled inline
}

async function aiGenerateSummary() {
    const summaryField = document.getElementById('summary-field');
    const btn = event?.target || document.querySelector('button[onclick="aiGenerateSummary()"]');
    if (!summaryField) return;

    const data = collectFormData();
    const contextText = summaryField.value.trim() || 
        `Candidate with skills in ${data.skills.technical.join(', ')}. Education: ${data.education.map(e => e.degree).join(', ')}.`;

    if (btn) {
        btn.classList.add('loading');
        btn.textContent = '';
    }

    try {
        const response = await fetch('/resume/ai/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: 'summary', data: { text: contextText } })
        });

        const result = await response.json();
        if (result.result) {
            summaryField.value = result.result;
            triggerPreviewUpdate();
        } else if (result.error) {
            showToast('AI Error', result.error);
        }
    } catch (err) {
        showToast('AI Error', 'Failed to generate summary. Please check your API key.');
    } finally {
        if (btn) {
            btn.classList.remove('loading');
            btn.textContent = '✨ Generate';
        }
    }
}

async function aiGenerate(button, type) {
    const entry = button.closest('.rb-dynamic-entry');
    if (!entry) return;

    const entryData = {};
    entry.querySelectorAll('[data-field]').forEach(input => {
        entryData[input.getAttribute('data-field')] = input.value.trim();
    });

    const roleOrProject = entryData.name || entryData.title || type;
    const rawNotes = entryData.description || '';

    button.classList.add('loading');
    const origText = button.textContent;
    button.textContent = '';

    try {
        const response = await fetch('/resume/ai/bullet-points', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ role_or_project: roleOrProject, raw_notes: rawNotes })
        });

        const result = await response.json();
        const textarea = entry.querySelector('[data-field="description"]');
        if (textarea) {
            if (result.bullets && result.bullets.length > 0) {
                textarea.value = result.bullets.map(b => `• ${b}`).join('\n');
            } else if (result.text || result.result) {
                textarea.value = result.text || result.result;
            }
            triggerPreviewUpdate();
        }
    } catch (err) {
        showToast('AI Error', 'Failed to generate bullet points. Please try again.');
    } finally {
        button.classList.remove('loading');
        button.textContent = origText;
    }
}

async function fetchFullResumeSuggestions() {
    const panel = document.getElementById('rb-full-suggestions-panel');
    const list = document.getElementById('rb-full-suggestions-list');
    const btn = event?.target || document.querySelector('button[onclick="fetchFullResumeSuggestions()"]');

    if (btn) {
        btn.classList.add('loading');
        btn.textContent = 'Analyzing...';
    }

    const resumeData = collectFormData();

    try {
        const response = await fetch('/resume/ai/suggestions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ resume_data: resumeData })
        });

        const result = await response.json();
        if (result.suggestions && result.suggestions.length > 0) {
            list.innerHTML = result.suggestions.map(s => `<li>${s}</li>`).join('');
            if (panel) {
                panel.style.display = 'block';
                panel.scrollIntoView({ behavior: 'smooth' });
            }
        } else if (result.result) {
            showToast('AI Review', result.result);
        }
    } catch (err) {
        showToast('AI Error', 'Failed to get suggestions. Please verify your connection.');
    } finally {
        if (btn) {
            btn.classList.remove('loading');
            btn.textContent = '💡 Get Suggestions';
        }
    }
}

async function aiSuggest(section, button) {
    const data = collectFormData();
    let content = '';

    if (section === 'skills') {
        content = JSON.stringify(data.skills);
    } else if (data[section]) {
        content = JSON.stringify(data[section]);
    }

    button.classList.add('loading');
    const origText = button.textContent;
    button.textContent = '';

    try {
        const response = await fetch('/resume/ai/suggest', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ section: section, content: content })
        });

        const result = await response.json();
        if (result.result) {
            showToast(`💡 Suggestions for ${section}`, result.result);
        }
    } catch (err) {
        showToast('AI Error', 'Failed to get suggestions.');
    } finally {
        button.classList.remove('loading');
        button.textContent = origText;
    }
}

// ===== Toast Notifications =====
function showToast(title, message) {
    let toast = document.getElementById('ai-toast');
    if (!toast) return;

    toast.querySelector('.rb-toast-title').innerHTML = title;
    toast.querySelector('.rb-toast-body').textContent = message;
    toast.classList.add('show');

    // Auto-hide after 10s
    clearTimeout(toast._timeout);
    toast._timeout = setTimeout(() => {
        toast.classList.remove('show');
    }, 10000);
}

function closeToast() {
    const toast = document.getElementById('ai-toast');
    if (toast) toast.classList.remove('show');
}

// ===== PDF Download =====
function initDownloadButton() {
    const btn = document.getElementById('download-pdf-btn');
    if (!btn) return;

    btn.addEventListener('click', async () => {
        const data = collectFormData();
        btn.disabled = true;
        btn.textContent = 'Generating...';

        try {
            const response = await fetch('/resume/download', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ template: currentTemplate, data: data })
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${data.personal.name || 'resume'}_resume.pdf`;
                document.body.appendChild(a);
                a.click();
                a.remove();
                window.URL.revokeObjectURL(url);
            } else if (response.status === 422) {
                const result = await response.json();
                const errList = result.details ? result.details.join('\n• ') : result.error;
                showToast('Validation Error', `Please fix the following:\n• ${errList}`);
            } else {
                const result = await response.json().catch(() => ({}));
                showToast('Download Error', result.error || 'Failed to generate PDF.');
            }
        } catch (err) {
            showToast('Download Error', 'Network error. Please try again.');
        } finally {
            btn.disabled = false;
            btn.textContent = '⬇ Download PDF';
        }
    });
}

// CSS fadeOut animation
const style = document.createElement('style');
style.textContent = `@keyframes fadeOut { from { opacity: 1; } to { opacity: 0; transform: translateY(-10px); } }`;
document.head.appendChild(style);
