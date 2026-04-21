<template>
  <div class="qa-content">
    <div class="qa-panel-left">
      <div class="qa-panel-title">历史记录</div>
      <button
        type="button"
        class="qa-new-chat-btn"
        :disabled="creatingSession"
        @click="startNewChat"
      >
        {{ creatingSession ? '创建中…' : '新对话' }}
      </button>
      <div v-if="createSessionError" class="qa-new-chat-error">{{ createSessionError }}</div>
      <ul class="qa-history-list">
        <li
          v-for="item in historyList"
          :key="item.session_id"
          class="qa-history-item"
          :class="{ active: currentSessionId === item.session_id }"
          @click="loadHistory(item)"
        >
          <div class="qa-history-content">
            <span class="qa-history-title">{{ sessionTitle(item) }}</span>
            <div class="qa-history-meta">
              <span v-if="sessionAgentType(item)" class="qa-history-agent-type">{{ sessionAgentType(item) }}</span>
              <span v-if="sessionTime(item)" class="qa-history-time">{{ sessionTime(item) }}</span>
            </div>
          </div>
          <button
            type="button"
            class="qa-history-delete-btn"
            aria-label="删除会话"
            :disabled="deletingSessionId === item.session_id"
            @click.stop="onDeleteSession(item)"
          >
            <svg class="qa-history-delete-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2M10 11v6M14 11v6"/>
            </svg>
          </button>
        </li>
        <li v-if="!historyList.length && !historyLoading" class="qa-history-empty">暂无历史</li>
        <li v-if="historyLoading" class="qa-history-empty">加载中…</li>
      </ul>
    </div>
    <div class="qa-panel-right">
      <div class="qa-chat-top">
        <div class="qa-model-select-wrap" ref="modelSelectWrapRef">
          <label class="qa-label">选择模型</label>
          <button
            type="button"
            class="qa-model-trigger"
            :disabled="modelsLoading"
            @click="showModelDropdown = !showModelDropdown; showAgentDropdown = false"
          >
            <span class="qa-model-trigger-text">{{ selectedModelDisplay }}</span>
            <span class="qa-model-trigger-arrow" :class="{ open: showModelDropdown }">▼</span>
          </button>
          <div v-if="showModelDropdown" class="qa-model-dropdown-mask" @click="showModelDropdown = false" />
          <div v-if="showModelDropdown" class="qa-model-dropdown">
            <div
              v-for="group in chatModelGroups"
              :key="group.provider"
              class="qa-model-group"
            >
              <div class="qa-model-group-title">{{ group.provider }}</div>
              <button
                v-for="opt in group.models"
                :key="opt.value"
                type="button"
                class="qa-model-option"
                :class="{ active: selectedModelValue === opt.value }"
                @click="selectModel(opt)"
              >
                {{ opt.display }}
              </button>
            </div>
          </div>
        </div>
        <div class="qa-model-select-wrap agent-select-wrap" ref="agentSelectWrapRef">
          <label class="qa-label">Agent 类型</label>
          <button
            type="button"
            class="qa-model-trigger"
            :disabled="agentTypesLoading"
            @click="showAgentDropdown = !showAgentDropdown; showModelDropdown = false"
          >
            <span class="qa-model-trigger-text">{{ selectedAgentDisplay }}</span>
            <span class="qa-model-trigger-arrow" :class="{ open: showAgentDropdown }">▼</span>
          </button>
          <div v-if="showAgentDropdown" class="qa-model-dropdown-mask" @click="showAgentDropdown = false" />
          <div v-if="showAgentDropdown" class="qa-model-dropdown">
            <button
              v-for="opt in agentTypeOptions"
              :key="opt.value"
              type="button"
              class="qa-model-option"
              :class="{ active: selectedAgentType === opt.value }"
              :title="opt.description"
              @click="selectAgentType(opt)"
            >
              {{ opt.label }}
            </button>
          </div>
        </div>
      </div>
      <div class="qa-chat-body">
        <div class="qa-chat-messages" ref="messagesRef" @scroll="onMessagesScroll" @mousedown="markActivity">
          <div v-if="!messages.length" class="qa-chat-empty">输入问题开始对话</div>
          <div
            v-for="(msg, idx) in messages"
            :key="idx"
            class="qa-msg"
            :class="msg.role"
          >
            <div class="qa-msg-avatar">
              <img v-if="msg.role === 'user' && userAvatarUrl" :src="userAvatarUrl" alt="我" class="qa-avatar-img" />
              <span v-else-if="msg.role === 'user'" class="qa-avatar-letter">{{ userAvatarLetter }}</span>
              <img v-else src="/pando-icon.png" alt="Pando" class="qa-moling-icon-img" />
            </div>
            <div class="qa-msg-bubble">
              <span class="qa-msg-role">{{ msg.role === 'user' ? '我' : 'Pando' }}</span>
              <span v-if="msg.createTime" class="qa-msg-time">{{ formatMessageTime(msg.createTime) }}</span>
              <div class="qa-msg-content qa-markdown" v-html="renderMarkdown(msg.content)"></div>
            </div>
          </div>
          <div v-if="sending" class="qa-msg assistant">
            <div class="qa-msg-avatar">
              <img src="/pando-icon.png" alt="Pando" class="qa-moling-icon-img" />
            </div>
            <div class="qa-msg-bubble">
              <span class="qa-msg-role">Pando</span>
              <div class="qa-msg-content qa-markdown" v-html="renderMarkdown(streamBuffer || '…')"></div>
            </div>
          </div>
        </div>
        <div class="qa-chat-input-wrap" ref="inputWrapRef">
          <div
            class="qa-input-resize-handle"
            title="拖动拉高输入框"
            @mousedown.prevent="startResizeInput"
          >
            <span class="qa-input-resize-handle-bar" />
          </div>
          <div
            class="qa-input-box"
            :class="{ disabled: !inputAllowed, 'qa-input-box-resized': inputAreaHeight != null }"
            :style="inputAreaHeight != null ? { height: inputAreaHeight + 'px' } : {}"
            ref="inputBoxRef"
          >
            <textarea
              v-model="inputText"
              class="qa-input"
              placeholder="输入问题…"
              rows="2"
              :readonly="!inputAllowed"
              @focus="onInputFocus"
              @keydown.enter.exact.prevent="inputAllowed && send()"
            />
            <div class="qa-input-footer">
              <button
                type="button"
                class="qa-send-btn"
                :disabled="!inputAllowed || sending || !inputText.trim() || !selectedAgentType || !selectedModelValue"
                @click="send"
              >
                发送
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { marked } from 'marked'
import { useAuth } from '../composables/useAuth.js'
import { listSessions, getSessionInfo, getSessionMessages, createSession, deleteSession, getChatModels, getAgentTypes, getUserId } from '../api/agentWorker.js'
import { useAgentWebSocket } from '../composables/useAgentWebSocket.js'

