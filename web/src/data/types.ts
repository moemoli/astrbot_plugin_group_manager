export interface GroupItem {
  id: string
  name: string
  max: number
  now: number
}

export interface WarningThreshold {
  count: number
  action: string
  mute_duration: number
}

export interface SettingsLoadData {
  enable: boolean | null
  answer: string | null
  level: number | null
  notify_enable: boolean | null
  notify_content: string | null
  blacklist_global_enabled: boolean | null
  blacklist_group_enabled: boolean | null
  violation_recall_enabled: boolean | null
  violation_recall_types: string[] | null
  violation_keywords: string[] | null
  violation_action: string | null
  violation_mute_duration: number | null
  warning_thresholds: WarningThreshold[] | null
}

export interface SettingsSavePayload {
  id: string
  enable: boolean
  answer: string
  level: number
  notify_enable: boolean
  notify_content: string
  blacklist_global_enabled: boolean
  blacklist_group_enabled: boolean
  violation_recall_enabled: boolean
  violation_recall_types: string[]
  violation_keywords: string[]
  violation_action: string
  violation_mute_duration: number
  warning_thresholds: WarningThreshold[]
}

export type ResultCode = 0 | -1

export interface ApiEnvelope<T> {
  c: ResultCode
  d: T
}

/** settings/has return codes: 1 = no config, 2 = has config, -1 = id error */
export type HasSettingsCode = 1 | 2 | -1

export interface HasSettingsEnvelope {
  c: HasSettingsCode
}

/** Import/export item format */
export interface SettingsExportItem {
  id: string
  name: string
  settings: SettingsLoadData
}
