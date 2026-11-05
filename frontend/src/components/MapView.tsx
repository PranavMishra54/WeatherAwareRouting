import { memo, useEffect, useMemo, useRef } from 'react'
import * as L from 'leaflet'
import { CircleMarker, MapContainer, Polyline, Popup, TileLayer, useMap } from 'react-leaflet'
import type { AnalyzeResponse, Checkpoint, Route, RiskLevel } from '../types'
import { formatLocalDateTime } from '../utils/format'

interface MapViewProps {
  data: AnalyzeResponse | null
  selectedRouteId: number | null
  hoveredMile: number | null
  onCheckpointHover: (mile: number | null) => void
  heatmapHour: number
  showHeatmap: boolean
}

const riskColors: Record<RiskLevel, string> = {
  low: '#29a36a',
  moderate: '#e5b72d',
  high: '#ed8b2f',
  severe: '#d94e45',
  no_travel: '#352444',
}

const routeColors: Record<number, string> = { 0: '#13845d', 1: '#da8c38', 2: '#607ba9' }
const routeOptions = { preferCanvas: true, zoomControl: true }
const emptyFrame: [number, number, number][] = []

function FitRoutes({ routes }: { routes: Route[] }) {
  const map = useMap()
  useEffect(() => {
    if (routes.length === 0) return
    const points = routes.flatMap((route) => route.path.map(([lat, lon]) => L.latLng(lat, lon)))
    map.fitBounds(L.latLngBounds(points), { padding: [55, 55], maxZoom: 7 })
  }, [map, routes])
  return null
}

interface RouteLinesProps {
  routes: Route[]
  selectedRouteId: number | null
  recommendedRouteId: number
}

const RouteLines = memo(function RouteLines({ routes, selectedRouteId, recommendedRouteId }: RouteLinesProps) {
  return (
    <>
      {routes.map((route) => {
        const selected = route.id === selectedRouteId
        const recommended = route.id === recommendedRouteId
        return (
          <Polyline
            key={route.id}
            positions={route.path}
            pathOptions={{
              color: routeColors[route.id] ?? '#52665c',
              weight: selected ? 6 : 3,
              opacity: selected ? 0.95 : 0.38,
              dashArray: recommended ? '12 7' : undefined,
              lineCap: 'round',
              lineJoin: 'round',
            }}
          />
        )
      })}
    </>
  )
})

const CheckpointMarkers = memo(function CheckpointMarkers({
  checkpoints,
  hoveredMile,
  onHover,
}: {
  checkpoints: Checkpoint[]
  hoveredMile: number | null
  onHover: (mile: number | null) => void
}) {
  return (
    <>
      {checkpoints.map((checkpoint) => {
        const focused = hoveredMile === checkpoint.mile
        return (
          <CircleMarker
            key={checkpoint.mile}
            center={[checkpoint.lat, checkpoint.lon]}
            radius={focused ? 9 : 6}
            pathOptions={{
              color: '#fff',
              weight: focused ? 3 : 2,
              fillColor: riskColors[checkpoint.risk],
              fillOpacity: 0.95,
            }}
            eventHandlers={{
              mouseover: () => onHover(checkpoint.mile),
              mouseout: () => onHover(null),
            }}
          >
            <Popup>
              <div className="flex max-w-[245px] flex-col gap-1 text-xs leading-[1.4] text-[#5d6c62]">
                <b className="text-sm capitalize text-[#25352b]">Mile {checkpoint.mile}</b>
                <span>ETA {formatLocalDateTime(checkpoint.eta)} · Forecast {formatLocalDateTime(checkpoint.forecast_time)} · {checkpoint.risk.replace('_', ' ')}</span>
                <span>Wind {checkpoint.wind_mph} mph · Rain {checkpoint.rain_in_hr.toFixed(2)} in/hr · Snow {checkpoint.snow_in_hr.toFixed(2)} in/hr</span>
                <span>{checkpoint.reasons.join(' · ')}</span>
              </div>
            </Popup>
          </CircleMarker>
        )
      })}
    </>
  )
})

