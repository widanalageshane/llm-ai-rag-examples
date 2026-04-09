/**
 * Day 9 Demo: LLM Chat with Streaming
 *
 * Key things to point out during demo:
 * 1. Toggle streaming ON/OFF to feel the UX difference
 * 2. The fetch + ReadableStream pattern (not EventSource — we need POST)
 * 3. Conversation history is maintained client-side and sent each request
 * 4. Token cost shows up after each response
 */

import { useEffect, useRef, useState } from 'react'
import ChatInput from './components/ChatInput'
import MessageList from './components/MessageList'
import UsageBar from './components/UsageBar'

const API_BASE = 'http://localhost:8000'

// Generate a stable session ID per browser tab
const SESSION_ID = `session-${Math.random().toString(36).slice(2, 9)}`

export default function App() {
  const [messages, setMessages] = useState([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingEnabled, setStreamingEnabled] = useState(true)
  const [lastUsage, setLastUsage] = useState(null)
  const [error, setError] = useState(null)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Convert our message format → Gemini history format
  // Gemini uses "model" not "assistant", and "parts" not "content"
  function buildHistory(msgs) {
    return msgs.map((m) => ({
      role: m.role === 'assistant' ? 'model' : 'user',
      parts: [{ text: m.content }],
    }))
  }

  async function sendMessage(text) {
    if (!text.trim() || isStreaming) return

    setError(null)
    const userMsg = { role: 'user', content: text }
    const updatedMessages = [...messages, userMsg]
    setMessages(updatedMessages)
    setIsStreaming(true)

    // History for the API is everything except the last user message
    // (the last message is sent as `message`, not in `history`)
    const history = buildHistory(messages)

    try {
      if (streamingEnabled) {
        await streamResponse(text, history, updatedMessages)
      } else {
        await fetchResponse(text, history, updatedMessages)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setIsStreaming(false)
    }
  }

  // ── Streaming: fetch + ReadableStream ─────────────────────────────────────
  // Why not EventSource? EventSource only supports GET. We need POST to send
  // the message body. The fetch ReadableStream API gives us the same streaming
  // behaviour with full control over the request.
  async function streamResponse(message, history, currentMessages) {
    const response = await fetch(`${API_BASE}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, history, session_id: SESSION_ID }),
    })

    if (!response.ok) {
      const err = await response.json()
      throw new Error(err.detail || `Server error: ${response.status}`)
    }

    // Add an empty assistant message slot — we'll fill it in as chunks arrive
    const assistantIndex = currentMessages.length
    setMessages([...currentMessages, { role: 'assistant', content: '' }])

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let fullText = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      // SSE events are separated by "\n\n"
      const events = buffer.split('\n\n')
      buffer = events.pop() // last item may be incomplete

      for (const event of events) {
        if (!event.startsWith('data: ')) continue
        const data = JSON.parse(event.slice(6))

        if (data.type === 'text') {
          fullText += data.content
          // Functional update to avoid stale closure over assistantIndex
          setMessages((prev) => {
            const updated = [...prev]
            updated[assistantIndex] = { role: 'assistant', content: fullText }
            return updated
          })
        } else if (data.type === 'done') {
          setLastUsage(data.usage)
        }
      }
    }
  }

  // ── Non-streaming: regular fetch ──────────────────────────────────────────
  async function fetchResponse(message, history, currentMessages) {
    const response = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, history, session_id: SESSION_ID }),
    })

    if (!response.ok) {
      const err = await response.json()
      throw new Error(err.detail || `Server error: ${response.status}`)
    }

    const data = await response.json()
    setMessages([...currentMessages, { role: 'assistant', content: data.response }])
    setLastUsage(data.usage)
  }

  function clearChat() {
    setMessages([])
    setLastUsage(null)
    setError(null)
  }

  return (
    <div className="app">
      <header className="header">
        <div className="header-title">
          <h1>LLM Chat Demo</h1>
          <span className="session-id">Session: {SESSION_ID}</span>
        </div>
        <div className="header-controls">
          <label className="streaming-toggle">
            <input
              type="checkbox"
              checked={streamingEnabled}
              onChange={(e) => setStreamingEnabled(e.target.checked)}
              disabled={isStreaming}
            />
            <span>Streaming</span>
          </label>
          <button onClick={clearChat} className="btn-clear" disabled={isStreaming}>
            Clear chat
          </button>
        </div>
      </header>

      {lastUsage && <UsageBar usage={lastUsage} />}

      {error && (
        <div className="error-banner">
          {error}
        </div>
      )}

      <MessageList messages={messages} isStreaming={isStreaming} ref={messagesEndRef} />

      <ChatInput onSend={sendMessage} disabled={isStreaming} />
    </div>
  )
}
