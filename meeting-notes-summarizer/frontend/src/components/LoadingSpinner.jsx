import React from 'react'

function LoadingSpinner() {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <div className="relative w-16 h-16 mb-4">
        <div className="absolute inset-0 bg-gradient-to-r from-blue-400 to-blue-600 rounded-full animate-spin"></div>
        <div className="absolute inset-2 bg-white rounded-full"></div>
      </div>
      <p className="text-gray-600 font-medium">Processing your transcript...</p>
      <p className="text-gray-500 text-sm mt-2">This may take a moment</p>
    </div>
  )
}

export default LoadingSpinner


