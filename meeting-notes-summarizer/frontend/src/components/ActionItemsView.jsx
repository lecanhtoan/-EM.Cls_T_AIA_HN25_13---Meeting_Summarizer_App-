import React, { useEffect, useMemo, useState } from 'react'
import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000/api'

function ActionItemsView({ items, meetingId, onUpdated }) {
  const [cards, setCards] = useState([])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)

  useEffect(() => {
    // Initialize editable cards from items
    const mapped = (items || []).map((it) => ({
      id: it.id,
      task: it.task || '',
      assignee: it.assignee || '',
      // convert to YYYY-MM-DD for <input type="date"/>
      deadline: it.deadline ? new Date(it.deadline).toISOString().slice(0, 10) : '',
      priority: it.priority || 'medium',
      status: it.status || 'open',
    }))
    setCards(mapped)
  }, [items])

  const handleChange = (idx, field, value) => {
    setCards((prev) => prev.map((c, i) => (i === idx ? { ...c, [field]: value } : c)))
  }

  const payload = useMemo(() => {
    return {
      items: cards.map((c) => ({
        id: c.id,
        task: c.task,
        assignee: c.assignee || null,
        deadline: c.deadline || null,
        priority: c.priority,
        status: c.status,
      })),
    }
  }, [cards])

  const handleSave = async () => {
    if (!meetingId) return
    try {
      setSaving(true)
      setError(null)
      setSuccess(null)
      const res = await axios.put(`${API_BASE_URL}/meetings/${meetingId}`, payload)
      setSuccess('Saved changes')
      onUpdated && onUpdated(res.data)
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Failed to save')
    } finally {
      setSaving(false)
      setTimeout(() => setSuccess(null), 2000)
    }
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
          <span className="text-xl">✓</span>
        </div>
        <h3 className="text-2xl font-bold text-gray-900">Action Items</h3>
        <span className="ml-auto bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm font-medium">
          {cards.length} items
        </span>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded p-2 mb-3">{error}</div>
      )}
      {success && (
        <div className="bg-green-50 border border-green-200 text-green-700 text-sm rounded p-2 mb-3">{success}</div>
      )}

      {/* Card grid: 3 per row on large screens */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {cards.map((card, idx) => (
          <div key={card.id} className="border rounded-lg p-4 shadow-sm bg-white">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-gray-500">#{card.id}</span>
              <span className="text-xs px-2 py-1 rounded bg-gray-100 text-gray-700">{card.status}</span>
            </div>

            <div className="mb-3">
              <label className="block text-xs font-medium text-gray-600 mb-1">Task</label>
              <textarea
                value={card.task}
                onChange={(e) => handleChange(idx, 'task', e.target.value)}
                className="w-full px-2 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 text-sm"
                rows={2}
                placeholder="Task name"
              />
            </div>

            <div className="mb-3">
              <label className="block text-xs font-medium text-gray-600 mb-1">Assignee</label>
              <input
                type="text"
                value={card.assignee}
                onChange={(e) => handleChange(idx, 'assignee', e.target.value)}
                className="w-full px-2 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 text-sm"
                placeholder="Assignee"
              />
            </div>

            <div className="grid grid-cols-2 gap-2 mb-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Deadline</label>
                <input
                  type="date"
                  value={card.deadline || ''}
                  onChange={(e) => handleChange(idx, 'deadline', e.target.value)}
                  className="w-full px-2 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Priority</label>
                <select
                  value={card.priority}
                  onChange={(e) => handleChange(idx, 'priority', e.target.value)}
                  className="w-full px-2 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 text-sm"
                >
                  <option value="high">high</option>
                  <option value="medium">medium</option>
                  <option value="low">low</option>
                </select>
              </div>
            </div>

            <div className="mb-3">
              <label className="block text-xs font-medium text-gray-600 mb-1">Status</label>
              <select
                value={card.status}
                onChange={(e) => handleChange(idx, 'status', e.target.value)}
                className="w-full px-2 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 text-sm"
              >
                <option value="open">open</option>
                <option value="done">done</option>
                <option value="canceled">canceled</option>
              </select>
            </div>
          </div>
        ))}
      </div>

      <div className="flex justify-end mt-6">
        <button
          onClick={handleSave}
          disabled={saving || !meetingId}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save Changes'}
        </button>
      </div>
    </div>
  )
}

export default ActionItemsView
