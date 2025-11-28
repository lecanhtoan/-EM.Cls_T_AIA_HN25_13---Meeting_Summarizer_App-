import React from 'react'

function DecisionsView({ decisions }) {
  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
          <span className="text-xl">⚡</span>
        </div>
        <h3 className="text-2xl font-bold text-gray-900">Key Decisions</h3>
        <span className="ml-auto bg-purple-100 text-purple-800 px-3 py-1 rounded-full text-sm font-medium">
          {decisions.length} decisions
        </span>
      </div>

      <div className="space-y-3">
        {decisions.map((decision) => (
          <div
            key={decision.id}
            className="border-l-4 border-purple-500 bg-purple-50 rounded-lg p-4"
          >
            <p className="font-medium text-gray-900">{decision.decision}</p>
            <div className="flex items-center gap-3 mt-2">
              {decision.owner && (
                <span className="text-xs bg-white text-gray-700 px-2 py-1 rounded border border-gray-200">
                  Owner: {decision.owner}
                </span>
              )}
              {decision.decision_date && (
                <span className="text-xs text-gray-600">
                  {new Date(decision.decision_date).toLocaleDateString()}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default DecisionsView


