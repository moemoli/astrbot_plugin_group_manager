import {
  getGroupsFromApi,
  getSettingsLoadFromApi,
  saveSettingsFromApi,
  hasSettingsFromApi,
} from './api'
import {
  getGroupsFromMock,
  getSettingsLoadFromMock,
  saveSettingsFromMock,
  hasSettingsFromMock,
} from './mock'
import type {
  ApiEnvelope,
  GroupItem,
  HasSettingsEnvelope,
  SettingsLoadData,
  SettingsSavePayload,
} from './types'

function isTestEnvironment(): boolean {
  const appEnv = import.meta.env.VITE_APP_ENV?.toLowerCase()
  return import.meta.env.MODE === 'development' || import.meta.env.MODE === 'test' || appEnv === 'test'
}

export const dataSourceName = isTestEnvironment() ? 'mock' : 'request'

export async function getGroups(): Promise<ApiEnvelope<GroupItem[]>> {
  if (isTestEnvironment()) {
    return getGroupsFromMock()
  }

  return getGroupsFromApi()
}

export async function getSettingsLoad(
  groupId: string,
): Promise<ApiEnvelope<SettingsLoadData>> {
  if (isTestEnvironment()) {
    return getSettingsLoadFromMock(groupId)
  }

  return getSettingsLoadFromApi(groupId)
}

export async function saveSettings(
  payload: SettingsSavePayload,
): Promise<ApiEnvelope<SettingsLoadData>> {
  if (isTestEnvironment()) {
    return saveSettingsFromMock(payload)
  }

  return saveSettingsFromApi(payload)
}

export async function hasSettings(
  groupId: string,
): Promise<HasSettingsEnvelope> {
  if (isTestEnvironment()) {
    return hasSettingsFromMock(groupId)
  }

  return hasSettingsFromApi(groupId)
}