const { user, userDisplayName, avatarUrl, loadAvatar, avatarObjectUrls } = useAuth()
const {
  connected: wsConnected,
  connect: wsConnect,
  disconnect: wsDisconnect,
  send: wsSend,
  markActivity,
} = useAgentWebSocket()

marked.setOptions({ breaks: true })
function renderMarkdown(text) {
  const s = text != null ? String(text) : ''
  if (!s.trim()) return ''
  try {
    return marked.parse(s)
  } catch {
    return s.replace(/</g, '&lt;').replace(/>/g, '&gt;')
  }
}

const agentTypeOptions = ref([])
const agentTypesLoading = ref(false)
const messages = ref([])
const inputText = ref('')
const sending = ref(false)
const streamBuffer = ref('')
const messagesRef = ref(null)
const historyList = ref([])
const historyLoading = ref(false)
const currentSessionId = ref(null)
const chatModelOptions = ref([])
const modelsLoading = ref(false)
const selectedModelValue = ref('')
const defaultModelValue = ref(null)
const selectedAgentType = ref('')
const showModelDropdown = ref(false)
const showAgentDropdown = ref(false)
const modelSelectWrapRef = ref(null)
const agentSelectWrapRef = ref(null)
const creatingSession = ref(false)
const createSessionError = ref('')
const deletingSessionId = ref(null)
const inputWrapRef = ref(null)
const inputBoxRef = ref(null)
const inputAreaHeight = ref(null)
const INPUT_AREA_MIN_H = 120
const INPUT_AREA_MAX_H = 480
let streamDoneTimer = null

const chatModelGroups = computed(() => {
  const opts = chatModelOptions.value
  if (!opts.length) return []
  const map = new Map()
  for (const opt of opts) {
    const p = opt.provider ?? ''
    if (!map.has(p)) map.set(p, [])
    map.get(p).push(opt)
  }
  return Array.from(map.entries()).map(([provider, models]) => ({
    provider: provider || '其他',
    models,
  }))
})

