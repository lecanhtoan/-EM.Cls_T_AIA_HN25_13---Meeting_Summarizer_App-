import React, { useEffect, useMemo, useRef, useState } from 'react'
import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000/api'

function ChatbotWidget({ meetingId = null, meetingTitle = null }) {
  const [open, setOpen] = useState(false)
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  // Keep history across meeting switches (do NOT reset when meetingId changes)
  const [messages, setMessages] = useState(() => ([
    {
      role: 'assistant',
      content: 'Hi! Ask me anything about your processed meeting summaries.',
      sources: [],
    },
  ]))

  // Default: search across all meetings
  // User can toggle "Only this meeting" when a meeting is selected
  const [onlyThisMeeting, setOnlyThisMeeting] = useState(false)

  const listRef = useRef(null)

  const scopeLabel = useMemo(() => {
    if (onlyThisMeeting && meetingId) {
      return `Scope: This meeting (${meetingTitle ? meetingTitle : `#${meetingId}`})`
    }
    return 'Scope: All meetings'
  }, [onlyThisMeeting, meetingId, meetingTitle])

  useEffect(() => {
    if (!open) return
    const el = listRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [open, messages])

  const sendMessage = async () => {
    const question = input.trim()
    if (!question || busy) return

    setError(null)
    setBusy(true)

    setMessages((prev) => [
      ...prev,
      { role: 'user', content: question },
    ])
    setInput('')

    try {
      const payload = {
        question,
        top_k: 5,
        meeting_ids: (onlyThisMeeting && meetingId) ? [meetingId] : null,
      }

      const res = await axios.post(`${API_BASE_URL}/chatbot/ask`, payload)

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: res.data?.answer || 'No answer returned.',
          sources: res.data?.sources || [],
        },
      ])
    } catch (e) {
      const msg = e.response?.data?.detail || e.message || 'Chat request failed'
      setError(msg)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry—something went wrong while contacting the chatbot API.',
          sources: [],
        },
      ])
    } finally {
      setBusy(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const handleIndex = async () => {
    setError(null)
    setBusy(true)
    try {
      // Index only when user explicitly chooses; keep it aligned with scope toggle
      const payload = (onlyThisMeeting && meetingId) ? { meeting_id: meetingId } : { limit: 200 }
      const res = await axios.post(`${API_BASE_URL}/chatbot/index`, payload)
      const indexed = res.data?.indexed ?? 0

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Indexing complete. Indexed ${indexed} summary record(s).`,
          sources: [],
        },
      ])
    } catch (e) {
      const msg = e.response?.data?.detail || e.message || 'Indexing failed'
      setError(msg)
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      {/* Floating button */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="fixed bottom-6 right-6 z-50 bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg rounded-full w-14 h-14 flex items-center justify-center"
        aria-label="Open chatbot"
        title="Chatbot"
      >
        {open ? '×' : '💬'}
      </button>

      {/* Chat window */}
      {open && (
        <div className="fixed bottom-24 right-6 z-50 w-[22rem] max-w-[90vw] bg-white rounded-xl shadow-2xl border border-gray-200 overflow-hidden">
          {/* Header */}
          <div className="px-4 py-3 bg-gradient-to-r from-indigo-600 to-blue-600 text-white">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="font-semibold">AI Chatbot</div>
                <div className="text-xs opacity-90">{scopeLabel}</div>

                {/* Scope toggle */}
                <div className="mt-2 flex items-center gap-2">
                  <input
                    id="scope-toggle"
                    type="checkbox"
                    className="h-4 w-4"
                    checked={onlyThisMeeting}
                    onChange={(e) => setOnlyThisMeeting(e.target.checked)}
                    disabled={!meetingId}
                  />
                  <label htmlFor="scope-toggle" className={`text-xs ${!meetingId ? 'opacity-70' : ''}`}>
                    Only this meeting
                    {!meetingId ? ' (select a meeting first)' : ''}
                  </label>
                </div>
              </div>

              <button
                onClick={handleIndex}
                disabled={busy}
                className="shrink-0 text-xs bg-white/15 hover:bg-white/25 px-2 py-1 rounded disabled:opacity-60"
                title="Index summaries into Pinecone"
              >
                Index
              </button>
            </div>
          </div>

          {/* Messages */}
          <div ref={listRef} className="h-80 overflow-y-auto px-3 py-3 space-y-3 bg-gray-50">
            {messages.map((m, idx) => (
              <div key={idx} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm shadow-sm ${
                    m.role === 'user'
                      ? 'bg-indigo-600 text-white rounded-br-md'
                      : 'bg-white text-gray-900 rounded-bl-md border border-gray-200'
                  }`}
                >
                  <div className="whitespace-pre-wrap leading-relaxed">{m.content}</div>

                  {/* Sources */}
                  {m.role === 'assistant' && Array.isArray(m.sources) && m.sources.length > 0 && (
                    <details className="mt-2">
                      <summary className="cursor-pointer text-xs text-gray-600 select-none">
                        Sources ({m.sources.length})
                      </summary>
                      <div className="mt-2 space-y-2">
                        {m.sources.map((s, sIdx) => (
                          <div key={sIdx} className="text-xs bg-gray-50 border border-gray-200 rounded p-2">
                            <div className="flex items-center justify-between gap-2">
                              <div className="font-medium text-gray-800 truncate">
                                {s.title || `Meeting #${s.meeting_id}`}
                              </div>
                              <div className="text-[10px] text-gray-500">
                                score: {typeof s.score === 'number' ? s.score.toFixed(3) : s.score}
                              </div>
                            </div>
                            <div className="mt-1 text-gray-700 whitespace-pre-wrap">
                              {s.snippet}
                            </div>
                          </div>
                        ))}
                      </div>
                    </details>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Error */}
          {error && (
            <div className="px-3 py-2 bg-red-50 border-t border-red-200 text-red-700 text-xs">
              {error}
            </div>
          )}

          {/* Input */}
          <div className="p-3 border-t border-gray-200 bg-white">
            <div className="flex gap-2">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask a question…"
                rows={1}
                className="flex-1 resize-none px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
              />
              <button
                onClick={sendMessage}
                disabled={busy || !input.trim()}
                className="bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-2 rounded-lg text-sm disabled:opacity-60"
              >
                {busy ? '...' : 'Send'}
              </button>
            </div>

            <div className="mt-2 text-[11px] text-gray-500">
              Tip: Press <span className="font-medium">Enter</span> to send, <span className="font-medium">Shift+Enter</span> for a new line.
            </div>
          </div>
        </div>
      )}
    </>
  )
}

export default ChatbotWidget