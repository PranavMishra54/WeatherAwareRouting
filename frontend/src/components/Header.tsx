export function Header() {
  return (
    <header className="flex h-[75px] items-center gap-[11px] border-b border-[#edf0ed] px-[25px] max-[900px]:px-[18px] max-[700px]:h-[66px]">
      <div className="grid size-[38px] place-items-center rounded-xl bg-[#e8f4ed] text-[#0e714b]" aria-hidden="true">
        <svg className="size-[27px]" viewBox="0 0 32 32" fill="none">
          <path d="M5 22.5 12.5 10l5.2 8.3 3.2-5 6.1 9.2H5Z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
          <path d="M20.5 6.5v4m-2-2h4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        </svg>
      </div>
      <div>
        <p className="m-0 font-heading text-[17px] font-extrabold leading-[1.15] tracking-[-0.5px] text-[#1b2922]">WeatherAware</p>
        <p className="mb-0 mt-1 text-[10px] font-bold tracking-[1.2px] text-[#87918b]">TRUCK ROUTING</p>
      </div>
      <span className="ml-auto flex items-center gap-1.5 whitespace-nowrap text-[11px] font-semibold text-[#6d7d73]"><span className="size-1.5 rounded-full bg-[#44a274] shadow-[0_0_0_3px_#e6f4eb]" /> Forecast ready</span>
    </header>
  )
}
