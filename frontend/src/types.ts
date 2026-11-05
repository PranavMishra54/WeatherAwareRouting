export type RiskLevel = 'low' | 'moderate' | 'high' | 'severe' | 'no_travel'

export type IntervalMiles = 10 | 25 | 50

export interface AnalyzeRequest {
  origin: string
  destination: string
  departure_time: string
  load_weight_lb: number
  interval_miles: IntervalMiles
}

export interface RouteSummary {
  no_travel_miles: number
  severe_miles: number
  high_miles: number
  moderate_miles: number
  low_miles: number
  avg_risk: number
  max_risk: RiskLevel
}

export interface Checkpoint {
  mile: number
  lat: number
  lon: number
  eta: string
  forecast_time: string
  wind_mph: number
  rain_in_hr: number
  snow_in_hr: number
  risk: RiskLevel
  reasons: string[]
}

export interface Route {
  id: number
  distance_miles: number
  duration_hours: number
  arrival_time: string
  path: [number, number][]
  summary: RouteSummary
  recommendation_reason: string
  checkpoints: Checkpoint[]
}

export interface Heatmap {
  hours: number[]
  frames: [number, number, number][][]
  start_time: string | null
}

export interface AnalyzeResponse {
  recommended_route_id: number
  routes: Route[]
  heatmap: Heatmap
}