const selectedModelDisplay = computed(() => {
  if (!selectedModelValue.value) return '请选择模型'
  const opt = chatModelOptions.value.find((o) => o.value === selectedModelValue.value)
  return opt ? opt.display : selectedModelValue.value
})

const selectedAgentDisplay = computed(() => {
  const opts = agentTypeOptions.value
  const opt = opts.find((o) => o.value === selectedAgentType.value)
  if (opt) return opt.label
  if (selectedAgentType.value) return selectedAgentType.value
  return agentTypesLoading.value ? '加载中…' : '请选择 Agent'
})

const userAvatarUrl = computed(() => {
  const u = user.value
  const uid = u?.id ?? u?.user_id
  if (!uid) return ''
  loadAvatar(uid)
  return avatarObjectUrls.value[uid] ?? avatarUrl(uid) ?? ''
})

const userAvatarLetter = computed(() => {
  const name = userDisplayName.value
  return (typeof name === 'string' && name.trim())
    ? String(name).trim().charAt(0).toUpperCase()
    : '我'
})

const selectedModel = computed(() => {
  if (!selectedModelValue.value) return { provider: null, model: null }
  const parts = selectedModelValue.value.split('|')
  return {
    provider: parts[0] || null,
    model: parts[1] || null,
  }
})

const inputAllowed = computed(() => true)

function selectModel(opt) {
  selectedModelValue.value = opt.value
  showModelDropdown.value = false
}

function selectAgentType(opt) {
  selectedAgentType.value = opt.value
  showAgentDropdown.value = false
}

function startResizeInput(e) {
  const box = inputBoxRef.value
  if (!box) return
  const startY = e.clientY
  const rect = box.getBoundingClientRect()
  const startH = inputAreaHeight.value != null ? inputAreaHeight.value : rect.height
  function onMove(moveE) {
    const delta = startY - moveE.clientY
    const newH = Math.round(Math.min(INPUT_AREA_MAX_H, Math.max(INPUT_AREA_MIN_H, startH + delta)))
    inputAreaHeight.value = newH
  }
  function onUp() {
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
    document.body.style.userSelect = ''
    document.body.style.cursor = ''
  }
  document.body.style.userSelect = 'none'
  document.body.style.cursor = 'ns-resize'
  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
}

function flattenChatModelsFromBackend(res) {
  if (Array.isArray(res)) return res
  if (!res || typeof res !== 'object') return []
  const supported = res.supported ?? res
  if (!supported || typeof supported !== 'object') return []
  const list = []
  for (const [provider, providerInfo] of Object.entries(supported)) {
    const models = providerInfo?.models ?? providerInfo?.instances ?? {}
    for (const modelName of Object.keys(models)) {
      list.push({
        provider,
        model: modelName,
        display: `${provider}/${modelName}`,
        value: `${provider}|${modelName}`,
      })
    }
  }
  return list
}

function normalizeChatModels(list) {
  if (!Array.isArray(list)) return []
  return list.map((m) => {
    if (typeof m === 'string') {
      const p = m.split('/')
      const provider = p.length >= 2 ? p[0] : ''
      const model = p.length >= 2 ? p.slice(1).join('/') : m
      return { provider, model, display: m, value: provider ? `${provider}|${model}` : model }
    }
    const provider = m.provider ?? m.provider_name ?? ''
    const model = m.model ?? m.model_name ?? ''
    const display = m.display ?? (provider ? `${provider}/${model}` : model)
    const value = m.value ?? (provider ? `${provider}|${model}` : model)
    return { provider, model, display, value }
  })
}

async function loadChatModels() {
  modelsLoading.value = true
  try {
    const res = await getChatModels()
    const flat = flattenChatModelsFromBackend(res)
    const opts = flat.length ? flat : normalizeChatModels(Array.isArray(res) ? res : (res?.models ?? res?.items ?? []))
    chatModelOptions.value = opts
    const def = res?.default
    if (def && def.provider != null && def.model != null) {
      defaultModelValue.value = `${def.provider}|${def.model}`
    } else {
      defaultModelValue.value = null
    }
    if (opts.length && !selectedModelValue.value) {
      const defaultVal = defaultModelValue.value
      selectedModelValue.value = (defaultVal && opts.some((o) => o.value === defaultVal)) ? defaultVal : opts[0].value
    }
  } catch {
    chatModelOptions.value = []
    defaultModelValue.value = null
  } finally {
    modelsLoading.value = false
  }
}

