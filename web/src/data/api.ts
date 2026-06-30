import { requestGet, requestPost } from '@/request'
import type {
  ApiEnvelope,
  GroupItem,
  HasSettingsEnvelope,
  SettingsLoadData,
  SettingsSavePayload,
} from './types'

export async function getGroupsFromApi(): Promise<ApiEnvelope<GroupItem[]>> {
  return requestGet<ApiEnvelope<GroupItem[]>>('groups')
}

export async function getSettingsLoadFromApi(
  groupId: string,
): Promise<ApiEnvelope<SettingsLoadData>> {
  return requestGet<ApiEnvelope<SettingsLoadData>>('settings/load', { id: groupId })
}

export async function saveSettingsFromApi(
  payload: SettingsSavePayload,
): Promise<ApiEnvelope<SettingsLoadData>> {
  return requestPost<ApiEnvelope<SettingsLoadData>>('settings/save', payload)
}
export async function hasSettingsFromApi(
  groupId: string,
): Promise<HasSettingsEnvelope> {
  return requestGet<HasSettingsEnvelope>('settings/has', { id: groupId })
}
