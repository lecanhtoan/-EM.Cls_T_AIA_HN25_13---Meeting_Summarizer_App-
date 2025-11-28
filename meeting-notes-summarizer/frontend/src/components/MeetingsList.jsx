import React, { useEffect, useState } from 'react'
import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000/api'

function MeetingsList({ onSelectMeeting }) {
  const [meetings, setMeetings] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchMeetings = async () => {
    try {
      setLoading(true)
      const res = await axios.get(`${API_BASE_URL}/meetings`)
      setMeetings(res.data.meetings || [])
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Failed to load meetings')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchMeetings()
  }, [])

  const handleClick = async (id) => {
    try {
      setLoading(true)
      const res = await axios.get(`${API_BASE_URL}/meetings/${id}`)
      onSelectMeeting && onSelectMeeting(res.data)
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Failed to load meeting details')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-semibold text-gray-900">Processed Meetings</h3>
        <button
          onClick={fetchMeetings}
          className="text-sm px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded"
        >
          Refresh
        </button>
      </div>
      {loading && <p className="text-sm text-gray-500">Loading...</p>}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded p-2 mb-2">{error}</div>
      )}
      {meetings.length === 0 ? (
        <p className="text-sm text-gray-500">No meetings yet.</p>
      ) : (
        <ul className="divide-y divide-gray-200 border rounded">
          {meetings.map((m) => (
            <li key={m.id} className="p-3 hover:bg-gray-50 cursor-pointer" onClick={() => handleClick(m.id)}>
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900">{m.title}</p>
                  <p className="text-xs text-gray-500">{new Date(m.created_at).toLocaleString()} • {m.language}</p>
                </div>
                <span className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded">{m.source}</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default MeetingsList

