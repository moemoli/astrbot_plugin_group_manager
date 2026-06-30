<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { CircleCloseFilled, Download, Refresh, Search, Upload } from '@element-plus/icons-vue'
import { ElLoading, ElNotification } from 'element-plus'
import { initBridgeContext } from '@/request'
import { dataSourceName, getGroups, getSettingsLoad, hasSettings, saveSettings } from '@/data'
import type { GroupItem, SettingsExportItem, SettingsLoadData, WarningThreshold } from '@/data/types'

const MIN_LOADING_DISPLAY_MS = 200
const TABLE_REGION_WIDTH = 1080
const TABLE_REGION_HEIGHT = 520
const INFINITE_MODE_THRESHOLD = 50
const LAZY_BATCH_SIZE = 20

const RECALL_TYPE_OPTIONS = [
  { value: 'keywords', label: '关键词' },
  { value: 'chat_history', label: '聊天记录' },
  { value: 'links', label: '链接' },
  { value: 'group_recommend', label: '群推荐' },
  { value: 'friend_recommend', label: '好友推荐' },
  { value: 'cards', label: '卡片' },
  { value: 'at_admin', label: '@管理' },
]

const VIOLATION_ACTION_OPTIONS = [
  { value: 'warn', label: '仅警告' },
  { value: 'mute', label: '仅禁言' },
  { value: 'recall', label: '仅撤回' },
  { value: 'recall_warn', label: '撤回警告' },
  { value: 'recall_mute', label: '撤回禁言' },
  { value: 'recall_kick', label: '撤回踢出' },
]

const THRESHOLD_ACTION_OPTIONS = [
  { value: 'warn', label: '警告' },
  { value: 'mute', label: '禁言' },
  { value: 'recall', label: '撤回' },
  { value: 'kick', label: '踢出' },
  { value: 'recall_warn', label: '撤回警告' },
  { value: 'recall_mute', label: '撤回禁言' },
  { value: 'recall_kick', label: '撤回踢出' },
]

const loading = ref(true)
const error = ref('')
const cachedGroups = ref<GroupItem[]>([])
const currentPage = ref(1)
const displayCount = ref(20)
const searchKeyword = ref('')
const lazyVisibleCount = ref(LAZY_BATCH_SIZE)
const fileInputRef = ref<HTMLInputElement | null>(null)
const settingsDrawerVisible = ref(false)
const activeGroup = ref<GroupItem | null>(null)
const loadingSettings = ref(false)
const savingSettings = ref(false)

const keywordInputVisible = ref(false)
const keywordInputValue = ref('')
const keywordInputRef = ref<any>(null)

const defaultSettingsForm: SettingsLoadData = {
  enable: null, answer: null, level: null, notify_enable: null, notify_content: null,
  blacklist_global_enabled: null, blacklist_group_enabled: null,
  violation_recall_enabled: null, violation_recall_types: null, violation_keywords: null,
  violation_action: null, violation_mute_duration: null, warning_thresholds: null,
}
const settingsForm = ref<SettingsLoadData>({ ...defaultSettingsForm })

let loadingOverlay: ReturnType<typeof ElLoading.service> | null = null
let loadingStartedAt = 0
let closeOverlayTimer: ReturnType<typeof setTimeout> | null = null
const displayCountOptions = [10, 20, 30, 50, 100, 200]

const filteredGroups = computed(() => {
  const kw = searchKeyword.value.trim().toLowerCase()
  if (!kw) return cachedGroups.value
  return cachedGroups.value.filter((i) => i.name.toLowerCase().includes(kw) || i.id.toLowerCase().includes(kw))
})
const isInfiniteMode = computed(() => displayCount.value > INFINITE_MODE_THRESHOLD)
const pagedGroups = computed(() => filteredGroups.value.slice((currentPage.value - 1) * displayCount.value, currentPage.value * displayCount.value))
const lazyGroups = computed(() => filteredGroups.value.slice(0, lazyVisibleCount.value))
const hasMoreLazyGroups = computed(() => lazyVisibleCount.value < filteredGroups.value.length)

