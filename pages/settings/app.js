// ==================== 配置 ====================
const bridge = window.AstrBotPluginPage;
const context = await bridge.ready();

// ==================== 状态 ====================
let groups = [];
let currentGroup = null;
let originalSettings = null;
let currentSettings = null;

// ==================== 初始化 ====================

document.addEventListener('DOMContentLoaded', () => {
    
    loadGroups();
    document.getElementById('searchInput').addEventListener('input', handleSearch);
});


// ==================== 加载群列表 ====================
async function loadGroups() {
    const listEl = document.getElementById('groupList');
    const loadingEl = document.getElementById('groupLoading');

    try {
        groups = await bridge.apiGet("groups");
        if (!Array.isArray(groups)) groups = [];
        renderGroupList(groups);
    } catch (err) {
        listEl.innerHTML = `
            <div class="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="12" y1="8" x2="12" y2="12"></line>
                    <line x1="12" y1="16" x2="12.01" y2="16"></line>
                </svg>
                <div>加载失败，请刷新重试</div>
            </div>
        `;
        showToast('加载群聊列表失败', 'error');
    } finally {
        if (loadingEl) loadingEl.remove();
    }
}

// ==================== 渲染群列表 ====================
function renderGroupList(data) {
    const listEl = document.getElementById('groupList');

    if (data.length === 0) {
        listEl.innerHTML = `
            <div class="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                    <circle cx="9" cy="7" r="4"></circle>
                </svg>
                <div>暂无群聊</div>
            </div>
        `;
        return;
    }

    listEl.innerHTML = data.map(g => {
        const initial = (g.name || '群').charAt(0).toUpperCase();
        const isActive = currentGroup && currentGroup.id === g.id;
        return `
            <div class="group-item ${isActive ? 'active' : ''}" data-id="${g.id}" onclick="selectGroup(${g.id})">
                <div class="group-avatar">${initial}</div>
                <div class="group-info">
                    <div class="group-name">${escapeHtml(g.name || '未命名群聊')}</div>
                    <div class="group-meta">${g.member_count ? g.member_count + ' 人' : '群聊'}</div>
                </div>
                <div class="group-id">${g.id}</div>
            </div>
        `;
    }).join('');
}

// ==================== 搜索 ====================
function handleSearch(e) {
    const keyword = e.target.value.trim().toLowerCase();
    const filtered = groups.filter(g => 
        (g.name || '').toLowerCase().includes(keyword) ||
        String(g.id).includes(keyword)
    );
    renderGroupList(filtered);
}

// ==================== 选择群聊 ====================
async function selectGroup(groupId) {
    const group = groups.find(g => g.id === groupId);
    if (!group) return;

    currentGroup = group;

    // 更新列表高亮
    document.querySelectorAll('.group-item').forEach(el => {
        el.classList.toggle('active', parseInt(el.dataset.id) === groupId);
    });

    // 更新头部
    document.getElementById('panelTitle').textContent = escapeHtml(group.name || '未命名群聊');
    document.getElementById('panelSubtitle').textContent = `ID: ${group.id}`;
    document.getElementById('headerActions').style.display = 'flex';

    // 加载设置
    await loadGroupSettings(groupId);
}

// ==================== 加载群设置 ====================
async function loadGroupSettings(groupId) {
    const bodyEl = document.getElementById('contentBody');
    bodyEl.innerHTML = `
        <div class="loading-overlay" style="position: relative; background: transparent;">
            <div class="spinner"></div>
            <div class="loading-text">加载设置...</div>
        </div>
    `;

    try {
        const res = await bridge.apiGet("settings/load", { id: groupId });
        console.log('加载设置结果:', res);
        if (res.code != undefined) {
            throw new Error(res.msg || '加载设置失败');
        }

        renderSettingsForm(res);
    } catch (err) {
        bodyEl.innerHTML = `
            <div class="placeholder-panel">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="12" y1="8" x2="12" y2="12"></line>
                    <line x1="12" y1="16" x2="12.01" y2="16"></line>
                </svg>
                <div class="placeholder-text">加载设置失败: ${escapeHtml(err.message)}</div>
            </div>
        `;
        showToast('加载设置失败', 'error');
    }
}

