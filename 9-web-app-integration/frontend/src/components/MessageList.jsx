import { forwardRef } from 'react'

// forwardRef lets App pass the scroll-to-bottom ref into this component
const MessageList = forwardRef(function MessageList({ messages, isStreaming }, ref) {
  if (messages.length === 0) {
    return (
      <div className="messages empty">
        <p className="empty-hint">
          Ask anything. Toggle <strong>Streaming</strong> in the header to compare the experience.
        </p>
        <div ref={ref} />
      </div>
    )
  }

  return (
    <div className="messages">
      {messages.map((msg, i) => {
        const isLastAssistant =
          msg.role === 'assistant' && i === messages.length - 1 && isStreaming

        return (
          <div key={i} className={`message ${msg.role}`}>
            <div className="message-label">
              {msg.role === 'user' ? 'You' : 'Gemini'}
            </div>
            <div className="message-content">
              {msg.content || <span className="thinking">thinking…</span>}
              {isLastAssistant && <span className="cursor" aria-hidden="true" />}
            </div>
          </div>
        )
      })}
      <div ref={ref} />
    </div>
  )
})

export default MessageList
