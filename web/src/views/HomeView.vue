<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { CircleCloseFilled, Download, Refresh, Search, Upload } from '@element-plus/icons-vue'
import { ElLoading, ElMessage, ElNotification } from 'element-plus'
import { dataSourceName, getGroups, getSettingsLoad, hasSettings, saveSettings } from '@/data'
import type { GroupItem, SettingsExportItem, SettingsLoadData } from '@/data/types'

const MIN_LOADING_DISPLAY_MS = 200
const TABLE_REGION_WIDTH = 1080
const TABLE_REGION_HEIGHT = 520
const INFINITE_MODE_THRESHOLD = 50
const LAZY_BATCH_SIZE = 20

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

const defaultSettingsForm: SettingsLoadData = {
  enable: null,
  answer: null,
  level: null,
  notify_enable: null,
  notify_content: null,
}
const settingsForm = ref<SettingsLoadData>({ ...defaultSettingsForm })

let loadingOverlay: ReturnType<typeof ElLoading.service> | null = null
let loadingStartedAt = 0
let closeOverlayTimer: ReturnType<typeof setTimeout> | null = null

const displayCountOptions = [10, 20, 30, 50, 100, 200]

const filteredGroups = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  if (!keyword) {
    return cachedGroups.value
  }

  return cachedGroups.value.filter((item) => {
    return item.name.toLowerCase().includes(keyword) || item.id.toLowerCase().includes(keyword)
  })
})

const isInfiniteMode = computed(() => displayCount.value > INFINITE_MODE_THRESHOLD)

const pagedGroups = computed(() => {
  const start = (currentPage.value - 1) * displayCount.value
  const end = start + displayCount.value
  return filteredGroups.value.slice(start, end)
})

const lazyGroups = computed(() => {
  return filteredGroups.value.slice(0, lazyVisibleCount.value)
})

const hasMoreLazyGroups = computed(() => lazyVisibleCount.value < filteredGroups.value.length)

watch([searchKeyword, displayCount], () => {
  currentPage.value = 1
  lazyVisibleCount.value = LAZY_BATCH_SIZE
})

watch(filteredGroups, () => {
  currentPage.value = 1
  lazyVisibleCount.value = LAZY_BATCH_SIZE
})

watch(isInfiniteMode, () => {
  lazyVisibleCount.value = LAZY_BATCH_SIZE
})

function closeLoadingOverlay() {
  loadingOverlay?.close()
  loadingOverlay = null
}

watch(loading, (isLoading) => {
  if (isLoading) {
    if (closeOverlayTimer) {
      clearTimeout(closeOverlayTimer)
      closeOverlayTimer = null
    }

    if (!loadingOverlay) {
      loadingOverlay = ElLoading.service({
        lock: true,
        fullscreen: true,
        text: '加载中...',
        background: 'rgba(255, 255, 255, 0.75)',
      })
      loadingStartedAt = Date.now()
    }
    return
  }

  if (!loadingOverlay) {
    return
  }

  const elapsed = Date.now() - loadingStartedAt
  const remaining = Math.max(0, MIN_LOADING_DISPLAY_MS - elapsed)
  closeOverlayTimer = setTimeout(() => {
    closeLoadingOverlay()
    closeOverlayTimer = null
  }, remaining)
})

watch(error, (message) => {
  if (!message) {
    return
  }
  ElMessage.error({ message: '数据加载失败', position: 'bottom-right' })
})

function getAvatarText(name: string): string {
  return name.slice(0, 1).toUpperCase()
}

function getAvatarUrl(groupId: string): string {
  return `https://p.qlogo.cn/gh/${groupId}/${groupId}/640`
}

function loadMoreLazyGroups() {
  if (!isInfiniteMode.value || !hasMoreLazyGroups.value) {
    return
  }
  lazyVisibleCount.value = Math.min(filteredGroups.value.length, lazyVisibleCount.value + LAZY_BATCH_SIZE)
}

function onRefresh() {
  void loadGroups()
}

