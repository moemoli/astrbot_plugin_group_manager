export interface PluginPageContext {
  pluginName: string
  displayName?: string
  pageName: string
  pageTitle?: string
  locale?: string
  i18n?: Record<string, unknown>
  isDark?: boolean
  [key: string]: unknown
}

type QueryValue = string | number | boolean | null | undefined

export type QueryParams =
  | Record<string, QueryValue | QueryValue[]>
  | undefined

export interface SSEMessageEvent {
  raw: string
  parsed: unknown
  eventType: string
  lastEventId?: string
}

export interface SSEHandlers {
  onOpen?: () => void
  onMessage?: (event: SSEMessageEvent) => void
  onError?: (error?: unknown) => void
}

export interface AstrBotPluginPageBridge {
  ready: () => Promise<PluginPageContext>
  getContext?: () => PluginPageContext | null
  apiGet: <T = unknown>(endpoint: string, params?: QueryParams) => Promise<T>
  apiPost: <T = unknown>(endpoint: string, body?: unknown) => Promise<T>
  upload: <T = unknown>(endpoint: string, file: File) => Promise<T>
  download: (
    endpoint: string,
    params?: QueryParams,
    filename?: string,
  ) => Promise<{ filename?: string }>
  subscribeSSE: (
    endpoint: string,
    handlers: SSEHandlers,
    params?: QueryParams,
  ) => Promise<string>
  unsubscribeSSE?: (subscriptionId: string) => Promise<void>
}

let readyPromise: Promise<PluginPageContext> | null = null

function getBridge(): AstrBotPluginPageBridge {
  const bridge = (window as Window & { AstrBotPluginPage?: AstrBotPluginPageBridge })
    .AstrBotPluginPage

  if (!bridge) {
    throw new Error(
      'AstrBotPluginPage bridge is not available. Ensure page script runs after bridge SDK injection.',
    )
  }

  return bridge
}

function normalizeEndpoint(endpoint: string): string {
  const normalized = endpoint.trim().replace(/^\/+/, '')

  if (!normalized) {
    throw new Error('Bridge endpoint cannot be empty.')
  }
  if (normalized.includes('\\')) {
    throw new Error('Bridge endpoint cannot contain backslashes.')
  }
  if (normalized.includes('?') || normalized.includes('#')) {
    throw new Error('Bridge endpoint cannot include query or hash.')
  }
  if (/^[a-z][a-z\d+.-]*:\/\//i.test(normalized)) {
    throw new Error('Bridge endpoint must be a plugin-relative path.')
  }

  const segments = normalized.split('/')
  for (const segment of segments) {
    if (!segment || segment === '.' || segment === '..') {
      throw new Error('Bridge endpoint contains invalid path segments.')
    }
  }

  return normalized
}

export function initBridgeContext(): Promise<PluginPageContext> {
  if (!readyPromise) {
    readyPromise = getBridge().ready()
  }
  return readyPromise
}

export function getBridgeContext(): PluginPageContext | null {
  return getBridge().getContext?.() ?? null
}

export async function requestGet<T = unknown>(
  endpoint: string,
  params?: QueryParams,
): Promise<T> {
  return getBridge().apiGet<T>(normalizeEndpoint(endpoint), params)
}

export async function requestPost<T = unknown>(
  endpoint: string,
  body?: unknown,
): Promise<T> {
  return getBridge().apiPost<T>(normalizeEndpoint(endpoint), body)
}

export async function requestUpload<T = unknown>(
  endpoint: string,
  file: File,
): Promise<T> {
  return getBridge().upload<T>(normalizeEndpoint(endpoint), file)
}

export async function requestDownload(
  endpoint: string,
  params?: QueryParams,
  filename?: string,
): Promise<{ filename?: string }> {
  return getBridge().download(normalizeEndpoint(endpoint), params, filename)
}

export async function requestSubscribeSSE(
  endpoint: string,
  handlers: SSEHandlers,
  params?: QueryParams,
): Promise<string> {
  return getBridge().subscribeSSE(normalizeEndpoint(endpoint), handlers, params)
}

export async function requestUnsubscribeSSE(
  subscriptionId: string,
): Promise<void> {
  const bridge = getBridge()
  if (!bridge.unsubscribeSSE) {
    throw new Error('Current bridge SDK does not support unsubscribeSSE.')
  }
  await bridge.unsubscribeSSE(subscriptionId)
}