watch([searchKeyword, displayCount], () => { currentPage.value = 1; lazyVisibleCount.value = LAZY_BATCH_SIZE })
watch(filteredGroups, () => { currentPage.value = 1; lazyVisibleCount.value = LAZY_BATCH_SIZE })
watch(isInfiniteMode, () => { lazyVisibleCount.value = LAZY_BATCH_SIZE })

function closeLoadingOverlay() { loadingOverlay?.close(); loadingOverlay = null }

watch(loading, (isLoading) => {
  if (isLoading) {
    if (closeOverlayTimer) { clearTimeout(closeOverlayTimer); closeOverlayTimer = null }
    if (!loadingOverlay) { loadingOverlay = ElLoading.service({ lock: true, fullscreen: true, text: '\u52a0\u8f7d\u4e2d...', background: 'rgba(255,255,255,0.75)' }); loadingStartedAt = Date.now() }
    return
  }
  if (!loadingOverlay) return
  const r = Math.max(0, MIN_LOADING_DISPLAY_MS - (Date.now() - loadingStartedAt))
  closeOverlayTimer = setTimeout(() => { closeLoadingOverlay(); closeOverlayTimer = null }, r)
})

watch(error, (m) => { if (m) ElNotification.error({ title: '错误', message: '数据加载失败', position: 'bottom-right' }) })
function getAvatarText(n: string): string { return n.slice(0, 1).toUpperCase() }
function getAvatarUrl(gid: string): string { return 'https://p.qlogo.cn/gh/' + gid + '/' + gid + '/640' }
function loadMoreLazyGroups() { if (isInfiniteMode.value && hasMoreLazyGroups.value) lazyVisibleCount.value = Math.min(filteredGroups.value.length, lazyVisibleCount.value + LAZY_BATCH_SIZE) }
function onRefresh() { void loadGroups() }

function normalizeSettingsData(data: Partial<SettingsLoadData> | null | undefined): SettingsLoadData {
  return {
    enable: data?.enable ?? null, answer: data?.answer ?? null, level: data?.level ?? null,
    notify_enable: data?.notify_enable ?? null, notify_content: data?.notify_content ?? null,
    blacklist_global_enabled: data?.blacklist_global_enabled ?? null, blacklist_group_enabled: data?.blacklist_group_enabled ?? null,
    violation_recall_enabled: data?.violation_recall_enabled ?? null,
    violation_recall_types: Array.isArray(data?.violation_recall_types) ? [...data!.violation_recall_types!] : null,
    violation_keywords: Array.isArray(data?.violation_keywords) ? [...data!.violation_keywords!] : null,
    violation_action: data?.violation_action ?? null, violation_mute_duration: data?.violation_mute_duration ?? null,
    warning_thresholds: Array.isArray(data?.warning_thresholds) ? data!.warning_thresholds!.map((t) => ({ ...t })) : null,
  }
}

async function loadGroupSettings(group: GroupItem) {
  loadingSettings.value = true
  settingsForm.value = { ...defaultSettingsForm }
  try {
    const result = await getSettingsLoad(group.id)
    if (result.c === 0) { settingsForm.value = normalizeSettingsData(result.d); return }
    ElNotification.error({ title: '错误', message: '加载群设置失败', position: 'bottom-right' })
  } catch
    ElNotification.error({ title: '错误', message: '加载群设置失败', position: 'bottom-right' })
  } finally { loadingSettings.value = false }
}

async function persistGroupSettings(showNotice: boolean): Promise<boolean> {
  if (!activeGroup.value) return true
  savingSettings.value = true
  try {
    const payload = toSavePayload(activeGroup.value.id, { ...settingsForm.value })
    const result = await saveSettings(toSavePayload(activeGroup.value.id, JSON.parse(JSON.stringify(settingsForm.value))))
    if (result.c === 0) {
      settingsForm.value = normalizeSettingsData(result.d)
      if (showNotice) ElNotification.success({ title: '成功', message: '保存成功', position: 'bottom-right' })
      return true
    }
    ElNotification.error({ title: '错误', message: '保存失败', position: 'bottom-right' })
    return false
  } catch
    ElNotification.error({ title: '错误', message: '保存失败', position: 'bottom-right' })
    return false
  } finally { savingSettings.value = false }
}