function normalizeSettingsData(data: Partial<SettingsLoadData> | null | undefined): SettingsLoadData {
  return {
    enable: data?.enable ?? null,
    answer: data?.answer ?? null,
    level: data?.level ?? null,
    notify_enable: data?.notify_enable ?? null,
    notify_content: data?.notify_content ?? null,
  }
}

async function loadGroupSettings(group: GroupItem) {
  loadingSettings.value = true
  settingsForm.value = { ...defaultSettingsForm }

  try {
    const result = await getSettingsLoad(group.id)
    if (result.c === 0) {
      settingsForm.value = normalizeSettingsData(result.d)
      return
    }

    ElMessage.error({ message: '加载群设置失败', position: 'bottom-right' })
  } catch {
    ElMessage.error({ message: '加载群设置失败', position: 'bottom-right' })
  } finally {
    loadingSettings.value = false
  }
}

async function persistGroupSettings(showSuccessNotice: boolean): Promise<boolean> {
  if (!activeGroup.value) {
    return true
  }

  savingSettings.value = true
  try {
    const result = await saveSettings({ id: activeGroup.value.id, ...settingsForm.value })
    if (result.c !== 0) {
      ElMessage.error({ message: '保存设置失败', position: 'bottom-right' })
      return false
    }

    settingsForm.value = normalizeSettingsData(result.d)
    if (showSuccessNotice) {
      ElNotification.success({
        title: '保存成功',
        position: 'bottom-right',
        message: `${activeGroup.value.name} 设置已保存`,
      })
    }
    return true
  } catch {
    ElMessage.error({ message: '保存设置失败', position: 'bottom-right' })
    return false
  } finally {
    savingSettings.value = false
  }
}

async function onEditSettings(item: GroupItem) {
  activeGroup.value = item
  settingsDrawerVisible.value = true
  await loadGroupSettings(item)
}

async function onSaveSettingsClick() {
  const saved = await persistGroupSettings(true)
  if (saved) {
    settingsDrawerVisible.value = false
  }
}

async function onDrawerBeforeClose(done: () => void) {
  const saved = await persistGroupSettings(true)
  if (saved) {
    done()
  }
}

function onDrawerClosed() {
  activeGroup.value = null
  settingsForm.value = { ...defaultSettingsForm }
}

async function onExport() {
  const allGroups = cachedGroups.value
  if (allGroups.length === 0) {
    ElMessage.error({ message: '没有可导出的群', position: 'bottom-right' })
    return
  }

  const exportingNotice = ElNotification.info({
    title: '正在导出',
    message: '正在检查各群配置状态...',
    position: 'bottom-right',
    duration: 0,
  })

  try {
    const hasSettingsResults = await Promise.all(
      allGroups.map(async (group) => {
        const result = await hasSettings(group.id)
        return { group, has: result.c === 2 }
      }),
    )

    const groupsWithSettings = hasSettingsResults
      .filter((item) => item.has)
      .map((item) => item.group)

    if (groupsWithSettings.length === 0) {
      ElMessage.warning({ message: '没有群存在配置，无需导出', position: 'bottom-right' })
      return
    }

    const settingsResults = await Promise.all(
      groupsWithSettings.map(async (group) => {
        const result = await getSettingsLoad(group.id)
        return {
          id: group.id,
          name: group.name,
          settings: result.c === 0 ? result.d : null,
        }
      }),
    )

    const exportData = settingsResults.filter((item) => item.settings !== null)
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'groups-settings-export.json'
    link.click()
    URL.revokeObjectURL(url)
    ElMessage.success({ message: `导出成功，共 ${exportData.length} 条配置`, position: 'bottom-right' })
  } catch {
    ElMessage.error({ message: '导出失败', position: 'bottom-right' })
  } finally {
    exportingNotice.close()
  }
}

function onImportClick() {
  fileInputRef.value?.click()
}


function toSavePayload(id: string, settings: Record<string, unknown>) {
  return {
    id,
    enable: Boolean(settings.enable),
    answer: typeof settings.answer === 'string' ? settings.answer : '',
    level: typeof settings.level === 'number' ? settings.level : 0,
    notify_enable: Boolean(settings.notify_enable),
    notify_content: typeof settings.notify_content === 'string' ? settings.notify_content : '',
  }
}

