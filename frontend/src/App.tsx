import { useCallback, useEffect, useMemo, useState } from 'react'
import { wakeBackend } from './api/client'
import { CheckpointTable } from './components/CheckpointTable'
import { ForecastSlider } from './components/ForecastSlider'
import { Header } from './components/Header'
import { MapView } from './components/MapView'
import { RouteCard } from './components/RouteCard'
import { TripForm } from './components/TripForm'
import { useAnalyze } from './hooks/useAnalyze'
import type { AnalyzeRequest } from './types'

function App() {
  const { data, error, loading, wakingUp, submit } = useAnalyze()
  const [selectedRouteId, setSelectedRouteId] = useState<number | null>(null)
  const [routeDetailsOpen, setRouteDetailsOpen] = useState(false)
  const [heatmapHour, setHeatmapHour] = useState(0)
  const [showHeatmap, setShowHeatmap] = useState(true)
  const [hoveredMile, setHoveredMile] = useState<number | null>(null)

  useEffect(() => {
    wakeBackend()
  }, [])

  const selectedRoute = useMemo(
    () => data?.routes.find((route) => route.id === selectedRouteId) ?? null,
    [data, selectedRouteId],
  )

  const handleSubmit = useCallback(
    async (request: AnalyzeRequest) => {
      const response = await submit(request)
      if (!response) return
      setSelectedRouteId(response.recommended_route_id)
      setRouteDetailsOpen(false)
      setHeatmapHour(0)
      setHoveredMile(null)
    },
    [submit],
  )

  const handleRouteSelect = (routeId: number) => {
    setSelectedRouteId(routeId)
    setRouteDetailsOpen(true)
    setHeatmapHour(0)
    setHoveredMile(null)
  }

  return (
    <main className="grid h-dvh min-h-0 grid-cols-[minmax(350px,390px)_minmax(0,1fr)] overflow-hidden bg-[#f5f7f5] max-[900px]:grid-cols-[minmax(330px,370px)_minmax(0,1fr)] max-[700px]:flex max-[700px]:flex-col">
      <aside className="z-10 flex h-full min-h-0 flex-col border-r border-[#e8ede9] bg-white shadow-[8px_0_28px_rgb(23_35_31_/_4%)] max-[700px]:h-[58dvh] max-[700px]:max-h-[58dvh] max-[700px]:shrink-0 max-[700px]:border-r-0">
        <Header />
        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain [scrollbar-color:#d7dfd9_transparent] [scrollbar-width:thin]">
          {(!data || !routeDetailsOpen) && (
            <TripForm onSubmit={handleSubmit} loading={loading} error={error} />
          )}

          {loading && (
            <section className="space-y-3 border-b border-[#edf0ed] px-6 py-5 max-[900px]:px-[18px]" aria-label="Loading route analysis" aria-live="polite">
              <div className="flex items-center gap-2 text-xs font-semibold text-[#557362]">
                <span className="size-3.5 animate-spin rounded-full border-2 border-[#b8d5c1] border-t-[#27845c]" aria-hidden="true" />
                {wakingUp
                  ? 'Waking up the server, this can take up to a minute...'
                  : 'Analyzing routes and forecast…'}
              </div>
              {[0, 1, 2].map((item) => (
                <div className="animate-pulse rounded-lg border border-[#e8ede9] p-3" key={item}>
                  <div className="mb-2 h-3 w-2/5 rounded bg-[#edf1ed]" />
                  <div className="h-2.5 w-3/4 rounded bg-[#f1f4f1]" />
                </div>
              ))}
            </section>
          )}

          {data && !routeDetailsOpen && (
            <section className="border-b border-[#edf0ed] px-6 py-[21px] max-[900px]:px-[18px] max-[420px]:px-[15px]" aria-labelledby="results-title">
              <div className="mb-[13px] flex items-center justify-between gap-3">
                <div>
                  <p className="mb-1.5 text-[10px] font-bold leading-tight tracking-[1.25px] text-[#8a9690]">ROUTE ANALYSIS</p>
                  <h2 id="results-title" className="m-0 font-heading text-[19px] font-bold tracking-[-0.6px] text-[#1d2b24]">Your routes</h2>
                </div>
                <span className="rounded bg-[#f2f5f2] px-2 py-[5px] text-xs font-semibold text-[#77857c]">{data.routes.length} options</span>
              </div>

              <div className="flex flex-col gap-[9px]">
                {data.routes.map((route) => (
                  <RouteCard
                    key={route.id}
                    route={route}
                    recommended={route.id === data.recommended_route_id}
                    selected={route.id === selectedRouteId}
                    onSelect={handleRouteSelect}
                  />
                ))}
              </div>

            </section>
          )}
          {data && routeDetailsOpen && selectedRoute && (
            <section className="px-6 py-[21px] max-[900px]:px-[18px] max-[420px]:px-[15px]" aria-labelledby="route-details-title">
              <button
                className="mb-5 border-0 bg-transparent p-0 text-xs font-semibold text-[#277d56] hover:text-[#175b3d]"
                type="button"
                onClick={() => setRouteDetailsOpen(false)}
              >
                All routes
              </button>
              <h2 id="route-details-title" className="mb-4 mt-0 font-heading text-[19px] font-bold text-[#1d2b24]">
                Route {selectedRoute.id + 1} details
              </h2>
              <ForecastSlider
                heatmap={data.heatmap}
                hour={heatmapHour}
                onChange={setHeatmapHour}
                heatmapVisible={showHeatmap}
                onToggleHeatmap={() => setShowHeatmap((visible) => !visible)}
              />
              <CheckpointTable
                route={selectedRoute}
                hoveredMile={hoveredMile}
                onHover={setHoveredMile}
              />
            </section>
          )}
          {!data && !loading && (
            <div className="px-6 py-6 text-center text-sm leading-relaxed text-[#7a877e] max-[900px]:px-[18px]">
              Enter your trip details to compare weather-aware routes.
            </div>
          )}
        </div>
      </aside>

      <section className="relative min-h-0 min-w-0 bg-[#e8eee8] max-[700px]:min-h-0 max-[700px]:flex-1" aria-label="Route map">
        <MapView
          data={data}
          selectedRouteId={selectedRouteId}
          hoveredMile={hoveredMile}
          onCheckpointHover={setHoveredMile}
          heatmapHour={heatmapHour}
          showHeatmap={showHeatmap}
        />
      </section>
    </main>
  )
}

export default App
