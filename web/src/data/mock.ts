import type {
  ApiEnvelope,
  GroupItem,
  HasSettingsEnvelope,
  SettingsLoadData,
  SettingsSavePayload,
} from './types'

const defaultSettings: SettingsLoadData = {
  enable: true,
  answer: 'This is the default reply in test environment.',
  level: 2,
  notify_enable: false,
  notify_content: null,
  blacklist_global_enabled: false,
  blacklist_group_enabled: false,
  violation_recall_enabled: false,
  violation_recall_types: [],
  violation_keywords: [],
  violation_action: 'warn',
  violation_mute_duration: 60,
  warning_thresholds: [],
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
        name: 'AstrBot Dev Group',
        max: 200,
        now: 128,
      },
      {
        id: '10002',
        name: 'Plugin Test Group',
        max: 100,
        now: 64,
      },
      {
        id: '10003',
        name: 'Operations Feedback Group',
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
    blacklist_global_enabled: payload.blacklist_global_enabled,
    blacklist_group_enabled: payload.blacklist_group_enabled,
    violation_recall_enabled: payload.violation_recall_enabled,
    violation_recall_types: payload.violation_recall_types,
    violation_keywords: payload.violation_keywords,
    violation_action: payload.violation_action,
    violation_mute_duration: payload.violation_mute_duration,
    warning_thresholds: payload.warning_thresholds,
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