// ==================== 渲染设置表单 ====================
function renderSettingsForm(data) {
    const bodyEl = document.getElementById('contentBody');

    bodyEl.innerHTML = `
        <div class="settings-card">
            <div class="settings-section">
                <div class="section-title">基础设置</div>

                <div class="form-row">
                    <div class="form-label">
                        <span class="form-label-text">功能开关</span>
                        <span class="form-hint">是否启用该群的管理功能</span>
                    </div>
                    <label class="toggle">
                        <input type="checkbox" id="enable" ${data.enable ? 'checked' : ''} onchange="updateSetting('enable', this.checked)">
                        <span class="toggle-slider"></span>
                    </label>
                </div>

                <div class="form-row">
                    <div class="form-label">
                        <span class="form-label-text">入群答案</span>
                        <span class="form-hint">设置该项后，申请需要携带此答案才可自动通过</span>
                    </div>
                    <input type="text" class="form-input" id="answer" value="${escapeHtml(data.answer || '')}" 
                        placeholder="输入入群答案..." onchange="updateSetting('answer', this.value)">
                </div>

                <div class="form-row">
                    <div class="form-label">
                        <span class="form-label-text">等级阈值</span>
                        <span class="form-hint">-1 表示不限制</span>
                    </div>
                    <input type="number" class="form-input" id="level" value="${data.level ?? -1}" 
                        onchange="updateSetting('level', parseInt(this.value))">
                </div>
            </div>

            <div class="settings-section">
                <div class="section-title">通知设置</div>

                <div class="form-row">
                    <div class="form-label">
                        <span class="form-label-text">通知开关</span>
                        <span class="form-hint">是否发送通知消息</span>
                    </div>
                    <label class="toggle">
                        <input type="checkbox" id="notify_enable" ${data.notify_enable ? 'checked' : ''} onchange="updateSetting('notify_enable', this.checked)">
                        <span class="toggle-slider"></span>
                    </label>
                </div>

                <div class="form-row">
                    <div class="form-label">
                        <span class="form-label-text">通知内容</span>
                        <span class="form-hint">通知消息的具体内容</span>
                    </div>
                    <textarea class="form-input" id="notify_content" placeholder="输入通知内容..." 
                        onchange="updateSetting('notify_content', this.value)">${escapeHtml(data.notify_content || '')}</textarea>
                </div>
            </div>
        </div>
    `;
}

// ==================== 更新本地设置 ====================
function updateSetting(key, value) {
    if (!currentSettings) currentSettings = {};
    currentSettings[key] = value;
}

// ==================== 重置设置 ====================
function resetSettings() {
    if (!originalSettings) return;
    currentSettings = JSON.parse(JSON.stringify(originalSettings));
    renderSettingsForm(currentSettings);
    showToast('已重置为原始设置');
}

// ==================== 保存设置 ====================
async function saveSettings() {
    if (!currentGroup || !currentSettings) return;

    const btn = document.getElementById('saveBtn');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<div class="spinner" style="width: 16px; height: 16px; border-width: 2px;"></div> 保存中...`;

    try {
        const payload = {
            id: currentGroup.id,
            ...currentSettings
        };
        const res = await bridge.apiPost("settings/save", payload);

        if (res.code == undefined) {
            originalSettings = JSON.parse(JSON.stringify(currentSettings));
            showToast('设置保存成功');
        } else {
            throw new Error(res.msg || '保存失败');
        }
    } catch (err) {
        showToast('保存失败: ' + err.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

// ==================== 工具函数 ====================
function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icon = type === 'success' 
        ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"></polyline></svg>'
        : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>';

    toast.innerHTML = `${icon}${escapeHtml(message)}`;
    container.appendChild(toast);

    setTimeout(() => toast.remove(), 3000);
}


window.selectGroup = selectGroup;
window.resetSettings = resetSettings;
window.saveSettings = saveSettings;
window.updateSetting = updateSetting;