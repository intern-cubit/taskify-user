import React, { useState, useEffect } from 'react'
import { Play, Loader2, Zap } from 'lucide-react'
import toast from 'react-hot-toast'

const Dashboard = () => {
  const [isStarting, setIsStarting] = useState(false)
  const [isRunningAutomation, setIsRunningAutomation] = useState(false)
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [isCheckingStatus, setIsCheckingStatus] = useState(true)
  const [automationResult, setAutomationResult] = useState(null) // { success, message, processed_count, status }
  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

  // Check browser status on mount
  useEffect(() => {
    checkBrowserStatus()
  }, [])

  const checkBrowserStatus = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/check-browser-status`)
      const data = await response.json()

      if (response.ok && data.success) {
        if (data.browser_open && data.logged_in) {
          setIsLoggedIn(true)
          toast.success('Browser is already open and logged in!')
        }
      }
    } catch (error) {
      console.error('Error checking browser status:', error)
    } finally {
      setIsCheckingStatus(false)
    }
  }

  const handleStart = async () => {
    setIsStarting(true)
    try {
      const response = await fetch(`${API_BASE_URL}/start-browser`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      const data = await response.json()

      if (response.ok && data.success) {
        if (data.reused_session) {
          toast.success('Using existing browser session!')
        } else {
          toast.success(data.message || 'Browser started successfully! Please login.')
        }
        setIsLoggedIn(true)
      } else {
        toast.error(data.message || 'Failed to start browser')
      }
    } catch (error) {
      console.error('Error starting browser:', error)
      toast.error('Failed to start browser. Check backend connection.')
    } finally {
      setIsStarting(false)
    }
  }

  const handleRunAutomation = async () => {
    setIsRunningAutomation(true)
    setAutomationResult(null) // Clear previous result
    
    try {
      const response = await fetch(`${API_BASE_URL}/run-automation`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      const data = await response.json()

      // Store the result for display
      setAutomationResult({
        success: data.success,
        message: data.message || (data.success ? 'Automation completed successfully!' : 'Automation failed'),
        processed_count: data.processed_count,
        status: data.status,
        error: data.error
      })

      if (response.ok && data.success) {
        toast.success('Automation completed!')
      } else {
        toast.error('Automation encountered errors')
      }
    } catch (error) {
      console.error('Error running automation:', error)
      setAutomationResult({
        success: false,
        message: 'Failed to run automation. Check backend connection.',
        status: 'error',
        error: error.message
      })
      toast.error('Failed to run automation. Check backend connection.')
    } finally {
      setIsRunningAutomation(false)
    }
  }

  if (isCheckingStatus) {
    return (
      <div className="min-h-screen p-8 flex items-center justify-center">
        <div className="flex items-center space-x-3">
          <Loader2 className="animate-spin text-blue-600" size={32} />
          <span className="text-lg text-gray-700 dark:text-gray-300">Checking browser status...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen p-8">
      <div className="max-w-7xl mx-auto">
        <div className="bg-white/70 backdrop-blur-lg border border-gray-200 dark:bg-gray-800/50 dark:border-gray-700 rounded-2xl p-8 shadow-xl">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-6">
            Taskify Dashboard
          </h1>
          
          <div className="mt-8 space-y-4">
            {!isLoggedIn ? (
              <button
                onClick={handleStart}
                disabled={isStarting}
                className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-bold py-4 px-8 rounded-lg shadow-lg transition-all duration-300 ease-in-out transform hover:scale-105 disabled:transform-none disabled:cursor-not-allowed flex items-center justify-center space-x-2 min-w-[200px]"
              >
                {isStarting ? (
                  <>
                    <Loader2 className="animate-spin" size={24} />
                    <span>Starting...</span>
                  </>
                ) : (
                  <>
                    <Play size={24} />
                    <span>Start</span>
                  </>
                )}
              </button>
            ) : (
              <div className="space-y-4">
                <div className="bg-green-100 dark:bg-green-900/30 border border-green-300 dark:border-green-700 rounded-lg p-4">
                  <p className="text-green-800 dark:text-green-200 font-semibold">
                    ✅ Browser started and login acknowledged! You can now run the automation.
                  </p>
                </div>
                
                <button
                  onClick={handleRunAutomation}
                  disabled={isRunningAutomation}
                  className="bg-green-600 hover:bg-green-700 disabled:bg-green-400 text-white font-bold py-4 px-8 rounded-lg shadow-lg transition-all duration-300 ease-in-out transform hover:scale-105 disabled:transform-none disabled:cursor-not-allowed flex items-center justify-center space-x-2 min-w-[200px]"
                >
                  {isRunningAutomation ? (
                    <>
                      <Loader2 className="animate-spin" size={24} />
                      <span>Running Automation...</span>
                    </>
                  ) : (
                    <>
                      <Zap size={24} />
                      <span>Start Automation</span>
                    </>
                  )}
                </button>

                {/* Automation Result Display */}
                {automationResult && (
                  <div 
                    className={`rounded-lg p-6 border-2 ${
                      automationResult.success 
                        ? 'bg-green-50 dark:bg-green-900/20 border-green-500 dark:border-green-600' 
                        : 'bg-red-50 dark:bg-red-900/20 border-red-500 dark:border-red-600'
                    }`}
                  >
                    <div className="flex items-start space-x-3">
                      <div className={`flex-shrink-0 text-2xl ${automationResult.success ? 'text-green-600' : 'text-red-600'}`}>
                        {automationResult.success ? '✅' : '❌'}
                      </div>
                      <div className="flex-1">
                        <h3 className={`text-lg font-bold mb-2 ${
                          automationResult.success 
                            ? 'text-green-900 dark:text-green-100' 
                            : 'text-red-900 dark:text-red-100'
                        }`}>
                          {automationResult.success ? 'Automation Completed Successfully!' : 'Automation Failed'}
                        </h3>
                        
                        <p className={`text-sm mb-3 whitespace-pre-wrap ${
                          automationResult.success 
                            ? 'text-green-800 dark:text-green-200' 
                            : 'text-red-800 dark:text-red-200'
                        }`}>
                          {automationResult.message}
                        </p>
                        
                        {automationResult.processed_count !== undefined && (
                          <div className={`inline-block px-3 py-1 rounded-full text-sm font-semibold ${
                            automationResult.success 
                              ? 'bg-green-200 dark:bg-green-800 text-green-900 dark:text-green-100' 
                              : 'bg-red-200 dark:bg-red-800 text-red-900 dark:text-red-100'
                          }`}>
                            Items Processed: {automationResult.processed_count}
                          </div>
                        )}
                        
                        {automationResult.status && (
                          <div className={`inline-block ml-2 px-3 py-1 rounded-full text-xs font-medium ${
                            automationResult.success 
                              ? 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300' 
                              : 'bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300'
                          }`}>
                            Status: {automationResult.status}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard