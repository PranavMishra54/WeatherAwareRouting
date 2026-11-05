import { memo, useEffect, useMemo, useState } from 'react'
import type { CSSProperties } from 'react'
import type { Heatmap } from '../types'
import { formatLocalDateTime } from '../utils/format'

interface ForecastSliderProps {
  heatmap: Heatmap
  hour: number
  onChange: (hour: number) => void
  heatmapVisible: boolean
  onToggleHeatmap: () => void
}

export const ForecastSlider = memo(function ForecastSlider({
  heatmap,
  hour,
  onChange,
  heatmapVisible,
  onToggleHeatmap,
}: ForecastSliderProps) {
  const [playing, setPlaying] = useState(false)
  const available = Boolean(heatmap.start_time && heatmap.frames.length)
  const forecastTime = useMemo(() => {
    if (!heatmap.start_time) return ''
    const time = new Date(new Date(heatmap.start_time).getTime() + hour * 3_600_000)
    return formatLocalDateTime(time.toISOString())
  }, [heatmap.start_time, hour])

  useEffect(() => {
    if (!playing || !available) return
    if (hour >= 48) {
      setPlaying(false)
      return
    }
    const timer = window.setInterval(() => {
      onChange(hour + 1)
    }, 400)
    return () => window.clearInterval(timer)
  }, [available, hour, onChange, playing])

  return (
    <div className="rounded-[10px] border border-[#e4ebe5]/95 bg-white/95 px-[19px] pb-[13px] pt-[15px] shadow-[0_5px_24px_rgb(30_45_34_/_13%)] backdrop-blur-lg max-[420px]:px-[13px]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="mb-1.5 text-[10px] font-bold leading-tight tracking-[1.25px] text-[#8a9690]">WEATHER FORECAST</p>
          {available
            ? <p className="mb-0 text-sm font-bold text-[#2c3b32]">{forecastTime} <span className="ml-[5px] text-xs font-semibold text-[#438565]">+{hour} h</span></p>
            : <p className="mb-0 text-sm font-bold text-[#8d4942]">Heatmap unavailable</p>}
        </div>
        <div className="flex items-center gap-2">
          <button
            className="rounded border border-[#e0e8e1] px-2 py-1 text-[11px] font-semibold text-[#4c5d52] disabled:cursor-not-allowed disabled:opacity-50"
            type="button"
            onClick={() => setPlaying((value) => !value)}
            disabled={!available}
            aria-label={playing ? 'Pause heatmap playback' : 'Play heatmap'}
          >
            {playing ? 'Pause' : 'Play'}
          </button>
          <button className="flex items-center gap-[7px] whitespace-nowrap bg-transparent py-1 pl-[5px] text-[11px] font-semibold text-[#738078] disabled:cursor-not-allowed disabled:opacity-50" type="button" onClick={onToggleHeatmap} aria-pressed={heatmapVisible} disabled={!available}>
          <span className={`flex h-[15px] w-[27px] items-center rounded-xl p-0.5 transition ${heatmapVisible ? 'bg-[#27845c]' : 'bg-[#cbd4cd]'}`}><span className={`size-[11px] rounded-full bg-white shadow-sm transition ${heatmapVisible ? 'translate-x-3' : ''}`} /></span>
          Weather layer
          </button>
        </div>
      </div>
      <label className="sr-only" htmlFor="forecast-hour">Forecast hour</label>
      <div className="mt-3 flex items-center gap-2.5 text-[10px] font-bold tracking-[0.4px] text-[#99a39c]">
        <span aria-hidden="true">NOW</span>
        <input className="h-[5px] w-full cursor-pointer appearance-none rounded-full bg-[linear-gradient(to_right,#31855d_var(--slider-progress),#e3e9e4_var(--slider-progress))] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#5bab84] disabled:cursor-not-allowed [&::-webkit-slider-thumb]:size-[14px] [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:border-[3px] [&::-webkit-slider-thumb]:border-[#28845a] [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:shadow-[0_1px_4px_rgb(0_0_0_/_20%)] [&::-moz-range-thumb]:size-[10px] [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:border-[3px] [&::-moz-range-thumb]:border-[#28845a] [&::-moz-range-thumb]:bg-white" id="forecast-hour" type="range" min="0" max="48" step="1" value={hour} disabled={!available} onChange={(event) => onChange(Number(event.target.value))} aria-valuetext={`${hour} hours after departure`} style={{ '--slider-progress': `${(hour / 48) * 100}%` } as CSSProperties} />
        <span>48 h</span>
      </div>
    </div>
  )
})
