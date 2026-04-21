import { ref, shallowRef, onUnmounted } from 'vue'
import { getAgentWorkerWsBase } from '../api/requestAgentWorker.js'

const HEARTBEAT_INTERVAL_MS = 30 * 1000

function buildWsUrl(sessionId, wsBase) {
  const base = wsBase || getAgentWorkerWsBase()
  if (!base) return ''
  const u = base.replace(/^http:\/\//i, 'ws://').replace(/^https:\/\//i, 'wss://')
  const root = u.endsWith('/') ? u.slice(0, -1) : u
  return `${root}/api/v1/websocket/${encodeURIComponent(sessionId)}`
}

export function useAgentWebSocket() {
  const ws = shallowRef(null)
  const connected = ref(false)
  const lastActivityAt = ref(0)
  let pingTimer = null
  let messageHandler = null
  /** 当前正在连接/已连接的会话，用于避免同一会话被重复 connect（会 disconnect 掉进行中的握手，触发 onerror） */
  let activeSessionId = null

  function markActivity() {
    lastActivityAt.value = Date.now()
  }

  function clearTimers() {
    if (pingTimer) {
      clearInterval(pingTimer)
      pingTimer = null
    }
  }

  function disconnect() {
    activeSessionId = null
    clearTimers()
    const s = ws.value
    if (s) {
      try {
        s.close()
      } catch (_) {}
      ws.value = null
    }
    connected.value = false
  }

  function connect(sessionId, onMessage) {
    if (!sessionId) return
    messageHandler = onMessage
    const existing = ws.value
    if (
      activeSessionId === sessionId &&
      existing &&
      (existing.readyState === WebSocket.OPEN || existing.readyState === WebSocket.CONNECTING)
    ) {
      return
    }
    activeSessionId = sessionId
    clearTimers()
    if (existing) {
      try {
        existing.close()
      } catch (_) {}
      ws.value = null
    }
    connected.value = false

    const url = buildWsUrl(sessionId)
    if (!url) {
      activeSessionId = null
      if (onMessage) onMessage({ message_type: 'connect_error', content: 'WebSocket 地址未配置' })
      return
    }
    const socket = new WebSocket(url)
    ws.value = socket

    socket.onopen = () => {
      connected.value = true
      markActivity()
      startPing()
    }

    socket.onmessage = (event) => {
      markActivity()
      try {
        const data = JSON.parse(event.data)
        const pong = data.type === 'pong' || data.message_type === 'pong'
        if (pong) return
        if (messageHandler) messageHandler(data)
      } catch {
        if (messageHandler) messageHandler({ type: 'message', content: event.data })
      }
    }

    socket.onclose = () => {
      clearTimers()
      connected.value = false
      ws.value = null
      activeSessionId = null
      if (messageHandler) messageHandler({ message_type: 'disconnect', content: '' })
    }

    socket.onerror = () => {
      if (messageHandler) messageHandler({ type: 'error', content: 'WebSocket 连接错误' })
    }
  }

  /** 选中会话持续保活：后台任务可能很久才完成，会无规律间隔返回响应，故只要当前会话处于选中状态就持续 ping；切会话时 disconnect 会清掉定时器 */
  function startPing() {
    clearTimers()
    pingTimer = setInterval(() => {
      const s = ws.value
      if (!s || s.readyState !== WebSocket.OPEN) return
      try {
        s.send(JSON.stringify({ type: 'ping' }))
      } catch (_) {}
    }, HEARTBEAT_INTERVAL_MS)
  }

  /** payload: content (必填), user_id?, agent_type?, llm_provider?, llm_model?, metadata?（字典），可选不传则用会话已有值 */
  function send(payload) {
    markActivity()
    const s = ws.value
    if (!s || s.readyState !== WebSocket.OPEN) return false
    try {
      const body = { content: payload.content ?? '' }
      if (payload.user_id != null && payload.user_id !== '') body.user_id = payload.user_id
      if (payload.agent_type != null && payload.agent_type !== '') body.agent_type = payload.agent_type
      if (payload.llm_provider != null && payload.llm_provider !== '') body.llm_provider = payload.llm_provider
      if (payload.llm_model != null && payload.llm_model !== '') body.llm_model = payload.llm_model
      if (payload.metadata != null && typeof payload.metadata === 'object') body.metadata = payload.metadata
      s.send(JSON.stringify(body))
      return true
    } catch {
      return false
    }
  }

  function ensureConnected(sessionId, onMessage) {
    if (connected.value && ws.value && ws.value.readyState === WebSocket.OPEN) return true
    connect(sessionId, onMessage)
    return false
  }

  onUnmounted(() => {
    disconnect()
  })

  return {
    ws,
    connected,
    lastActivityAt,
    connect,
    disconnect,
    send,
    markActivity,
    ensureConnected,
  }
}
