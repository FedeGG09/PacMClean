import React from 'react'

export default function MetricCard({ label, value, hint, accent = false }) {
  return (
    <div className={[
      'rounded-[22px] border p-5',
      accent
        ? 'border-brand-100 bg-gradient-to-br from-brand-50 to-white'
        : 'border-slate-200 bg-white'
    ].join(' ')}>
      <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</div>
      <div className="mt-3 text-3xl font-bold text-slate-900">{value}</div>
      {hint ? <div className="mt-1 text-sm text-slate-500">{hint}</div> : null}
    </div>
  )
}