const TripMarkers = memo(function TripMarkers({ routes }: { routes: Route[] }) {
  const first = routes[0]
  if (!first || first.path.length < 2) return null
  const origin = first.path[0]
  const destination = first.path[first.path.length - 1]
  return (
    <>
      <CircleMarker center={origin} radius={9} pathOptions={{ color: '#fff', weight: 3, fillColor: '#147952', fillOpacity: 1 }}>
        <Popup>Origin</Popup>
      </CircleMarker>
      <CircleMarker center={destination} radius={9} pathOptions={{ color: '#fff', weight: 3, fillColor: '#26332d', fillOpacity: 1 }}>
        <Popup>Destination</Popup>
      </CircleMarker>
    </>
  )
})

function HeatmapLayer({ frame, visible }: { frame: [number, number, number][]; visible: boolean }) {
  const map = useMap()
  const layerRef = useRef<L.HeatLayer | null>(null)

  useEffect(() => {
    if (!visible) return
    let cancelled = false
    let layer: L.HeatLayer | null = null
    let updateRadius: (() => void) | null = null

    const initialize = async () => {
      ;(globalThis as typeof globalThis & { L: typeof L }).L = L
      await import('leaflet.heat')
      if (cancelled) return

      layer = L.heatLayer([], {
        radius: heatRadius(map.getZoom()),
        blur: heatBlur(map.getZoom()),
        maxZoom: 8,
        max: 1,
        minOpacity: 0.25,
        gradient: {
          0.03: '#35a66f',
          0.25: '#f0d83b',
          0.5: '#f28c2d',
          0.75: '#d9473f',
          1: '#352444',
        },
      })
      updateRadius = () => {
        const zoom = map.getZoom()
        layer?.setOptions({
          radius: heatRadius(zoom),
          blur: heatBlur(zoom),
          max: 1,
        })
      }
      const canvasPrototype = HTMLCanvasElement.prototype
      const originalGetContext = canvasPrototype.getContext
      const patchedGetContext = function (
        this: HTMLCanvasElement,
        contextId: string,
        options?: CanvasRenderingContext2DSettings,
      ) {
        if (contextId === '2d' && this.classList.contains('leaflet-heatmap-layer')) {
          return originalGetContext.call(this, '2d', { ...options, willReadFrequently: true })
        }
        return Reflect.apply(originalGetContext, this, [contextId, options]) as ReturnType<typeof originalGetContext>
      } as typeof canvasPrototype.getContext
      canvasPrototype.getContext = patchedGetContext
      try {
        layer.addTo(map)
      } finally {
        canvasPrototype.getContext = originalGetContext
      }
      layerRef.current = layer
      map.on('zoomend', updateRadius)
    }

    void initialize()
    return () => {
      cancelled = true
      if (updateRadius) map.off('zoomend', updateRadius)
      if (layer) map.removeLayer(layer)
      layerRef.current = null
    }
  }, [map, visible])

  useEffect(() => {
    if (!visible || !layerRef.current) return
    const animationFrame = window.requestAnimationFrame(() => {
      layerRef.current?.setLatLngs(frame)
    })
    return () => window.cancelAnimationFrame(animationFrame)
  }, [frame, visible])

  return null
}

