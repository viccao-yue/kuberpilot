const PREVIEW_MODE_KEY = 'sxdevops_preview_mode'

function isLocalDevHost() {
  if (typeof window === 'undefined') return false
  const host = window.location.hostname
  return host === 'localhost' || host === '127.0.0.1'
}

export function ensurePreviewMode() {
  if (typeof window === 'undefined') return false
  if (!import.meta.env.DEV || !isLocalDevHost()) return false

  const params = new URLSearchParams(window.location.search)
  if (params.get('preview') === '1') {
    localStorage.setItem(PREVIEW_MODE_KEY, '1')
    return true
  }
  if (params.get('preview') === '0') {
    localStorage.removeItem(PREVIEW_MODE_KEY)
    return false
  }

  // Local development connects to the real backend by default. Preview mode
  // remains available through ?preview=1 and can be cleared with ?preview=0.
  return localStorage.getItem(PREVIEW_MODE_KEY) === '1'
}

export function isPreviewMode() {
  if (typeof window === 'undefined') return false
  if (!import.meta.env.DEV || !isLocalDevHost()) return false
  return localStorage.getItem(PREVIEW_MODE_KEY) === '1'
}

export function getPreviewUser() {
  return {
    id: 'preview-user',
    username: 'preview',
    display_name: '本地预览模式',
    is_superuser: true,
    effective_permissions: ['*'],
    roles: [{ name: 'Preview' }],
  }
}

export function getPreviewToken() {
  return 'preview-token'
}
