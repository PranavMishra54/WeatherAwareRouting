import { useState, type FormEvent } from 'react'
import type { AnalyzeRequest, IntervalMiles } from '../types'
import { toDateTimeLocalValue } from '../utils/formatters'

interface TripFormProps {
  onSubmit: (request: AnalyzeRequest) => Promise<void>
  loading: boolean
  error: string | null
}

export function TripForm({ onSubmit, loading, error }: TripFormProps) {
  const [origin, setOrigin] = useState('Chicago, IL')
  const [destination, setDestination] = useState('Dallas, TX')
  const [departureTime, setDepartureTime] = useState(() => toDateTimeLocalValue(new Date(Date.now() + 60 * 60_000)))
  const [weight, setWeight] = useState('40000')
  const [interval, setInterval] = useState<IntervalMiles>(25)
  const [errors, setErrors] = useState<Record<string, string>>({})

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const nextErrors: Record<string, string> = {}
    if (!origin.trim()) nextErrors.origin = 'Enter a starting location.'
    if (!destination.trim()) nextErrors.destination = 'Enter a destination.'
    if (!departureTime || Number.isNaN(new Date(departureTime).getTime())) {
      nextErrors.departureTime = 'Choose a valid departure date and time.'
    }
    const parsedWeight = Number(weight)
    if (!Number.isInteger(parsedWeight) || parsedWeight < 1 || parsedWeight > 150000) {
      nextErrors.weight = 'Load weight must be a whole number from 1 to 150,000 lb.'
    }
    if (origin.trim().toLowerCase() === destination.trim().toLowerCase()) {
      nextErrors.destination = 'Origin and destination must be different.'
    }
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) return

    try {
      await onSubmit({
        origin: origin.trim(),
        destination: destination.trim(),
        departure_time: new Date(departureTime).toISOString(),
        load_weight_lb: parsedWeight,
        interval_miles: interval,
      })
    } catch {
      // The API error is displayed in the persistent form banner.
    }
  }

  return (
    <section className="border-b border-[#edf0ed] px-6 pb-[23px] pt-[25px] max-[900px]:px-[18px] max-[700px]:pt-[21px] max-[420px]:px-[15px]" aria-labelledby="trip-title">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="mb-1.5 text-[10px] font-bold leading-tight tracking-[1.25px] text-[#8a9690]">PLAN YOUR DRIVE</p>
          <h1 id="trip-title" className="m-0 font-heading text-[22px] font-bold leading-[1.3] tracking-[-0.6px] text-[#1d2b24]">Build a safer trip</h1>
        </div>
        <span className="rounded bg-[#eff7f1] px-2 py-[5px] text-[11px] font-bold text-[#1b7952]">01 <span className="font-medium text-[#98aa9e]">/ 01</span></span>
      </div>
      <p className="mb-5 mt-2 max-w-[290px] text-sm leading-[1.5] text-[#76827c]">Compare truck-ready routes with weather conditions along the way.</p>

      <form className="flex flex-col gap-3.5" onSubmit={handleSubmit} noValidate>
        <div className="grid grid-cols-2 gap-[11px] max-[420px]:gap-2">
          <div className="flex min-w-0 flex-col gap-1.5">
            <label className="text-xs font-bold text-[#49574f]" htmlFor="origin">Starting point</label>
            <div className="relative">
              <span className="absolute left-[11px] top-1/2 z-[1] size-[9px] -translate-y-1/2 rounded-full border-2 border-[#338961]" aria-hidden="true" />
              <input className={`h-[42px] w-full min-w-0 rounded-[7px] border bg-white py-0 pl-[29px] pr-[10px] text-[13px] text-[#27352d] placeholder:text-[#a4ada8] focus:border-[#55a47c] focus:shadow-[0_0_0_3px_rgb(45_144_93_/_10%)] focus:outline-none max-[420px]:text-xs ${errors.origin ? 'border-[#d6584e]' : 'border-[#dfe6e1]'}`} id="origin" value={origin} onChange={(event) => setOrigin(event.target.value)} aria-invalid={Boolean(errors.origin)} aria-describedby={errors.origin ? 'origin-error' : undefined} placeholder="City, state" />
            </div>
            {errors.origin && <span className="text-xs leading-[1.3] text-[#b7433c]" id="origin-error">{errors.origin}</span>}
          </div>
          <div className="flex min-w-0 flex-col gap-1.5">
            <label className="text-xs font-bold text-[#49574f]" htmlFor="destination">Destination</label>
            <div className="relative">
              <span className="absolute left-[11px] top-1/2 z-[1] size-[9px] -translate-y-1/2 rounded-sm border-2 border-[#d07b37]" aria-hidden="true" />
              <input className={`h-[42px] w-full min-w-0 rounded-[7px] border bg-white py-0 pl-[29px] pr-[10px] text-[13px] text-[#27352d] placeholder:text-[#a4ada8] focus:border-[#55a47c] focus:shadow-[0_0_0_3px_rgb(45_144_93_/_10%)] focus:outline-none max-[420px]:text-xs ${errors.destination ? 'border-[#d6584e]' : 'border-[#dfe6e1]'}`} id="destination" value={destination} onChange={(event) => setDestination(event.target.value)} aria-invalid={Boolean(errors.destination)} aria-describedby={errors.destination ? 'destination-error' : undefined} placeholder="City, state" />
            </div>
            {errors.destination && <span className="text-xs leading-[1.3] text-[#b7433c]" id="destination-error">{errors.destination}</span>}
          </div>
        </div>

        <div className="flex min-w-0 flex-col gap-1.5">
          <label className="text-xs font-bold text-[#49574f]" htmlFor="departure">Departure date &amp; time</label>
          <input className={`h-[42px] w-full min-w-0 rounded-[7px] border bg-white px-[10px] text-[13px] text-[#27352d] focus:border-[#55a47c] focus:shadow-[0_0_0_3px_rgb(45_144_93_/_10%)] focus:outline-none ${errors.departureTime ? 'border-[#d6584e]' : 'border-[#dfe6e1]'}`} id="departure" type="datetime-local" value={departureTime} onChange={(event) => setDepartureTime(event.target.value)} aria-invalid={Boolean(errors.departureTime)} aria-describedby={errors.departureTime ? 'departure-error' : undefined} />
          {errors.departureTime && <span className="text-xs leading-[1.3] text-[#b7433c]" id="departure-error">{errors.departureTime}</span>}
        </div>

        <div className="grid grid-cols-2 gap-[11px] max-[420px]:gap-2">
          <div className="flex min-w-0 flex-col gap-1.5">
            <label className="text-xs font-bold text-[#49574f]" htmlFor="weight">Load weight</label>
            <div className="relative">
              <input className={`h-[42px] w-full min-w-0 rounded-[7px] border bg-white py-0 pl-[10px] pr-[31px] text-[13px] text-[#27352d] focus:border-[#55a47c] focus:shadow-[0_0_0_3px_rgb(45_144_93_/_10%)] focus:outline-none max-[420px]:text-xs ${errors.weight ? 'border-[#d6584e]' : 'border-[#dfe6e1]'}`} id="weight" type="number" min="1" max="150000" step="1" value={weight} onChange={(event) => setWeight(event.target.value)} aria-invalid={Boolean(errors.weight)} aria-describedby={errors.weight ? 'weight-error' : undefined} />
              <span className="absolute right-[10px] top-1/2 -translate-y-1/2 text-xs text-[#89958e]">lb</span>
            </div>
            {errors.weight && <span className="text-xs leading-[1.3] text-[#b7433c]" id="weight-error">{errors.weight}</span>}
          </div>
          <div className="flex min-w-0 flex-col gap-1.5">
            <label className="text-xs font-bold text-[#49574f]" htmlFor="interval">Checkpoint interval</label>
            <div className="relative">
              <select className="h-[42px] w-full min-w-0 cursor-pointer appearance-none rounded-[7px] border border-[#dfe6e1] bg-white py-0 pl-[10px] pr-[27px] text-[13px] text-[#27352d] focus:border-[#55a47c] focus:shadow-[0_0_0_3px_rgb(45_144_93_/_10%)] focus:outline-none max-[420px]:text-xs" id="interval" value={interval} onChange={(event) => setInterval(Number(event.target.value) as IntervalMiles)}>
                <option value={10}>Every 10 miles</option>
                <option value={25}>Every 25 miles</option>
                <option value={50}>Every 50 miles</option>
              </select>
              <span className="pointer-events-none absolute right-[11px] top-1/2 size-1.5 -translate-y-[70%] rotate-45 border-b-[1.5px] border-r-[1.5px] border-[#69766e]" />
            </div>
          </div>
        </div>

        {error && <div className="flex items-start gap-[9px] rounded-[7px] border border-[#f4d0cb] bg-[#fff1ef] px-[11px] py-[10px] text-[#8d342d]" role="alert"><span className="grid size-4 shrink-0 place-items-center rounded-full bg-[#c7584e] text-xs font-bold text-white" aria-hidden="true">!</span><p className="mb-0 mt-px text-[13px] leading-[1.4]">{error}</p></div>}

        <button className="mt-px flex min-h-[44px] items-center justify-center gap-2.5 rounded-[7px] border-0 bg-[#13744c] text-sm font-bold text-white shadow-[0_3px_8px_rgb(19_116_76_/_16%)] transition hover:-translate-y-px hover:bg-[#0d603d]" type="submit">
          {loading ? <><span className="size-3.5 animate-spin rounded-full border-2 border-white/40 border-t-white" aria-hidden="true" /> Analyzing routes…</> : <>Analyze routes <span aria-hidden="true" className="text-base leading-none">→</span></>}
        </button>
      </form>
    </section>
  )
}