export const MapView = memo(function MapView({
  data,
  selectedRouteId,
  hoveredMile,
  onCheckpointHover,
  heatmapHour,
  showHeatmap,
}: MapViewProps) {
  const fallbackCenter = useMemo<[number, number]>(() => [38.5, -94.5], [])
  const selectedRoute = useMemo(
    () => data?.routes.find((route) => route.id === selectedRouteId) ?? null,
    [data, selectedRouteId],
  )
  const frame = data?.heatmap.frames[heatmapHour] ?? emptyFrame
  return (
    <div className="absolute inset-0 h-full w-full max-[700px]:min-h-[590px]">
      <MapContainer center={fallbackCenter} zoom={4} scrollWheelZoom preferCanvas={routeOptions.preferCanvas} className="absolute inset-0 h-full w-full">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {data && (
          <>
            <FitRoutes routes={data.routes} />
            <HeatmapLayer frame={frame} visible={showHeatmap} />
            <RouteLines routes={data.routes} selectedRouteId={selectedRouteId} recommendedRouteId={data.recommended_route_id} />
            <TripMarkers routes={data.routes} />
            {selectedRoute && (
              <CheckpointMarkers checkpoints={selectedRoute.checkpoints} hoveredMile={hoveredMile} onHover={onCheckpointHover} />
            )}
          </>
        )}
      </MapContainer>
      <MapLegend />
      {!data && <MapEmptyState />}
    </div>
  )
})

function heatRadius(zoom: number): number {
  if (zoom <= 5) return 18
  if (zoom <= 7) return 25
  return 35
}

function heatBlur(zoom: number): number {
  return Math.round(heatRadius(zoom) * 0.75)
}

function MapLegend() {
  return (
    <div className="absolute left-5 top-5 z-[500] w-[183px] rounded-[9px] border border-[#e4ebe5]/90 bg-white/95 px-[14px] pb-3 pt-[13px] shadow-[0_4px_18px_rgb(30_45_34_/_9%)] max-[900px]:left-[14px] max-[900px]:top-[14px] max-[900px]:scale-[0.92] max-[900px]:origin-top-left max-[700px]:left-3 max-[700px]:top-3 max-[700px]:scale-[0.88]" aria-label="Map legend">
      <p className="mb-[10px] text-[10px] font-extrabold tracking-[1.2px] text-[#8a968e]">MAP KEY</p>
      <div className="flex flex-col gap-[7px] border-b border-[#edf0ed] pb-[10px]">
        <span className="flex items-center gap-[7px] text-[11px] capitalize text-[#58675e]"><i className="h-[3px] w-5 rounded-sm bg-[repeating-linear-gradient(90deg,#17815b_0_6px,transparent_6px_9px)]" /> Recommended</span>
        <span className="flex items-center gap-[7px] text-[11px] capitalize text-[#58675e]"><i className="h-[3px] w-5 rounded-sm bg-[#62759a]" /> Alternate</span>
      </div>
      <div className="grid grid-cols-2 gap-x-1 gap-y-2 pt-[10px]">
        {(['low', 'moderate', 'high', 'severe', 'no_travel'] as RiskLevel[]).map((risk) => (
          <span className="flex items-center gap-[5px] text-[10px] capitalize text-[#58675e]" key={risk}><i className="size-[7px] shrink-0 rounded-full" style={{ backgroundColor: riskColors[risk] }} />{risk.replace('_', ' ')}</span>
        ))}
      </div>
    </div>
  )
}

function MapEmptyState() {
  return (
    <div className="absolute left-1/2 top-1/2 z-[400] w-[min(300px,calc(100%_-_40px))] -translate-x-1/2 -translate-y-1/2 rounded-xl border border-[#e2e9e3] bg-white/95 px-[23px] pb-5 pt-6 text-center shadow-[0_8px_35px_rgb(33_52_38_/_13%)]">
      <div className="mx-auto mb-3 grid size-10 place-items-center rounded-xl bg-[#e8f3eb] text-[23px] text-[#24784f]" aria-hidden="true">⌖</div>
      <p className="mb-[7px] font-heading text-base font-extrabold text-[#2a3930]">Your route, at a glance</p>
      <p className="mb-0 text-xs leading-[1.5] text-[#7a877e]">Enter your trip details to see weather-aware routes and conditions along the way.</p>
      <div className="mt-[17px] flex items-center justify-center gap-[7px] border-t border-[#edf0ed] pt-3 text-[10px] font-bold tracking-[0.9px] text-[#829087]"><span className="size-1.5 rounded-full bg-[#45a06d]" /> LIVE WEATHER LAYERS</div>
    </div>
  )
}
