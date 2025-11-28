import React from 'react'

function SummaryView({ summary }) {
  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
          <span className="text-xl">📋</span>
        </div>
        <h3 className="text-2xl font-bold text-gray-900">Summary</h3>
        <span className="ml-auto text-sm bg-blue-100 text-blue-800 px-3 py-1 rounded-full">
          {summary.style}
        </span>
      </div>

      <div className="space-y-3">
        {summary.bullets && summary.bullets.length > 0 ? (
          summary.bullets.map((bullet, index) => (
            <div key={index} className="flex gap-3 items-start">
              <span className="text-blue-600 font-bold flex-shrink-0 mt-1">•</span>
              <p className="text-gray-700 leading-relaxed">{bullet}</p>
            </div>
          ))
        ) : (
          <p className="text-gray-500 italic">No summary bullets available</p>
        )}
      </div>

      {summary.max_bullets && (
        <p className="text-xs text-gray-500 mt-4">
          Showing up to {summary.max_bullets} key points
        </p>
      )}
    </div>
  )
}

export default SummaryView


