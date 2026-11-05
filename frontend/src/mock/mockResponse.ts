import type { AnalyzeRequest, AnalyzeResponse, Checkpoint, RiskLevel, Route } from '../types'

const routeDefinitions = [
  {
    id: 1,
    distance: 923,
    duration: 14.8,
    name: 'I-55 · I-44 · I-35',
    reason: 'Lowest overall weather exposure while keeping travel time competitive.',
    path: [
      [41.8781, -87.6298],
      [39.0997, -94.5786],
      [37.6872, -97.3301],
      [35.4676, -97.5164],
      [32.7767, -96.797],
    ] as [number, number][],
  },
  {
    id: 2,
    distance: 967,
    duration: 15.6,
    name: 'I-57 · I-40 · I-30',
    reason: 'A steady southern alternative with fewer high-wind segments.',
    path: [
      [41.8781, -87.6298],
      [38.627, -90.1994],
      [36.1627, -86.7816],
      [34.7465, -92.2896],
      [32.7767, -96.797],
    ] as [number, number][],
  },
  {
    id: 3,
    distance: 946,
    duration: 15.2,
    name: 'I-55 · I-70 · I-44',
    reason: 'A western arc that avoids the most intense forecast cells.',
    path: [
      [41.8781, -87.6298],
      [39.7817, -89.6501],
      [38.627, -90.1994],
      [37.0842, -94.5133],
      [35.4676, -97.5164],
      [32.7767, -96.797],
    ] as [number, number][],
  },
]

const riskPattern: RiskLevel[] = [
  'low', 'low', 'moderate', 'moderate', 'high', 'moderate', 'low', 'low',
  'moderate', 'high', 'severe', 'high', 'moderate', 'low', 'moderate', 'low',
  'low', 'moderate', 'high', 'moderate', 'low', 'low', 'moderate', 'low', 'low',
]

function checkpointFor(route: (typeof routeDefinitions)[number], index: number, departure: Date): Checkpoint {
  const progress = (index + 1) / 26
  const segmentCount = route.path.length - 1
  const segmentPosition = progress * segmentCount
  const segmentIndex = Math.min(Math.floor(segmentPosition), segmentCount - 1)
  const segmentProgress = segmentPosition - segmentIndex
  const start = route.path[segmentIndex]
  const end = route.path[segmentIndex + 1]
  const mile = Math.round(route.distance * progress / 10) * 10
  const risk = riskPattern[(index + route.id * 3) % riskPattern.length]
  const weatherSeverity = risk === 'severe' ? 1 : risk === 'high' ? 0.72 : risk === 'moderate' ? 0.38 : 0.12
  const eta = new Date(departure.getTime() + route.duration * 3_600_000 * progress)
  const reasons = risk === 'severe'
    ? ['Thunderstorms and poor visibility expected', 'Wind gusts above 40 mph']
    : risk === 'high'
      ? ['Heavy rain may reduce stopping distance', 'Crosswinds near exposed sections']
      : risk === 'moderate'
        ? ['Intermittent showers in the forecast']
        : ['No significant weather concerns']

  return {
    mile,
    lat: start[0] + (end[0] - start[0]) * segmentProgress,
    lon: start[1] + (end[1] - start[1]) * segmentProgress,
    eta: eta.toISOString(),
    forecast_time: new Date(Math.round(eta.getTime() / 3_600_000) * 3_600_000).toISOString(),
    wind_mph: Math.round(8 + weatherSeverity * 34 + ((index * 7) % 8)),
    rain_in_hr: Number((weatherSeverity * (risk === 'severe' ? 0.42 : 0.24)).toFixed(2)),
    snow_in_hr: 0,
    risk,
    reasons,
  }
}

function makeRoute(
  definition: (typeof routeDefinitions)[number],
  departure: Date,
): Route {
  const checkpoints = Array.from({ length: 25 }, (_, index) =>
    checkpointFor(definition, index, departure),
  )
  const severeMiles = checkpoints.filter((checkpoint) => checkpoint.risk === 'severe').length * 10
  const highMiles = checkpoints.filter((checkpoint) => checkpoint.risk === 'high').length * 10
  const riskScore: Record<RiskLevel, number> = {
    low: 1,
    moderate: 2,
    high: 3,
    severe: 4,
    no_travel: 5,
  }
  const avgRisk = checkpoints.reduce((sum, checkpoint) => sum + riskScore[checkpoint.risk], 0) / checkpoints.length
  const maxRisk = checkpoints.reduce<RiskLevel>(
    (highest, checkpoint) => riskScore[checkpoint.risk] > riskScore[highest] ? checkpoint.risk : highest,
    'low',
  )
  const arrival = new Date(departure.getTime() + definition.duration * 3_600_000)

  return {
    id: definition.id,
    distance_miles: definition.distance,
    duration_hours: definition.duration,
    arrival_time: arrival.toISOString(),
    path: definition.path,
    summary: {
      no_travel_miles: 0,
      severe_miles: severeMiles,
      high_miles: highMiles,
      moderate_miles: checkpoints.filter((checkpoint) => checkpoint.risk === 'moderate').length * 10,
      low_miles: checkpoints.filter((checkpoint) => checkpoint.risk === 'low').length * 10,
      avg_risk: Number(avgRisk.toFixed(1)),
      max_risk: maxRisk,
    },
    recommendation_reason: definition.reason,
    checkpoints,
  }
}

export function createMockResponse(request: AnalyzeRequest): AnalyzeResponse {
  const departure = new Date(request.departure_time)
  const routes = routeDefinitions.map((definition) => makeRoute(definition, departure))
  const hours = Array.from({ length: 49 }, (_, hour) => hour)
  const frames = hours.map((hour) =>
    Array.from({ length: 30 }, (_, index) => {
      const lat = 39.2 + ((index * 17 + hour * 3) % 55) / 10
      const lon = -101.5 + ((index * 29 + hour * 5) % 125) / 10
      const movingBand = Math.abs(Math.sin((index + hour * 0.7) / 5))
      const intensity = Math.min(1, 0.15 + movingBand * 0.8)
      return [lat, lon, Number(intensity.toFixed(2))] as [number, number, number]
    }),
  )

  return {
    recommended_route_id: 1,
    routes,
    heatmap: { hours, frames, start_time: departure.toISOString() },
  }
}
