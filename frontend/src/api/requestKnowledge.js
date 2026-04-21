import { GUEST_USER_ID } from './guestIdentity.js'

const BASE_URL = ''

function getUserId() {
  return GUEST_USER_ID
}

function buildUrl(path, params = {}) {
  const target = path.startsWith('http') ? path : `${BASE_URL}${path}`
  const base = (typeof window !== 'undefined' && window.location) ? window.location.origin : 'http://127.0.0.1'
  const url = new URL(target, base)
  const uid = params.user_id ?? getUserId()
  if (uid) url.searchParams.set('user_id', uid)
  Object.keys(params).forEach((k) => {
    if (k === 'user_id') return
    if (params[k] != null && params[k] !== '') url.searchParams.set(k, params[k])
  })
  return url.toString()
}

export async function requestKnowledge(path, options = {}, queryParams = {}) {
  const uid = getUserId()
  // const token = localStorage.getItem('moling_token') || ''
  // if (!token || !uid) {
  //   const err = new Error('请先登录')
  //   err.needLogin = true
  //   throw err
  // }
  const url = buildUrl(path, queryParams)
  const isFormData = options.body instanceof FormData
  const headers = {
    ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
    ...options.headers,
  }
  // if (token) headers['Authorization'] = `Bearer ${token}`
  const method = (options.method || 'GET').toUpperCase()
  const body = options.body !== undefined ? options.body : (method === 'POST' || method === 'PUT' && !isFormData ? '{}' : undefined)
  const res = await fetch(url, { ...options, headers, body })
  const text = await res.text()
  let data = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = text
    }
  }
  if (!res.ok) {
    const err = new Error(data?.detail?.message || data?.message || res.statusText || '请求失败')
    err.status = res.status
    err.data = data
    throw err
  }
  return data
}

export { getUserId as getKnowledgeUserId }
