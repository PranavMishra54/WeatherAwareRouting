import axios from 'axios'
import { createMockResponse } from '../mock/mockResponse'
import type { AnalyzeRequest, AnalyzeResponse } from '../types'

const apiUrl = import.meta.env.VITE_API_URL?.trim()
const useMock = import.meta.env.VITE_USE_MOCK === 'true'

const client = axios.create({
  baseURL: apiUrl,
  headers: { 'Content-Type': 'application/json' },
  timeout: 60_000,
})

let healthCheckStarted = false

export function wakeBackend(): void {
  if (useMock || !apiUrl || healthCheckStarted) return
  healthCheckStarted = true
  void client.get('/health/').catch(() => undefined)
}

export async function analyzeTrip(
  request: AnalyzeRequest,
  signal?: AbortSignal,
): Promise<AnalyzeResponse> {
  if (useMock) {
    await new Promise<void>((resolve, reject) => {
      const timeout = window.setTimeout(resolve, 500)
      const onAbort = () => {
        window.clearTimeout(timeout)
        reject(new axios.CanceledError())
      }
      if (signal?.aborted) {
        onAbort()
      } else {
        signal?.addEventListener('abort', onAbort, { once: true })
      }
    })
    return createMockResponse(request)
  }
  if (!apiUrl) throw new Error('VITE_API_URL is not configured')

  const response = await client.post<AnalyzeResponse>(
    '/analyze/',
    {
      ...request,
      departure_time: new Date(request.departure_time).toISOString(),
      load_weight_lb: Number(request.load_weight_lb),
      interval_miles: Number(request.interval_miles),
    },
    { signal },
  )
  return response.data
}