async function onEditSettings(item: GroupItem) {
  activeGroup.value = item; settingsDrawerVisible.value = true
  await loadGroupSettings(item)
}
async function onSaveSettingsClick() { if (await persistGroupSettings(true)) settingsDrawerVisible.value = false }
async function onDrawerBeforeClose(done: () => void) { if (await persistGroupSettings(true)) done() }
function onDrawerClosed() { activeGroup.value = null; settingsForm.value = { ...defaultSettingsForm }; keywordInputVisible.value = false; keywordInputValue.value = "" }

function showKeywordInput() { keywordInputVisible.value = true; nextTick(() => { keywordInputRef.value?.focus() }) }
function addKeyword() {
  const v = keywordInputValue.value.trim()
  if (!v) { keywordInputVisible.value = false; return }
  if (!settingsForm.value.violation_keywords) settingsForm.value.violation_keywords = []
  if (!settingsForm.value.violation_keywords.includes(v)) settingsForm.value.violation_keywords.push(v)
  keywordInputValue.value = ""; keywordInputVisible.value = false
}
function removeKeyword(kw: string) { if (settingsForm.value.violation_keywords) settingsForm.value.violation_keywords = settingsForm.value.violation_keywords.filter((k) => k !== kw) }

function addThreshold() {
  if (!settingsForm.value.warning_thresholds) settingsForm.value.warning_thresholds = []
  settingsForm.value.warning_thresholds.push({ count: 3, operator: '>=', action: 'mute', mute_duration: 60 })
}
function removeThreshold(idx: number) { if (settingsForm.value.warning_thresholds) settingsForm.value.warning_thresholds.splice(idx, 1) }

async function onExport() {
  const all = cachedGroups.value
  if (!all.length) { ElNotification.error({ title: '错误', message: "没有可导出的群", position: "bottom-right" }); return }
  const n = ElNotification.info({ title: "正在导出", message: "正在检查各群配置状态...", position: "bottom-right", duration: 0 })
  try {
    const hs = await Promise.all(all.map(async (g) => ({ g, has: (await hasSettings(g.id)).c === 2 })))
    const gs = hs.filter((i) => i.has).map((i) => i.g)
    if (!gs.length) { ElNotification.warning({ title: '提示', message: "没有群存在配置，无需导出", position: "bottom-right" }); return }
    const sr = await Promise.all(gs.map(async (g) => ({ id: g.id, name: g.name, settings: (await getSettingsLoad(g.id)).c === 0 ? (await getSettingsLoad(g.id)).d : null })))
    const ed = sr.filter((i) => i.settings !== null)
    const b = new Blob([JSON.stringify(ed, null, 2)], { type: "application/json" })
    const u = URL.createObjectURL(b); const a = document.createElement("a"); a.href = u; a.download = "groups-settings-export.json"; a.click(); URL.revokeObjectURL(u)
    ElNotification.success({ title: '成功', message: "导出成功，共 " + ed.length + " 条配置", position: "bottom-right" })
  } catch { ElNotification.error({ title: '错误', message: "导出失败", position: "bottom-right" }) }
  finally { n.close() }
}
function onImportClick() { fileInputRef.value?.click() }

function toSavePayload(id: string, s: Record<string, unknown>) {
  return {
    id, enable: Boolean(s.enable), answer: typeof s.answer === "string" ? s.answer : "",
    level: typeof s.level === "number" ? s.level : 0, notify_enable: Boolean(s.notify_enable),
    notify_content: typeof s.notify_content === "string" ? s.notify_content : "",
    blacklist_global_enabled: Boolean(s.blacklist_global_enabled),
    blacklist_group_enabled: Boolean(s.blacklist_group_enabled),
    violation_recall_enabled: Boolean(s.violation_recall_enabled),
    violation_recall_types: Array.isArray(s.violation_recall_types) ? s.violation_recall_types : [],
    violation_keywords: Array.isArray(s.violation_keywords) ? s.violation_keywords : [],
    violation_action: typeof s.violation_action === "string" ? s.violation_action : "warn",
    violation_mute_duration: typeof s.violation_mute_duration === "number" ? s.violation_mute_duration : 60,
    warning_thresholds: Array.isArray(s.warning_thresholds) ? s.warning_thresholds : [],
  }
}