async function onImportChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) {
    return
  }

  try {
    const text = await file.text()
    const parsed: unknown = JSON.parse(text)

    if (!Array.isArray(parsed)) {
      throw new Error('导入文件格式无效')
    }

    const items = parsed.filter(
      (item): item is { id: string; name: string; settings: Record<string, unknown> } =>
        item != null
        && typeof item === 'object'
        && typeof (item as Record<string, unknown>).id === 'string'
        && (item as Record<string, unknown>).settings != null
        && typeof (item as Record<string, unknown>).settings === 'object',
    )

    if (items.length === 0) {
      ElMessage.warning({ message: '文件中没有有效的配置数据', position: 'bottom-right' })
      return
    }

    const importingNotice = ElNotification.info({
      title: '正在导入',
        message: `共 ${items.length} 条配置，正在写入...`,
      position: 'bottom-right',
      duration: 0,
    })

    let successCount = 0
    let failCount = 0

    try {
      const results = await Promise.allSettled(
        items.map(async (item) => {
          const result = await saveSettings(toSavePayload(item.id, item.settings))
          if (result.c !== 0) {
            throw new Error('保存失败: ' + item.id)
          }
          return item.id
        }),
      )

      for (const r of results) {
        if (r.status === 'fulfilled') {
          successCount++
        } else {
          failCount++
        }
      }
    } finally {
      importingNotice.close()
    }

    if (failCount === 0) {
      ElMessage.success({ message: '导入完成，共 ' + successCount + ' 条', position: 'bottom-right' })
    } else {
      ElMessage.warning({
        message: '导入完成：' + successCount + ' 成功，' + failCount + ' 失败',
        position: 'bottom-right',
      })
    }
  } catch {
    ElMessage.error({ message: '导入失败，请检查 JSON 格式', position: 'bottom-right' })
  } finally {
    input.value = ''
  }
}
async function loadGroups() {
  loading.value = true
  error.value = ''

  try {
    const result = await getGroups()

    if (result.c === 0) {
      cachedGroups.value = result.d
      return
    }

    cachedGroups.value = []
    error.value = '请求失败(c=-1)'
  } catch (err) {
    cachedGroups.value = []
    error.value = err instanceof Error ? err.message : '加载数据失败'
  } finally {
    loading.value = false
  }
}

onMounted(loadGroups)

onBeforeUnmount(() => {
  if (closeOverlayTimer) {
    clearTimeout(closeOverlayTimer)
    closeOverlayTimer = null
  }
  closeLoadingOverlay()
})
</script>

