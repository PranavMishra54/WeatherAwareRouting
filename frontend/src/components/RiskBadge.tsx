import type { RiskLevel } from '../types'

const labels: Record<RiskLevel, string> = {
  low: 'Low',
  moderate: 'Moderate',
  high: 'High',
  severe: 'Severe',
  no_travel: 'No travel',
}

const colors: Record<RiskLevel, string> = {
  low: 'border-[#d3ead9] bg-[#e7f4eb] text-[#167447]',
  moderate: 'border-[#f1e4b7] bg-[#fff6d8] text-[#8a6800]',
  high: 'border-[#f2d8be] bg-[#fff0e2] text-[#a84c0b]',
  severe: 'border-[#f1cfcd] bg-[#fde9e8] text-[#a63131]',
  no_travel: 'border-[#352444] bg-[#352444] text-white',
}

export function RiskBadge({ risk }: { risk: RiskLevel }) {
  return <span className={`inline-flex min-h-[22px] items-center whitespace-nowrap rounded border px-1.5 py-0.5 text-[11px] font-bold leading-none ${colors[risk]}`}>{labels[risk]}</span>
}
