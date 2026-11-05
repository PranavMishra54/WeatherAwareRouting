import { useCallback, useEffect, useRef, useState } from 'react'
import axios from 'axios'
import { analyzeTrip } from '../api/client'
import type { AnalyzeRequest, AnalyzeResponse } from '../types'

export function useAnalyze() {
  const [loading, setLoading] = useState(false)
  const [wakingUp, setWakingUp] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<AnalyzeResponse | null>(null)
  const controllerRef = useRef<AbortController | null>(null)

  const submit = useCallback(async (request: AnalyzeRequest) => {
    controllerRef.current?.abort()
    const controller = new AbortController()
    controllerRef.current = controller
    setLoading(true)
    setWakingUp(false)
    setError(null)
    const wakeupTimer = window.setTimeout(() => {
      if (controllerRef.current === controller) setWakingUp(true)
    }, 5000)
    try {
      const response = await analyzeTrip(request, controller.signal)
      setData(response)
      return response
    } catch (requestError: unknown) {
      if (axios.isCancel(requestError)) return null
      const message = getErrorMessage(requestError)
      if (controllerRef.current === controller) setError(message)
      return null
    } finally {
      window.clearTimeout(wakeupTimer)
      if (controllerRef.current === controller) {
        controllerRef.current = null
        setLoading(false)
        setWakingUp(false)
      }
    }
  }, [])

  useEffect(() => () => controllerRef.current?.abort(), [])

  return { loading, wakingUp, error, data, submit }
}

function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (!error.response) return 'Could not reach the server'
    const responseData: unknown = error.response.data
    if (
      typeof responseData === 'object' &&
      responseData !== null &&
      'error' in responseData &&
      typeof responseData.error === 'string'
    ) {
      return responseData.error
    }
  }

  return error instanceof Error && error.message
    ? error.message
    : 'Something went wrong'
}