<template>
  <main class="page">
    <header class="toolbar">
      <el-button type="primary" :icon="Refresh" @click="onRefresh">刷新</el-button>
      <el-button :icon="Download" @click="onExport">导出</el-button>
      <el-button :icon="Upload" @click="onImportClick">导入</el-button>
      <el-input
        v-model="searchKeyword"
        class="search-box"
        placeholder="搜索群名称或群 ID"
        clearable
      >
        <template #prefix>
          <el-icon>
            <Search />
          </el-icon>
        </template>
      </el-input>
      <input
        ref="fileInputRef"
        class="hidden-input"
        type="file"
        accept="application/json"
        @change="onImportChange"
      />
    </header>

    <section v-if="error" class="state error">
      <el-result title="加载失败" sub-title="主界面数据加载失败，请重试。" icon="error">
        <template #icon>
          <el-icon size="52" color="#f56c6c">
            <CircleCloseFilled />
          </el-icon>
        </template>
        <template #extra>
          <div class="error-extra">
            <p class="error-detail">{{ error }}</p>
            <el-button type="primary" @click="loadGroups">重新加载</el-button>
          </div>
        </template>
      </el-result>
    </section>

    <section v-else class="panel">
      <div class="panel-meta">
        <span>当前数据源: {{ dataSourceName }}</span>
        <span>数据总量: {{ filteredGroups.length }}</span>
      </div>

      <div class="table-region" :style="{ width: `${TABLE_REGION_WIDTH}px`, height: `${TABLE_REGION_HEIGHT}px` }">
        <div
          v-if="isInfiniteMode"
          v-infinite-scroll="loadMoreLazyGroups"
          class="table-scroll"
          :infinite-scroll-disabled="!hasMoreLazyGroups"
          :infinite-scroll-distance="30"
        >
          <table class="group-table">
            <thead>
              <tr>
                <th>群头像</th>
                <th>群信息</th>
                <th>群当前人数 / 群最大人数</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in lazyGroups" :key="item.id">
                <td class="avatar-cell">
                  <el-avatar :size="38" :src="getAvatarUrl(item.id)">
                    {{ getAvatarText(item.name) }}
                  </el-avatar>
                </td>
                <td>
                  <div class="group-info">
                    <span class="group-name">{{ item.name }}</span>
                    <span class="group-id">{{ item.id }}</span>
                  </div>
                </td>
                <td>{{ item.now }} / {{ item.max }}</td>
                <td>
                  <el-button size="small" type="primary" text @click="onEditSettings(item)">
                    设置
                  </el-button>
                </td>
              </tr>
            </tbody>
          </table>
          <div class="lazy-footer">已加载 {{ lazyGroups.length }} / {{ filteredGroups.length }}</div>
        </div>

        <div v-else class="table-scroll">
          <table class="group-table">
            <thead>
              <tr>
                <th>群头像</th>
                <th>群信息</th>
                <th>群当前人数 / 群最大人数</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in pagedGroups" :key="item.id">
                <td class="avatar-cell">
                  <el-avatar :size="38" :src="getAvatarUrl(item.id)">
                    {{ getAvatarText(item.name) }}
                  </el-avatar>
                </td>
                <td>
                  <div class="group-info">
                    <span class="group-name">{{ item.name }}</span>
                    <span class="group-id">{{ item.id }}</span>
                  </div>
                </td>
                <td>{{ item.now }} / {{ item.max }}</td>
                <td>
                  <el-button size="small" type="primary" text @click="onEditSettings(item)">
                    设置
                  </el-button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <footer class="table-footer">
        <div class="display-count">
          <span>展示数量</span>
          <el-select v-model="displayCount" class="count-select">
            <el-option v-for="count in displayCountOptions" :key="count" :label="`${count}`" :value="count" />
          </el-select>
        </div>

        <el-pagination
          v-if="!isInfiniteMode"
          v-model:current-page="currentPage"
          :page-size="displayCount"
          layout="prev, pager, next"
          :total="filteredGroups.length"
        />

        <span v-else class="mode-tip">展示数量过多，已切换为无限滚动懒加载</span>
      </footer>
    </section>

    <el-drawer
      v-model="settingsDrawerVisible"
      size="460px"
      :before-close="onDrawerBeforeClose"
      @closed="onDrawerClosed"
    >
      <template #header>
        <div v-if="activeGroup" class="drawer-header-wrap">
          <div class="drawer-group-head">
            <el-avatar :size="42" :src="getAvatarUrl(activeGroup.id)">
              {{ getAvatarText(activeGroup.name) }}
            </el-avatar>
            <div class="drawer-group-meta">
              <span class="drawer-group-name">{{ activeGroup.name }}</span>
              <span class="drawer-group-id">{{ activeGroup.id }}</span>
            </div>
          </div>
          <el-button type="primary" :loading="savingSettings" @click="onSaveSettingsClick">
            保存
          </el-button>
        </div>
      </template>

      <div v-loading="loadingSettings" class="drawer-settings-scroll">
        <el-form label-width="110px" class="settings-form">
          <el-form-item label="启用">
            <el-switch
              v-model="settingsForm.enable"
              :active-value="true"
              :inactive-value="false"
            />
          </el-form-item>

          <el-form-item label="回复内容">
            <el-input
              v-model="settingsForm.answer"
              type="textarea"
              :rows="4"
              placeholder="请输入回复内容"
            />
          </el-form-item>

          <el-form-item label="等级">
            <el-input-number v-model="settingsForm.level" :min="0" :max="100" />
          </el-form-item>

          <el-form-item label="通知开关">
            <el-switch
              v-model="settingsForm.notify_enable"
              :active-value="true"
              :inactive-value="false"
            />
          </el-form-item>

          <el-form-item label="通知内容">
            <el-input
              v-model="settingsForm.notify_content"
              type="textarea"
              :rows="6"
              placeholder="请输入通知内容"
            />
          </el-form-item>
        </el-form>
      </div>
    </el-drawer>
  </main>
