import React, { useState } from 'react'
import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000/api'

function TranscriptInput({ onProcessComplete, onError, onLoadingChange, onReset }) {
  const [inputMode, setInputMode] = useState('upload') // 'upload' or 'text'
  const [title, setTitle] = useState('')
  const [language, setLanguage] = useState('en')
  const [file, setFile] = useState(null)
  const [textContent, setTextContent] = useState('')
  const [fileName, setFileName] = useState('')

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile) {
      setFile(selectedFile)
      setFileName(selectedFile.name)
      // Auto-fill title from filename
      const nameWithoutExt = selectedFile.name.replace(/\.[^/.]+$/, '')
      setTitle(nameWithoutExt)
    }
  }

  const handleUpload = async (e) => {
    e.preventDefault()

    if (!file || !title) {
      onError('Please select a file and enter a title')
      return
    }

    try {
      onLoadingChange(true)
      const formData = new FormData()
      formData.append('file', file)
      formData.append('title', title)
      formData.append('language', language)

      const response = await axios.post(`${API_BASE_URL}/meetings/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      onProcessComplete(response.data)
      // Reset form
      setFile(null)
      setFileName('')
      setTitle('')
      setLanguage('en')
      document.getElementById('file-input').value = ''
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to process transcript'
      onError(errorMessage)
    } finally {
      onLoadingChange(false)
    }
  }

  const handleTextSubmit = async (e) => {
    e.preventDefault()

    if (!textContent || !title) {
      onError('Please enter both title and transcript text')
      return
    }

    try {
      onLoadingChange(true)
      const response = await axios.post(`${API_BASE_URL}/meetings/text`, {
        title,
        language,
        transcript_text: textContent,
      })

      onProcessComplete(response.data)
      // Reset form
      setTextContent('')
      setTitle('')
      setLanguage('en')
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to process transcript'
      onError(errorMessage)
    } finally {
      onLoadingChange(false)
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Input Transcript</h2>

      {/* Mode Tabs */}
      <div className="flex gap-2 mb-6 border-b border-gray-200">
        <button
          onClick={() => setInputMode('upload')}
          className={`px-4 py-2 font-medium transition-colors ${
            inputMode === 'upload'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          Upload File
        </button>
        <button
          onClick={() => setInputMode('text')}
          className={`px-4 py-2 font-medium transition-colors ${
            inputMode === 'text'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          Paste Text
        </button>
      </div>

      {/* Common Fields */}
      <div className="space-y-4 mb-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Meeting Title *
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g., Team Standup"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Language
          </label>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="en">English</option>
            <option value="vi">Vietnamese</option>
            <option value="es">Spanish</option>
            <option value="fr">French</option>
            <option value="de">German</option>
          </select>
        </div>
      </div>

      {/* Upload Mode */}
      {inputMode === 'upload' && (
        <form onSubmit={handleUpload} className="space-y-4">
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-blue-400 transition-colors">
            <input
              id="file-input"
              type="file"
              accept=".txt,.md"
              onChange={handleFileChange}
              className="hidden"
            />
            <label htmlFor="file-input" className="cursor-pointer">
              <div className="text-gray-600">
                <p className="font-medium mb-1">Click to upload or drag and drop</p>
                <p className="text-sm text-gray-500">Supported formats: .txt, .md</p>
                {fileName && (
                  <p className="text-sm text-blue-600 mt-2 font-medium">
                    Selected: {fileName}
                  </p>
                )}
              </div>
            </label>
          </div>

          <button
            type="submit"
            className="w-full bg-blue-600 text-white font-medium py-2 px-4 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Process Transcript
          </button>
        </form>
      )}

      {/* Text Mode */}
      {inputMode === 'text' && (
        <form onSubmit={handleTextSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Transcript Text *
            </label>
            <textarea
              value={textContent}
              onChange={(e) => setTextContent(e.target.value)}
              placeholder="Paste your meeting transcript here..."
              rows="10"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
            />
          </div>

          <button
            type="submit"
            className="w-full bg-blue-600 text-white font-medium py-2 px-4 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Process Transcript
          </button>
        </form>
      )}

      {/* Reset Button */}
      <button
        onClick={onReset}
        className="w-full mt-4 bg-gray-200 text-gray-700 font-medium py-2 px-4 rounded-lg hover:bg-gray-300 transition-colors"
      >
        Clear Results
      </button>
    </div>
  )
}

export default TranscriptInput


