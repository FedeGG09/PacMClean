import React from 'react'

export default function SectionCard({ title, subtitle, children, className = '' , right }) {
  return (
    <section className={`rounded-[28px] border border-slate-200 bg-white shadow-soft ${className}`}>
      <div className="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-5 sm:px-7">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">{title}</h2>
          {subtitle ? <p className="mt-1 text-sm leading-6 text-slate-500">{subtitle}</p> : null}
        </div>
        {right}
      </div>
      <div className="px-6 py-6 sm:px-7">{children}</div>
    </section>
  )
}
