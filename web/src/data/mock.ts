import type {
  ApiEnvelope,
  GroupItem,
  HasSettingsEnvelope,
  SettingsLoadData,
  SettingsSavePayload,
} from './types'

const defaultSettings: SettingsLoadData = {
  enable: true,
  answer: '这是测试环境的默认回复',
  level: 2,
  notify_enable: false,
  notify_content: null,
}

const settingsStore = new Map<string, SettingsLoadData>()

function getStoredSettings(groupId: string): SettingsLoadData {
  const existing = settingsStore.get(groupId)
  if (existing) {
    return { ...existing }
  }

  const initial = { ...defaultSettings }
  settingsStore.set(groupId, initial)
  return { ...initial }
}

export async function getGroupsFromMock(): Promise<ApiEnvelope<GroupItem[]>> {
  return {
    c: 0,
    d: [
      {
        id: '10001',
        name: 'AstrBot 开发群',
        max: 200,
        now: 128,
      },
      {
        id: '10002',
        name: '插件内测群',
        max: 100,
        now: 64,
      },
      {
        id: '10003',
        name: '运营反馈群',
        max: 300,
        now: 212,
      },
    ],
  }
}

export async function getSettingsLoadFromMock(
  groupId: string,
): Promise<ApiEnvelope<SettingsLoadData>> {
  return {
    c: 0,
    d: getStoredSettings(groupId),
  }
}

export async function saveSettingsFromMock(
  payload: SettingsSavePayload,
): Promise<ApiEnvelope<SettingsLoadData>> {
  const groupId = payload.id
  const merged = {
    ...getStoredSettings(groupId),
    enable: payload.enable,
    answer: payload.answer,
    level: payload.level,
    notify_enable: payload.notify_enable,
    notify_content: payload.notify_content,
  }
  settingsStore.set(groupId, merged)

  return {
    c: 0,
    d: { ...merged },
  }
}
export async function hasSettingsFromMock(
  groupId: string,
): Promise<HasSettingsEnvelope> {
  if (!groupId) {
    return { c: -1 }
  }

  return settingsStore.has(groupId) ? { c: 2 } : { c: 1 }
}
