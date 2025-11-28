import React, { useState } from 'react'
import TranscriptInput from './components/TranscriptInput'
import SummaryView from './components/SummaryView'
import ActionItemsView from './components/ActionItemsView'
import DecisionsView from './components/DecisionsView'
import LoadingSpinner from './components/LoadingSpinner'
import MeetingsList from './components/MeetingsList'

function App() {
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleProcessComplete = (data) => {
    setResults(data)
    setError(null)
  }

  const handleError = (errorMessage) => {
    setError(errorMessage)
    setResults(null)
  }

  const handleLoadingChange = (isLoading) => {
    setLoading(isLoading)
  }

  const handleReset = () => {
    setResults(null)
    setError(null)
  }

  const handleBackToList = () => {
    setResults(null)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Meeting Notes Summarizer
          </h1>
          <p className="text-lg text-gray-600">
            Extract summaries, action items, and decisions from your meeting transcripts
          </p>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column: Input only */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow-lg p-6 sticky top-8">
              <TranscriptInput
                onProcessComplete={handleProcessComplete}
                onError={handleError}
                onLoadingChange={handleLoadingChange}
                onReset={handleReset}
              />
            </div>
          </div>

          {/* Right Column: Results or Meetings list */}
          <div className="lg:col-span-2">
            {loading && <LoadingSpinner />}

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
                <p className="text-red-800 font-semibold">Error</p>
                <p className="text-red-700 mt-1">{error}</p>
              </div>
            )}

            {results && !loading && (
              <div className="space-y-6">
                {/* Back Button */}
                <div className="flex justify-start">
                  <button
                    onClick={handleBackToList}
                    className="px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 text-gray-800 rounded"
                  >
                    ← Back to all meetings
                  </button>
                </div>

                {/* Meeting Title */}
                <div className="bg-white rounded-lg shadow p-4">
                  <h2 className="text-2xl font-bold text-gray-900">{results.title}</h2>
                  <p className="text-sm text-gray-500 mt-1">
                    Language: {results.language} • Created: {new Date(results.created_at).toLocaleDateString()}
                  </p>
                </div>

                {/* Summary */}
                {results.summary && (
                  <SummaryView summary={results.summary} />
                )}

                {/* Action Items */}
                {results.action_items && results.action_items.length > 0 && (
                  <ActionItemsView items={results.action_items} meetingId={results.meeting_id || results.id} onUpdated={setResults} />
                )}

                {/* Decisions */}
                {results.decisions && results.decisions.length > 0 && (
                  <DecisionsView decisions={results.decisions} />
                )}
              </div>
            )}

            {!results && !loading && !error && (
              <div className="bg-white rounded-lg shadow p-4">
                <MeetingsList onSelectMeeting={setResults} />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