</template>

<style scoped>
.page {
  padding: 0;
}

/* ── Toolbar ── */
.toolbar {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 20px;
}

.toolbar :deep(.el-button) {
  border-radius: 8px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.toolbar :deep(.el-button:hover) {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.search-box {
  width: 280px;
  margin-left: auto;
}

.search-box :deep(.el-input__wrapper) {
  border-radius: 8px;
  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.08) !important;
  transition: box-shadow 0.2s ease;
}

.search-box :deep(.el-input__wrapper:hover),
.search-box :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #4f6ef7, 0 0 0 3px rgba(79, 110, 247, 0.12) !important;
}

.hidden-input {
  display: none;
}

/* ── Error state ── */
.state {
  min-height: calc(100vh - 160px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.state.error {
  background: #fef2f2;
  border: 1px solid #fecaca;
}

.error-extra {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.error-detail {
  color: #b91c1c;
  font-size: 13px;
}

/* ── Panel ── */
.panel {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.02);
}

.panel-meta {
  display: flex;
  gap: 20px;
  color: #9ca3af;
  font-size: 13px;
  font-weight: 500;
}

.panel-meta span {
  display: flex;
  align-items: center;
  gap: 4px;
}

/* ── Table region ── */
.table-region {
  border: 1px solid #f0f0f0;
  border-radius: 10px;
  overflow: hidden;
  background: #fff;
}

.table-scroll {
  width: 100%;
  height: 100%;
  overflow: auto;
}

.group-table {
  width: 100%;
  border-collapse: collapse;
}

.group-table th,
.group-table td {
  text-align: left;
  padding: 14px 16px;
}

.group-table th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: #fafbfc;
  color: #6b7280;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid #f0f0f0;
}

.group-table td {
  border-bottom: 1px solid #f5f5f5;
  transition: background 0.15s ease;
}

.group-table tbody tr:hover td {
  background: #f8faff;
}

.group-table tbody tr:last-child td {
  border-bottom: none;
}

.avatar-cell {
  width: 80px;
}

.group-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.group-name {
  font-weight: 600;
  color: #1f2937;
  font-size: 14px;
}

.group-id {
  color: #9ca3af;
  font-size: 12px;
  font-family: 'SF Mono', 'Fira Code', monospace;
}

/*人数列样式 */
.group-table td:nth-child(3) {
  color: #6b7280;
  font-size: 13px;
  font-variant-numeric: tabular-nums;
}

/*操作列按钮 */
.group-table td:last-child .el-button {
  border-radius: 6px;
  font-weight: 500;
}

/* ── Table footer ── */
.table-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.display-count {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #9ca3af;
  font-size: 13px;
}

.count-select {
  width: 100px;
}

.lazy-footer,
.mode-tip {
  font-size: 12px;
  color: #9ca3af;
  text-align: center;
  padding: 10px 0;
}

/* ── Drawer ── */
.drawer-header-wrap {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.drawer-group-head {
  display: flex;
  align-items: center;
  gap: 12px;
}

.drawer-group-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.drawer-group-name {
  font-weight: 700;
  font-size: 15px;
  color: #1f2937;
}

.drawer-group-id {
  font-size: 12px;
  color: #9ca3af;
  font-family: 'SF Mono', 'Fira Code', monospace;
}

.drawer-settings-scroll {
  height: calc(100vh - 180px);
  overflow: auto;
  padding: 8px 4px 16px 0;
}

.settings-form :deep(.el-form-item__label) {
  font-weight: 500;
  color: #374151;
}

.settings-form :deep(.el-input__wrapper),
.settings-form :deep(.el-textarea__inner) {
  border-radius: 8px;
}

.settings-form :deep(.el-switch) {
  --el-switch-on-color: #4f6ef7;
}
</style>
