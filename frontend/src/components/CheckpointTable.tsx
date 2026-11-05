import { memo } from 'react'
import type { Route } from '../types'
import { formatLocalDateTime } from '../utils/format'
import { RiskBadge } from './RiskBadge'

interface CheckpointTableProps {
  route: Route
  hoveredMile: number | null
  onHover: (mile: number | null) => void
}

export const CheckpointTable = memo(function CheckpointTable({
  route,
  hoveredMile,
  onHover,
}: CheckpointTableProps) {
  return (
    <section className="mt-[23px]" aria-labelledby="checkpoint-title">
      <div className="mb-[11px] flex items-end justify-between gap-3">
        <div>
          <p className="mb-1.5 text-[10px] font-bold leading-tight tracking-[1.25px] text-[#8a9690]">ON-ROAD CONDITIONS</p>
          <h2 id="checkpoint-title" className="m-0 font-heading text-[19px] font-bold tracking-[-0.6px] text-[#1d2b24]">Checkpoints <span className="ml-1 font-sans text-xs font-semibold text-[#92a097]">{route.checkpoints.length}</span></h2>
        </div>
        <span className="text-[11px] text-[#929e96]">Hover a row to locate</span>
      </div>
      <div className="max-h-[390px] overflow-auto rounded-[7px] border border-[#e8ede9] [scrollbar-color:#d7dfd9_transparent] [scrollbar-width:thin]">
        <table className="w-full border-separate border-spacing-0 text-[11px]">
          <thead className="sticky top-0 z-[1]">
            <tr>
              <th className="whitespace-nowrap border-b border-[#e5ebe6] bg-[#f5f8f5] px-[7px] py-[9px] text-left text-[10px] font-bold text-[#748178]" scope="col">Mile</th>
              <th className="whitespace-nowrap border-b border-[#e5ebe6] bg-[#f5f8f5] px-[7px] py-[9px] text-left text-[10px] font-bold text-[#748178]" scope="col">ETA</th>
              <th className="whitespace-nowrap border-b border-[#e5ebe6] bg-[#f5f8f5] px-[7px] py-[9px] text-left text-[10px] font-bold text-[#748178]" scope="col">Forecast</th>
              <th className="whitespace-nowrap border-b border-[#e5ebe6] bg-[#f5f8f5] px-[7px] py-[9px] text-left text-[10px] font-bold text-[#748178]" scope="col">Wind</th>
              <th className="whitespace-nowrap border-b border-[#e5ebe6] bg-[#f5f8f5] px-[7px] py-[9px] text-left text-[10px] font-bold text-[#748178]" scope="col">Rain</th>
              <th className="whitespace-nowrap border-b border-[#e5ebe6] bg-[#f5f8f5] px-[7px] py-[9px] text-left text-[10px] font-bold text-[#748178]" scope="col">Snow</th>
              <th className="whitespace-nowrap border-b border-[#e5ebe6] bg-[#f5f8f5] px-[7px] py-[9px] text-left text-[10px] font-bold text-[#748178]" scope="col">Risk &amp; outlook</th>
            </tr>
          </thead>
          <tbody>
            {route.checkpoints.map((checkpoint) => (
              <tr
                key={`${route.id}-${checkpoint.mile}`}
                className={hoveredMile === checkpoint.mile ? 'bg-[#eff8f1]' : 'hover:bg-[#eff8f1]'}
                onMouseEnter={() => onHover(checkpoint.mile)}
                onMouseLeave={() => onHover(null)}
                onFocus={() => onHover(checkpoint.mile)}
                onBlur={() => onHover(null)}
                tabIndex={0}
                aria-label={`Mile ${checkpoint.mile}, ${checkpoint.risk} risk`}
              >
                <td className="whitespace-nowrap border-b border-[#eef1ee] px-[7px] py-[9px] font-bold text-[#32443a]">{checkpoint.mile}</td>
                <td className="whitespace-nowrap border-b border-[#eef1ee] px-[7px] py-[9px] text-[#65736a]">{formatLocalDateTime(checkpoint.eta)}</td>
                <td className="whitespace-nowrap border-b border-[#eef1ee] px-[7px] py-[9px] text-[#65736a]">{formatLocalDateTime(checkpoint.forecast_time)}</td>
                <td className="whitespace-nowrap border-b border-[#eef1ee] px-[7px] py-[9px] text-[#65736a]">{checkpoint.wind_mph}<small className="text-[10px] text-[#98a39c]"> mph</small></td>
                <td className="whitespace-nowrap border-b border-[#eef1ee] px-[7px] py-[9px] text-[#65736a]">{checkpoint.rain_in_hr.toFixed(2)}<small className="text-[10px] text-[#98a39c]"> in</small></td>
                <td className="whitespace-nowrap border-b border-[#eef1ee] px-[7px] py-[9px] text-[#65736a]">{checkpoint.snow_in_hr.toFixed(2)}<small className="text-[10px] text-[#98a39c]"> in</small></td>
                <td className="min-w-[150px] border-b border-[#eef1ee] px-[7px] py-[9px] text-[#65736a]">
                  <RiskBadge risk={checkpoint.risk} />
                  <span className="ml-1.5 text-[10px] leading-[1.35] text-[#849087]">{checkpoint.reasons.join(' · ')}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
})