async function loadAgentTypes() {
  agentTypesLoading.value = true
  try {
    const items = await getAgentTypes()
    const opts = Array.isArray(items)
      ? items.map((item) => ({
          value: item.agent_type ?? '',
          label: item.name ?? item.agent_type ?? '',
          description: item.description ?? '',
        }))
      : []
    agentTypeOptions.value = opts
    if (opts.length && !selectedAgentType.value) {
      selectedAgentType.value = opts[0].value
    }
  } catch {
    agentTypeOptions.value = []
  } finally {
    agentTypesLoading.value = false
  }
}

function formatSessionTime(isoOrStr) {
  if (!isoOrStr) return ''
  const d = new Date(isoOrStr)
  if (Number.isNaN(d.getTime())) return ''
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${y}-${m}-${day} ${h}:${min}`
}

function formatMessageTime(createTime) {
  if (createTime == null) return ''
  const t = typeof createTime === 'number' ? (createTime < 1e12 ? createTime * 1000 : createTime) : createTime
  const d = new Date(t)
  if (Number.isNaN(d.getTime())) return ''
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  const sec = String(d.getSeconds()).padStart(2, '0')
  return `${y}-${m}-${day} ${h}:${min}:${sec}`
}

function sessionTitle(item) {
  return item.description?.trim() || '未命名对话'
}

function sessionTime(item) {
  return formatSessionTime(item.last_updated ?? item.created_at)
}

function sessionAgentType(item) {
  const raw = (item?.agent_type ?? item?.session_type ?? '').trim() || null
  if (!raw) return null
  const opt = agentTypeOptions.value.find((o) => o.value === raw)
  return opt ? opt.label : raw
}

function sessionSortKey(s) {
  const t = s.last_updated ?? s.created_at ?? ''
  return new Date(t).getTime() || 0
}

async function loadSessionList() {
  historyLoading.value = true
  try {
    const list = await listSessions()
    const items = Array.isArray(list) ? list : []
    historyList.value = [...items].sort((a, b) => sessionSortKey(b) - sessionSortKey(a))
  } catch {
    historyList.value = []
  } finally {
    historyLoading.value = false
  }
}

async function onDeleteSession(item) {
  const sid = item?.session_id
  if (!sid) return
  deletingSessionId.value = sid
  try {
    await deleteSession(sid)
    if (currentSessionId.value === sid) {
      wsDisconnect()
      currentSessionId.value = null
      messages.value = []
    }
    await loadSessionList()
  } catch {
    createSessionError.value = '删除会话失败'
  } finally {
    deletingSessionId.value = null
  }
}

async function startNewChat() {
  createSessionError.value = ''
  creatingSession.value = true
  wsDisconnect()
  const agentType = selectedAgentType.value ?? ''
  const opts = chatModelOptions.value
  const useDefault = defaultModelValue.value && opts.some((o) => o.value === defaultModelValue.value)
  if (useDefault) selectedModelValue.value = defaultModelValue.value
  const provider = selectedModel.value?.provider ?? ''
  const model = selectedModel.value?.model ?? null
  try {
    const res = await createSession({
      agent_type: agentType || null,
      llm_provider: provider || null,
      llm_model: model,
    })
    const sid = res?.session_id
    if (sid) {
      currentSessionId.value = sid
      messages.value = []
      await loadSessionList()
      nextTick(() => connectWs())
    } else {
      currentSessionId.value = null
      messages.value = []
      loadSessionList()
    }
  } catch (e) {
    createSessionError.value = e?.message || '创建会话失败'
    currentSessionId.value = null
    messages.value = []
    loadSessionList()
  } finally {
    creatingSession.value = false
  }
}

async function loadHistory(item) {
  if (!item?.session_id) return
  wsDisconnect()
  currentSessionId.value = item.session_id
  try {
    const [msgs, info] = await Promise.all([
      getSessionMessages(item.session_id),
      getSessionInfo(item.session_id),
    ])
    messages.value = (msgs || []).map((m) => ({
      role: m.role || 'user',
      content: m.content ?? '',
      createTime: m.create_time ?? m.created_at ?? null,
    }))
    if (info?.agent_type != null && String(info.agent_type).trim()) {
      const t = String(info.agent_type).trim()
      if (agentTypeOptions.value.some((o) => o.value === t)) selectedAgentType.value = t
    }
    if (info?.llm_provider != null || info?.llm_model != null) {
      const p = (info.llm_provider ?? '').trim()
      const m = (info.llm_model ?? '').trim()
      const val = p && m ? `${p}|${m}` : p || m || ''
      const opt = chatModelOptions.value.find((o) => o.provider === p && o.model === m)
      selectedModelValue.value = opt ? opt.value : val
    }
  } catch {
    messages.value = []
  } finally {
    await nextTick()
    scrollToBottom()
    connectWs()
  }
}

function handleWsMessage(data) {
  const rawType = data.message_type ?? data.type ?? ''
  const type = String(rawType).toLowerCase()
  const content = data.content ?? data.text ?? ''
  if (type === 'connect_success') return
  if (type === 'response') {
    // 一条请求可能对应后端多条 RESPONSE，每条立即追加为一条助手消息（与 MoLing-Chat 一致）
    if (streamDoneTimer) {
      clearTimeout(streamDoneTimer)
      streamDoneTimer = null
    }
    const text = (content || '').trim() || '无回复'
    messages.value.push({ role: 'assistant', content: text, createTime: Date.now() })
    sending.value = false
    streamBuffer.value = ''
    loadSessionList()
    scrollToBottom()
    return
  }
  if (type === 'error') {
    messages.value.push({ role: 'assistant', content: content || '请求出错', createTime: Date.now() })
    sending.value = false
    streamBuffer.value = ''
    loadSessionList()
    scrollToBottom()
    return
  }
  if (type === 'disconnect' || type === 'disconnected') {
    if (sending.value && (streamBuffer.value || '').length > 0) {
      messages.value.push({ role: 'assistant', content: (streamBuffer.value || '').trim() || '连接已断开', createTime: Date.now() })
      streamBuffer.value = ''
    }
    sending.value = false
    loadSessionList()
    return
  }
  if (content !== '' && sending.value) {
    // 未识别的类型但带 content 时也按单条助手消息展示
    if (streamDoneTimer) {
      clearTimeout(streamDoneTimer)
      streamDoneTimer = null
    }
    const text = (content || '').trim() || '无回复'
    messages.value.push({ role: 'assistant', content: text, createTime: Date.now() })
    sending.value = false
    streamBuffer.value = ''
    loadSessionList()
    scrollToBottom()
  }
}

function connectWs() {
  const sid = currentSessionId.value
  if (!sid) return
  wsConnect(sid, handleWsMessage)
}

function onInputFocus() {
  markActivity()
  if (!wsConnected.value && currentSessionId.value) connectWs()
}

function onMessagesScroll() {
  markActivity()
}

async function send() {
  const text = inputText.value.trim()
  if (!text || sending.value) return
  if (!selectedAgentType.value) {
    messages.value.push({ role: 'assistant', content: '请先选择 Agent 类型', createTime: Date.now() })
    return
  }
  if (!selectedModelValue.value) {
    messages.value.push({ role: 'assistant', content: '请先选择模型', createTime: Date.now() })
    return
  }
  markActivity()
  if (!currentSessionId.value) {
    await startNewChat()
    if (!currentSessionId.value) return
    await nextTick()
  }
  const sid = currentSessionId.value
  const payload = {
    content: text,
    user_id: getUserId(),
    agent_type: selectedAgentType.value || undefined,
    llm_provider: selectedModel.value?.provider ?? undefined,
    llm_model: selectedModel.value?.model ?? undefined,
  }

  async function waitConnected(ms) {
    if (wsConnected.value) return true
    connectWs()
    return new Promise((resolve) => {
      const stop = watch(wsConnected, (v) => {
        if (v) { stop(); resolve(true) }
      })
      setTimeout(() => { stop(); resolve(false) }, ms)
    })
  }

  if (!wsConnected.value) {
    const connected = await waitConnected(8000)
    if (!connected) {
      const retryConnected = await waitConnected(5000)
      if (!retryConnected) {
        messages.value.push({ role: 'assistant', content: '连接超时，请重试', createTime: Date.now() })
        sending.value = false
        streamBuffer.value = ''
        return
      }
    }
  }

  messages.value.push({ role: 'user', content: text, createTime: Date.now() })
  inputText.value = ''
  sending.value = true
  streamBuffer.value = ''
  scrollToBottom()

  let ok = wsSend(payload)
  if (!ok) {
    const reconnected = await waitConnected(6000)
    if (reconnected) ok = wsSend(payload)
  }
  if (!ok) {
    messages.value.push({ role: 'assistant', content: '发送失败，请检查连接后重试', createTime: Date.now() })
    sending.value = false
    streamBuffer.value = ''
    loadSessionList()
    return
  }
  loadSessionList()
  scrollToBottom()
}

function scrollToBottom() {
  setTimeout(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  }, 50)
}

watch(messages, () => {
  nextTick(() => scrollToBottom())
}, { deep: true })

onMounted(async () => {
  loadSessionList()
  await Promise.all([
    loadChatModels(),
    loadAgentTypes(),
  ])
  if (chatModelOptions.value.length && !selectedModelValue.value) {
    const defaultVal = defaultModelValue.value
    const opts = chatModelOptions.value
    selectedModelValue.value = (defaultVal && opts.some((o) => o.value === defaultVal)) ? defaultVal : opts[0].value
  }
  if (agentTypeOptions.value.length && !selectedAgentType.value) {
    selectedAgentType.value = agentTypeOptions.value[0].value
  }
})

onUnmounted(() => {
  wsDisconnect()
})
</script>

<style scoped>
.qa-content {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 12px;
  overflow: hidden;
}
.qa-panel-left {
  flex: 0 0 320px;
  min-width: 0;
  min-height: 0;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.qa-panel-title {
  flex-shrink: 0;
  min-height: 48px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  font-size: 14px;
  font-weight: 500;
  color: #202124;
  border-bottom: 1px solid #e8eaed;
}
.qa-new-chat-btn {
  margin: 12px 16px;
  padding: 8px 12px;
  font-size: 13px;
  color: #1a73e8;
  background: #e8f0fe;
  border: none;
  border-radius: 8px;
  cursor: pointer;
}
.qa-new-chat-btn:hover:not(:disabled) {
  background: #d2e3fc;
}
.qa-new-chat-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
.qa-new-chat-error {
  margin: 8px 16px 0;
  font-size: 12px;
  color: #d93025;
}
.qa-history-list {
  list-style: none;
  margin: 0;
  padding: 8px 0;
  overflow: auto;
  flex: 1;
}
.qa-history-item {
  padding: 10px 16px;
  font-size: 13px;
  color: #202124;
  cursor: pointer;
  border-left: 3px solid transparent;
  display: flex;
  align-items: flex-start;
  gap: 8px;
}
.qa-history-item:hover {
  background: #e8eaed;
}
.qa-history-item.active {
  background: #e8f0fe;
  color: #1a73e8;
  border-left-color: #1a73e8;
}
.qa-history-item .qa-history-content {
  flex: 1;
  min-width: 0;
}
.qa-history-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.qa-history-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: block;
  line-height: 1.4;
}
.qa-history-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-height: 20px;
  line-height: 1.2;
}
.qa-history-agent-type {
  font-size: 11px;
  color: #5f6368;
  padding: 0 6px;
  border-radius: 4px;
  background: #e8eaed;
  flex-shrink: 0;
  max-width: fit-content;
}
.qa-history-item.active .qa-history-agent-type {
  background: #dadce0;
  color: #202124;
}
.qa-history-time {
  font-size: 11px;
  color: #9aa0a6;
  flex-shrink: 0;
}
.qa-history-item.active .qa-history-time {
  color: #5f6368;
}
.qa-history-delete-btn {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  padding: 0;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: #5f6368;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0.7;
}
.qa-history-delete-btn:hover:not(:disabled) {
  background: rgba(0, 0, 0, 0.08);
  color: #d93025;
  opacity: 1;
}
.qa-history-delete-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
.qa-history-delete-icon {
  display: block;
}
.qa-history-empty {
  padding: 16px;
  font-size: 13px;
  color: #9aa0a6;
  list-style: none;
}
.qa-panel-right {
  flex: 1;
  min-width: 0;
  min-height: 0;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.qa-chat-top {
  flex-shrink: 0;
  min-height: 48px;
  padding: 0 16px;
  border-bottom: 1px solid #e8eaed;
  display: flex;
  align-items: center;
  gap: 16px;
}
.qa-model-select-wrap {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
}
.agent-select-wrap {
  min-width: 140px;
}
.qa-label {
  font-size: 13px;
  color: #5f6368;
  font-weight: 500;
}
.qa-model-trigger {
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-width: 280px;
  padding: 10px 14px;
  font-size: 14px;
  color: #202124;
  background: #fff;
  border: 1px solid #dadce0;
  border-radius: 8px;
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.qa-model-trigger:hover:not(:disabled) {
  border-color: #1a73e8;
  box-shadow: 0 0 0 1px rgba(26, 115, 232, 0.15);
}
.qa-model-trigger:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
.qa-model-trigger-text {
  flex: 1;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.qa-model-trigger-arrow {
  flex-shrink: 0;
  font-size: 10px;
  color: #5f6368;
  transition: transform 0.2s;
}
.qa-model-trigger-arrow.open {
  transform: rotate(180deg);
}
.qa-model-dropdown-mask {
  position: fixed;
  inset: 0;
  z-index: 100;
}
.qa-model-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  z-index: 101;
  min-width: 360px;
  max-height: 320px;
  overflow: auto;
  background: #fff;
  border: 1px solid #e8eaed;
  border-radius: 10px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
  padding: 4px 0;
}
.qa-model-group {
  padding: 0 0 2px;
}
.qa-model-group:not(:first-child) {
  margin-top: 4px;
  padding-top: 4px;
  border-top: 1px solid #f1f3f4;
}
.qa-model-group-title {
  padding: 3px 14px 4px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #5f6368;
}
.qa-model-option {
  display: block;
  width: 100%;
  padding: 5px 14px;
  font-size: 14px;
  color: #202124;
  text-align: left;
  background: transparent;
  border: none;
  cursor: pointer;
  transition: background 0.15s;
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.qa-model-option:hover {
  background: #f1f3f4;
}
.qa-model-option.active {
  background: #e8f0fe;
  color: #1a73e8;
  font-weight: 500;
}
.qa-chat-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.qa-chat-messages {
  flex: 1 1 0;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 16px;
  background: #fff;
}
.qa-chat-empty {
  color: #9aa0a6;
  font-size: 14px;
  text-align: center;
  padding: 24px;
}
.qa-msg {
  margin-bottom: 16px;
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  gap: 10px;
}
.qa-msg.user {
  flex-direction: row-reverse;
}
.qa-msg-avatar {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #e8eaed;
}
.qa-msg.user .qa-msg-avatar {
  background: #e8f0fe;
}
.qa-avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.qa-avatar-letter {
  font-size: 14px;
  font-weight: 600;
  color: #5f6368;
}
.qa-msg.user .qa-avatar-letter {
  color: #1a73e8;
}
.qa-moling-icon-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.qa-msg-bubble {
  max-width: 78%;
  display: inline-flex;
  flex-direction: column;
  align-items: flex-start;
}
.qa-msg.user .qa-msg-bubble {
  align-items: flex-end;
}
.qa-msg-time {
  font-size: 12px;
  color: #9aa0a6;
  margin-bottom: 2px;
  display: block;
}
.qa-msg-role {
  font-size: 12px;
  color: #5f6368;
  margin-bottom: 4px;
  display: block;
}
.qa-msg-content {
  font-size: 14px;
  color: #202124;
  white-space: pre-wrap;
  word-break: break-word;
  padding: 10px 14px;
  border-radius: 12px;
  line-height: 1.4;
  background: rgba(0, 0, 0, 0.06);
  border: 1px solid rgba(0, 0, 0, 0.08);
}
.qa-msg.assistant .qa-msg-content {
  background: rgba(0, 0, 0, 0.06);
  border-radius: 4px 12px 12px 12px;
}
.qa-msg.user .qa-msg-content {
  background: rgba(0, 0, 0, 0.05);
  color: #1a1a1a;
  border-radius: 12px 12px 4px 12px;
  border-color: rgba(0, 0, 0, 0.08);
}
/* 与 .qa-msg-content 的 pre-wrap 叠加会让块级 MD 行距异常偏大，改为常规排版 */
.qa-markdown {
  white-space: normal;
  line-height: 1.38;
}
.qa-markdown :deep(p) {
  margin: 0 !important;
  line-height: 1.38;
}
.qa-markdown :deep(p + p) {
  margin-top: 0.35em !important;
}
.qa-markdown :deep(* + p),
.qa-markdown :deep(* + ul),
.qa-markdown :deep(* + ol),
.qa-markdown :deep(* + h1),
.qa-markdown :deep(* + h2),
.qa-markdown :deep(* + h3),
.qa-markdown :deep(* + h4),
.qa-markdown :deep(* + h5),
.qa-markdown :deep(* + h6) {
  margin-top: 0.35em !important;
}
.qa-markdown :deep(p:first-child) {
  margin-top: 0 !important;
}
.qa-markdown :deep(h1),
.qa-markdown :deep(h2),
.qa-markdown :deep(h3),
.qa-markdown :deep(h4),
.qa-markdown :deep(h5),
.qa-markdown :deep(h6) {
  margin: 0.35em 0 0.2em !important;
  font-weight: 600;
  line-height: 1.25;
}
.qa-markdown :deep(h1):first-child,
.qa-markdown :deep(h2):first-child,
.qa-markdown :deep(h3):first-child {
  margin-top: 0 !important;
}
.qa-markdown :deep(h1) { font-size: 1.3em; }
.qa-markdown :deep(h2) { font-size: 1.2em; }
.qa-markdown :deep(h3) { font-size: 1.1em; }
.qa-markdown :deep(ul),
.qa-markdown :deep(ol) {
  margin: 0.25em 0 !important;
  padding-left: 1.35em;
}
.qa-markdown :deep(li) {
  margin: 0 !important;
  padding: 0;
  line-height: 1.38;
}
/* marked 常在 li 内包一层 p，段落默认 margin 会撑大行距 */
.qa-markdown :deep(li > p) {
  margin: 0 !important;
}
.qa-markdown :deep(li + li) {
  margin-top: 0.2em !important;
}
.qa-markdown :deep(blockquote) {
  margin: 0.15em 0 !important;
  padding: 0.2em 0 0.2em 1em;
  border-left: 3px solid #dadce0;
  color: #5f6368;
}
.qa-markdown :deep(pre) {
  margin: 0.15em 0 !important;
  padding: 10px;
  background: rgba(0, 0, 0, 0.1);
  border-radius: 8px;
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.4;
}
.qa-markdown :deep(code) {
  font-family: ui-monospace, SFMono-Regular, Monaco, Consolas, monospace;
  font-size: 0.9em;
}
.qa-chat-input-wrap {
  flex-shrink: 0;
  padding: 0 16px 12px;
  padding-top: 4px;
  border-top: 1px solid #e8eaed;
  background: #fff;
  position: relative;
  display: flex;
  flex-direction: column;
}
.qa-input-resize-handle {
  flex-shrink: 0;
  height: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: ns-resize;
  margin-bottom: 2px;
  border-radius: 4px;
  color: #9aa0a6;
  transition: color 0.15s, background 0.15s;
}
.qa-input-resize-handle:hover {
  color: #1a73e8;
  background: rgba(26, 115, 232, 0.06);
}
.qa-input-resize-handle-bar {
  display: block;
  width: 36px;
  height: 4px;
  border-radius: 2px;
  background: currentColor;
}
.qa-input-box {
  position: relative;
  border: 1px solid #dadce0;
  border-radius: 12px;
  background: #fff;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 120px;
}
.qa-input-box:focus-within {
  border-color: #1a73e8;
  box-shadow: 0 0 0 2px rgba(26, 115, 232, 0.2);
}
.qa-input-box.disabled {
  background: #f8fafc;
  border-color: #e8eaed;
}
.qa-input {
  flex: 1;
  min-height: 0;
  width: 100%;
  padding: 12px 16px 52px 16px;
  padding-right: 100px;
  font-size: 14px;
  border: none;
  outline: none;
  resize: none;
  overflow-y: auto;
  font-family: inherit;
  background: transparent;
  box-sizing: border-box;
}
.qa-input::placeholder {
  color: #9aa0a6;
}
.qa-input-footer {
  position: absolute;
  bottom: 10px;
  right: 16px;
  display: flex;
  align-items: center;
  pointer-events: none;
}
.qa-input-footer .qa-send-btn {
  pointer-events: auto;
}
.qa-send-btn {
  flex-shrink: 0;
  height: 36px;
  padding: 0 20px;
  font-size: 14px;
  color: #fff;
  background: #1a73e8;
  border: none;
  border-radius: 999px;
  cursor: pointer;
}
.qa-send-btn:hover:not(:disabled) {
  background: #1557b0;
}
.qa-send-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