async function onImportChange(event: Event) {
  const input = event.target as HTMLInputElement; const file = input.files?.[0]
  if (!file) return
  try {
    const parsed: unknown = JSON.parse(await file.text())
    if (!Array.isArray(parsed)) throw new Error("invalid")
    const items = parsed.filter((i): i is { id: string; name: string; settings: Record<string, unknown> } =>
      i != null && typeof i === "object" && typeof (i as any).id === "string" && (i as any).settings != null && typeof (i as any).settings === "object")
    if (!items.length) { ElNotification.warning({ title: '提示', message: "文件中没有有效的配置数据", position: "bottom-right" }); return }
    const im = ElNotification.info({ title: "正在导入", message: "共 " + items.length + " 条配置，正在写入...", position: "bottom-right", duration: 0 })
    let ok = 0, fail = 0
    try {
      const rs = await Promise.allSettled(items.map(async (i) => { const r = await saveSettings(toSavePayload(i.id, i.settings)); if (r.c !== 0) throw new Error("fail") }))
      for (const r of rs) { if (r.status === "fulfilled") ok++; else fail++ }
    } finally { im.close() }
    if (!fail) ElNotification.success({ title: '成功', message: "导入完成，共 " + ok + " 条", position: "bottom-right" })
    else ElNotification.warning({ title: '提示', message: "导入完成，" + ok + " 成功，" + fail + " 失败", position: "bottom-right" })
  } catch { ElNotification.error({ title: '错误', message: "导入失败，请检查 JSON 格式", position: "bottom-right" }) }
  finally { input.value = "" }
}

async function loadGroups() {
  loading.value = true; error.value = ""
  try {
    const r = await getGroups()
    if (r.c === 0) { cachedGroups.value = r.d; return }
    cachedGroups.value = []; error.value = "请求失败(c=-1)"
  } catch (err) { cachedGroups.value = []; error.value = err instanceof Error ? err.message : "加载数据失败" }
  finally { loading.value = false }
}

