/** AIAgent Worker 服务（智能助手） */
export const API_AGENT_SERVICE_URL = (() => {
  const v = import.meta.env.VITE_API_AGENT_SERVICE_URL
  if (v !== undefined && v !== '') return v
  if (typeof window !== 'undefined' && window.location) return window.location.origin
  return ''
})()

export const isDevelopment = import.meta.env.DEV
