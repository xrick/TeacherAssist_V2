/**
 * Server-Sent Events (SSE) Hook
 *
 * Custom React hook for handling SSE connections for real-time progress updates
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import type { GenerationRequest, ProgressUpdate, GenerationResponse } from '@/types/api'
import { generationAPI } from '@/api/client'

export interface SSEState {
  isConnected: boolean
  isGenerating: boolean
  progress: ProgressUpdate | null
  result: GenerationResponse | null
  error: string | null
}

export interface UseSSEReturn extends SSEState {
  startGeneration: (request: GenerationRequest) => void
  stopGeneration: () => void
  reset: () => void
}

/**
 * Hook for SSE-based presentation generation with real-time progress
 */
export function useSSE(): UseSSEReturn {
  const [state, setState] = useState<SSEState>({
    isConnected: false,
    isGenerating: false,
    progress: null,
    result: null,
    error: null,
  })

  const eventSourceRef = useRef<EventSource | null>(null)
  const requestRef = useRef<GenerationRequest | null>(null)

  /**
   * Close existing SSE connection
   */
  const closeConnection = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    setState((prev) => ({ ...prev, isConnected: false, isGenerating: false }))
  }, [])

  /**
   * Start generation with SSE progress updates
   */
  const startGeneration = useCallback((request: GenerationRequest) => {
    // Close any existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }

    // Reset state
    setState({
      isConnected: false,
      isGenerating: true,
      progress: null,
      result: null,
      error: null,
    })

    requestRef.current = request

    try {
      // Create SSE connection with POST data via URL params (EventSource doesn't support POST)
      // We'll send a POST request first, then connect to SSE stream
      const streamUrl = new URL(generationAPI.getStreamUrl())

      // For SSE, we need to send the request body via fetch POST
      fetch(streamUrl.toString(), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
        },
        body: JSON.stringify(request),
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`)
          }

          const reader = response.body?.getReader()
          const decoder = new TextDecoder()

          if (!reader) {
            throw new Error('No response body reader')
          }

          setState((prev) => ({ ...prev, isConnected: true }))

          // Read stream
          const readStream = async () => {
            try {
              while (true) {
                const { done, value } = await reader.read()

                if (done) {
                  setState((prev) => ({ ...prev, isConnected: false, isGenerating: false }))
                  break
                }

                // Decode and parse SSE messages
                const chunk = decoder.decode(value, { stream: true })
                const lines = chunk.split('\n')

                for (const line of lines) {
                  if (line.startsWith('event:')) {
                    // Skip event type line (we determine type from data content)
                    continue
                  }

                  if (line.startsWith('data:')) {
                    const data = line.substring(5).trim()

                    if (data) {
                      try {
                        const parsed = JSON.parse(data)

                        // Handle different event types
                        if (parsed.stage !== undefined && parsed.progress !== undefined) {
                          // Progress event
                          setState((prev) => ({
                            ...prev,
                            progress: parsed as ProgressUpdate,
                          }))
                        } else if (parsed.presentation_id) {
                          // Complete event
                          setState((prev) => ({
                            ...prev,
                            result: parsed as GenerationResponse,
                            isGenerating: false,
                            isConnected: false,
                          }))
                        } else if (parsed.error) {
                          // Error event
                          setState((prev) => ({
                            ...prev,
                            error: parsed.error,
                            isGenerating: false,
                            isConnected: false,
                          }))
                        }
                      } catch (e) {
                        console.error('Failed to parse SSE data:', e, data)
                      }
                    }
                  }
                }
              }
            } catch (error) {
              console.error('Stream reading error:', error)
              setState((prev) => ({
                ...prev,
                error: error instanceof Error ? error.message : 'Stream error',
                isGenerating: false,
                isConnected: false,
              }))
            }
          }

          readStream()
        })
        .catch((error) => {
          console.error('SSE connection error:', error)
          setState((prev) => ({
            ...prev,
            error: error instanceof Error ? error.message : 'Connection failed',
            isGenerating: false,
            isConnected: false,
          }))
        })
    } catch (error) {
      console.error('Failed to start generation:', error)
      setState((prev) => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Failed to start generation',
        isGenerating: false,
      }))
    }
  }, [])

  /**
   * Stop ongoing generation
   */
  const stopGeneration = useCallback(() => {
    closeConnection()
    setState((prev) => ({
      ...prev,
      isGenerating: false,
      error: 'Generation cancelled by user',
    }))
  }, [closeConnection])

  /**
   * Reset state
   */
  const reset = useCallback(() => {
    closeConnection()
    setState({
      isConnected: false,
      isGenerating: false,
      progress: null,
      result: null,
      error: null,
    })
  }, [closeConnection])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      closeConnection()
    }
  }, [closeConnection])

  return {
    ...state,
    startGeneration,
    stopGeneration,
    reset,
  }
}