onMounted(async () => { await initBridgeContext(); loadGroups() })
onBeforeUnmount(() => { if (closeOverlayTimer) { clearTimeout(closeOverlayTimer); closeOverlayTimer = null } closeLoadingOverlay() })
</script>
<template>
  <main class="page">
    <header class="toolbar">
      <el-button type="primary" :icon="Refresh" @click="onRefresh">刷新</el-button>
      <el-button :icon="Download" @click="onExport">导出</el-button>
      <el-button :icon="Upload" @click="onImportClick">导入</el-button>
      <el-input v-model="searchKeyword" class="search-box" placeholder="搜索群名称或群 ID" clearable>
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <input ref="fileInputRef" class="hidden-input" type="file" accept="application/json" @change="onImportChange" />
    </header>

    <section v-if="error" class="state error">
      <el-result title="加载失败" sub-title="主界面数据加载失败，请重试。" icon="error">
        <template #icon><el-icon size="52" color="#f56c6c"><CircleCloseFilled /></el-icon></template>
        <template #extra><div class="error-extra"><p class="error-detail">{{ error }}</p>
          <el-button type="primary" @click="loadGroups">重新加载</el-button></div></template>
      </el-result>
    </section>

    <section v-else class="panel">
      <div class="panel-meta">
        <span>当前数据源: {{ dataSourceName }}</span>
        <span>数据总量: {{ filteredGroups.length }}</span>
      </div>
      <div class="table-region" :style="{ width: TABLE_REGION_WIDTH + 'px', height: TABLE_REGION_HEIGHT + 'px' }">
        <div v-if="isInfiniteMode" v-infinite-scroll="loadMoreLazyGroups" class="table-scroll" :infinite-scroll-disabled="!hasMoreLazyGroups" :infinite-scroll-distance="30">
          <table class="group-table"><thead><tr><th>群头像</th><th>群信息</th><th>群当前人数 / 群最大人数</th><th>操作</th></tr></thead>
            <tbody><tr v-for="item in lazyGroups" :key="item.id">
              <td class="avatar-cell"><el-avatar :size="38" :src="getAvatarUrl(item.id)">{{ getAvatarText(item.name) }}</el-avatar></td>
              <td><div class="group-info"><span class="group-name">{{ item.name }}</span><span class="group-id">{{ item.id }}</span></div></td>
              <td>{{ item.now }} / {{ item.max }}</td>
              <td><el-button size="small" type="primary" text @click="onEditSettings(item)">设置</el-button></td>
            </tr></tbody></table>
          <div class="lazy-footer">已加载 {{ lazyGroups.length }} / {{ filteredGroups.length }}</div>
        </div>
        <div v-else class="table-scroll">
          <table class="group-table"><thead><tr><th>群头像</th><th>群信息</th><th>群当前人数 / 群最大人数</th><th>操作</th></tr></thead>
            <tbody><tr v-for="item in pagedGroups" :key="item.id">
              <td class="avatar-cell"><el-avatar :size="38" :src="getAvatarUrl(item.id)">{{ getAvatarText(item.name) }}</el-avatar></td>
              <td><div class="group-info"><span class="group-name">{{ item.name }}</span><span class="group-id">{{ item.id }}</span></div></td>
              <td>{{ item.now }} / {{ item.max }}</td>
              <td><el-button size="small" type="primary" text @click="onEditSettings(item)">设置</el-button></td>
            </tr></tbody></table>
        </div>
      </div>
      <footer class="table-footer">
        <div class="display-count"><span>展示数量</span>
          <el-select v-model="displayCount" class="count-select"><el-option v-for="c in displayCountOptions" :key="c" :label="c+''" :value="c" /></el-select>
        </div>
        <el-pagination v-if="!isInfiniteMode" v-model:current-page="currentPage" :page-size="displayCount" layout="prev, pager, next" :total="filteredGroups.length" />
        <span v-if="isInfiniteMode" class="mode-tip">无限滚动模式</span>
      </footer>
    </section>
    <el-drawer v-model="settingsDrawerVisible" title="群设置" size="520px" direction="rtl" :before-close="onDrawerBeforeClose" @closed="onDrawerClosed">
      <template #header>
        <div v-if="activeGroup" class="drawer-header-wrap">
          <div class="drawer-group-head">
            <el-avatar :size="42" :src="getAvatarUrl(activeGroup.id)">{{ getAvatarText(activeGroup.name) }}</el-avatar>
            <div class="drawer-group-meta"><span class="drawer-group-name">{{ activeGroup.name }}</span><span class="drawer-group-id">{{ activeGroup.id }}</span></div>
          </div>
          <el-button type="primary" :loading="savingSettings" @click="onSaveSettingsClick">保存</el-button>
        </div>
      </template>

      <div v-loading="loadingSettings" class="drawer-settings-scroll">
        <el-form label-width="110px" class="settings-form">
          <!-- Basic settings -->
          <el-form-item label="启用"><el-switch v-model="settingsForm.enable" :active-value="true" :inactive-value="false" /></el-form-item>
          <el-form-item label="回复内容"><el-input v-model="settingsForm.answer" type="textarea" :rows="4" placeholder="请输入回复内容" /></el-form-item>
          <el-form-item label="等级"><el-input-number v-model="settingsForm.level" :min="0" :max="100" /></el-form-item>
          <el-form-item label="通知开关"><el-switch v-model="settingsForm.notify_enable" :active-value="true" :inactive-value="false" /></el-form-item>
          <el-form-item label="通知内容"><el-input v-model="settingsForm.notify_content" type="textarea" :rows="6" placeholder="请输入通知内容" /></el-form-item>

          <el-divider />

          <!-- Blacklist settings -->
          <h4 class="section-title">黑名单设置</h4>
          <el-form-item label="启用全局黑名单"><el-switch v-model="settingsForm.blacklist_global_enabled" :active-value="true" :inactive-value="false" /></el-form-item>
          <el-form-item label="启用分群黑名单"><el-switch v-model="settingsForm.blacklist_group_enabled" :active-value="true" :inactive-value="false" /></el-form-item>

          <el-divider />

          <!-- Violation recall settings -->
          <h4 class="section-title">违规撤回设置</h4>
          <el-form-item label="启用违规撤回"><el-switch v-model="settingsForm.violation_recall_enabled" :active-value="true" :inactive-value="false" /></el-form-item>

          <template v-if="settingsForm.violation_recall_enabled">
            <el-form-item label="撤回类型">
              <el-checkbox-group v-model="settingsForm.violation_recall_types">
                <el-checkbox v-for="opt in RECALL_TYPE_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</el-checkbox>
              </el-checkbox-group>
            </el-form-item>

            <el-form-item v-if="settingsForm.violation_recall_types?.includes('keywords')" label="违规关键词">
              <div class="keyword-tags">
                <el-tag v-for="kw in settingsForm.violation_keywords" :key="kw" closable @close="removeKeyword(kw)">{{ kw }}</el-tag>
                <el-input v-if="keywordInputVisible" ref="keywordInputRef" v-model="keywordInputValue" size="small" class="keyword-input" placeholder="输入关键词" @keyup.enter="addKeyword" @blur="addKeyword" />
                <el-button v-else size="small" @click="showKeywordInput">+ 添加关键词</el-button>
              </div>
            </el-form-item>

            <el-form-item label="处理类型">
              <el-select v-model="settingsForm.violation_action" style="width: 100%;">
                <el-option v-for="opt in VIOLATION_ACTION_OPTIONS" :key="opt.value" :label="opt.label" :value="opt.value" />
              </el-select>
            </el-form-item>

            <el-form-item v-if="settingsForm.violation_action?.includes('mute')" label="禁言时间(秒)">
              <el-input-number v-model="settingsForm.violation_mute_duration" :min="1" :max="2592000" />
            </el-form-item>

            <el-divider />

            <!-- Warning thresholds -->
            <h4 class="section-title">警告阈值</h4>
            <p class="section-desc">按条件配置警告阈值，支持达到(>=)、大于(>)、小于(<)、小于等于(<=) 四种运算符，按次数从高到低匹配第一个命中的规则。</p>

            <div v-for="(threshold, idx) in settingsForm.warning_thresholds" :key="idx" class="threshold-row">
              <el-select v-model="threshold.operator" size="small" class="threshold-operator">
                <el-option value=">=" label="达到" />
                <el-option value=">" label="大于" />
                <el-option value="<" label="小于" />
                <el-option value="<=" label="小于等于" />
              </el-select>
              <el-input-number v-model="threshold.count" :min="1" :max="999" size="small" controls-position="right" class="threshold-count" />
              <span class="threshold-label">次时</span>
              <el-select v-model="threshold.action" size="small" class="threshold-action">
                <el-option v-for="opt in THRESHOLD_ACTION_OPTIONS" :key="opt.value" :label="opt.label" :value="opt.value" />
              </el-select>
              <template v-if="threshold.action?.includes('mute')">
                <span class="threshold-label">禁言</span>
                <el-input-number v-model="threshold.mute_duration" :min="1" :max="2592000" size="small" controls-position="right" class="threshold-duration" />
                <span class="threshold-label">秒</span>
              </template>
              <el-button type="danger" text size="small" @click="removeThreshold(idx)">删除</el-button>
            </div>
            <el-button size="small" class="add-threshold-btn" @click="addThreshold">+ 添加阈值规则</el-button>
          </template>
        </el-form>
      </div>
    </el-drawer>
  </main>
</template>
<style scoped>
.page { padding: 0; }
.toolbar { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-bottom: 20px; }
.toolbar :deep(.el-button) { border-radius: 8px; font-weight: 500; transition: all 0.2s ease; }
.toolbar :deep(.el-button:hover) { transform: translateY(-1px); box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
.search-box { width: 280px; margin-left: auto; }
.search-box :deep(.el-input__wrapper) { border-radius: 8px; box-shadow: 0 0 0 1px rgba(0,0,0,0.08) !important; transition: box-shadow 0.2s ease; }
.search-box :deep(.el-input__wrapper:hover), .search-box :deep(.el-input__wrapper.is-focus) { box-shadow: 0 0 0 1px #4f6ef7, 0 0 0 3px rgba(79,110,247,0.12) !important; }
.hidden-input { display: none; }
.state { min-height: calc(100vh - 160px); display: flex; align-items: center; justify-content: center; padding: 24px; border-radius: 12px; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.state.error { background: #fef2f2; border: 1px solid #fecaca; }
.error-extra { display: flex; flex-direction: column; align-items: center; gap: 12px; }
.error-detail { color: #b91c1c; font-size: 13px; }
.panel { background: #fff; border-radius: 12px; padding: 20px; display: flex; flex-direction: column; gap: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.02); }
.panel-meta { display: flex; gap: 20px; color: #9ca3af; font-size: 13px; font-weight: 500; }
.panel-meta span { display: flex; align-items: center; gap: 4px; }
.table-region { border: 1px solid #f0f0f0; border-radius: 10px; overflow: hidden; background: #fff; }
.table-scroll { width: 100%; height: 100%; overflow: auto; }
.group-table { width: 100%; border-collapse: collapse; }
.group-table th, .group-table td { text-align: left; padding: 14px 16px; }
.group-table th { position: sticky; top: 0; z-index: 1; background: #fafbfc; color: #6b7280; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #f0f0f0; }
.group-table td { border-bottom: 1px solid #f5f5f5; transition: background 0.15s ease; }
.group-table tbody tr:hover td { background: #f8faff; }
.group-table tbody tr:last-child td { border-bottom: none; }
.avatar-cell { width: 80px; }
.group-info { display: flex; flex-direction: column; gap: 2px; }
.group-name { font-weight: 600; color: #1f2937; font-size: 14px; }
.group-id { color: #9ca3af; font-size: 12px; font-family: 'SF Mono', 'Fira Code', monospace; }
.group-table td:nth-child(3) { color: #6b7280; font-size: 13px; font-variant-numeric: tabular-nums; }
.group-table td:last-child .el-button { border-radius: 6px; font-weight: 500; }
.table-footer { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.display-count { display: flex; align-items: center; gap: 8px; color: #9ca3af; font-size: 13px; }
.count-select { width: 100px; }
.lazy-footer, .mode-tip { font-size: 12px; color: #9ca3af; text-align: center; padding: 10px 0; }
.drawer-header-wrap { width: 100%; display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.drawer-group-head { display: flex; align-items: center; gap: 12px; }
.drawer-group-meta { display: flex; flex-direction: column; gap: 2px; }
.drawer-group-name { font-weight: 700; font-size: 15px; color: #1f2937; }
.drawer-group-id { font-size: 12px; color: #9ca3af; font-family: 'SF Mono', 'Fira Code', monospace; }
.drawer-settings-scroll { height: calc(100vh - 180px); overflow: auto; padding: 8px 4px 16px 0; }
.settings-form :deep(.el-form-item__label) { font-weight: 500; color: #374151; }
.settings-form :deep(.el-input__wrapper), .settings-form :deep(.el-textarea__inner) { border-radius: 8px; }
.settings-form :deep(.el-switch) { --el-switch-on-color: #4f6ef7; }
.section-title { font-size: 15px; font-weight: 600; color: #1f2937; margin: 0 0 4px 0; }
.section-desc { font-size: 12px; color: #9ca3af; margin: 0 0 12px 0; line-height: 1.5; }
.keyword-tags { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.keyword-input { width: 120px; }
.threshold-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-bottom: 10px; padding: 8px 10px; background: #f9fafb; border-radius: 8px; border: 1px solid #f0f0f0; }
.threshold-label { font-size: 13px; color: #374151; white-space: nowrap; }
.threshold-operator { width: 100px; }
.threshold-count { width: 80px; }
.threshold-action { width: 110px; }
.threshold-duration { width: 80px; }
.add-threshold-btn { margin-top: 4px; }
</style>
