import { memo } from 'react'
import type { Route } from '../types'
import { formatHours, formatMiles } from '../utils/formatters'
import { formatLocalDateTime } from '../utils/format'
import { RiskBadge } from './RiskBadge'

interface RouteCardProps {
  route: Route
  recommended: boolean
  selected: boolean
  onSelect: (routeId: number) => void
}

export const RouteCard = memo(function RouteCard({
  route,
  recommended,
  selected,
  onSelect,
}: RouteCardProps) {
  const routeColor = route.id % 3 === 0 ? 'bg-[#13845d]' : route.id % 3 === 1 ? 'bg-[#da8c38]' : 'bg-[#607ba9]'
  return (
    <button
      className={`relative flex w-full gap-[11px] rounded-[9px] border px-[11px] py-3 text-left text-inherit transition hover:border-[#b4d2bf] ${selected ? 'border-[#399268] bg-[#f8fcf8] shadow-[0_0_0_1px_rgb(57_146_104_/_9%)]' : 'border-[#e5eae6] bg-white'}`}
      type="button"
      aria-pressed={selected}
      onClick={() => onSelect(route.id)}
    >
      <span className={`w-[3px] shrink-0 self-stretch rounded-[5px] ${routeColor}`} aria-hidden="true" />
      <span className="flex min-w-0 flex-1 flex-col gap-[9px]">
        <span className="flex items-center justify-between gap-2">
          <span className="flex min-w-0 flex-col items-start gap-0.5">
            <span className="text-[13px] font-bold text-[#23332a]">Route {route.id + 1}</span>
            <span className="text-[11px] text-[#8a9690]">Weather-aware corridor</span>
          </span>
          {recommended && <span className="shrink-0 rounded bg-[#e8f5ec] px-1.5 py-1 text-[10px] font-extrabold tracking-[0.6px] text-[#147247]">BEST FIT</span>}
        </span>
        <span className="flex flex-wrap gap-x-3 gap-y-[7px] text-[11px] font-semibold text-[#5b6b61]">
          <span>{formatMiles(route.distance_miles)}</span>
          <span>{formatHours(route.duration_hours)}</span>
          <span>Arrive {formatLocalDateTime(route.arrival_time)}</span>
        </span>
        <span className="flex flex-wrap items-center gap-1.5">
          <RiskBadge risk={route.summary.max_risk} />
          <span className="whitespace-nowrap text-[10px] text-[#7c8981]"><b className="font-bold text-[#526158]">{route.summary.severe_miles}</b> severe mi</span>
          <span className="whitespace-nowrap text-[10px] text-[#7c8981]"><b className="font-bold text-[#526158]">{route.summary.high_miles}</b> high mi</span>
          {route.summary.no_travel_miles > 0 && <span className="whitespace-nowrap text-[10px] text-[#7c8981]"><b className="font-bold text-[#352444]">{route.summary.no_travel_miles}</b> no-travel mi</span>}
          <span className="whitespace-nowrap text-[10px] text-[#7c8981]">Avg <b className="font-bold text-[#526158]">{route.summary.avg_risk.toFixed(1)}</b>/5</span>
        </span>
        {recommended && <span className="border-t border-[#e7efe8] pt-[7px] text-[11px] leading-[1.4] text-[#53765f]">{route.recommendation_reason}</span>}
      </span>
    </button>
  )
})
