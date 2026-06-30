export interface GroupItem {
  id: string
  name: string
  max: number
  now: number
}

export interface SettingsLoadData {
  enable: boolean | null
  answer: string | null
  level: number | null
  notify_enable: boolean | null
  notify_content: string | null
}

export interface SettingsSavePayload {
  id: string
  enable: boolean
  answer: string
  level: number
  notify_enable: boolean
  notify_content: string
}

export type ResultCode = 0 | -1

export interface ApiEnvelope<T> {
  c: ResultCode
  d: T
}

/** settings/has 返回码：1 = 该群不存在配置, 2 = 存在配置, -1 = id 错误 */
export type HasSettingsCode = 1 | 2 | -1

export interface HasSettingsEnvelope {
  c: HasSettingsCode
}
/** 导入/导出条目格式 */
export interface SettingsExportItem {
  id: string
  name: string
  settings: SettingsLoadData
}
