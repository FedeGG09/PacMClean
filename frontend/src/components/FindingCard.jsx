import React from 'react'
import { ChevronRight, Info, TriangleAlert } from 'lucide-react'
import Badge from './Badge'

export default function FindingCard({ finding, active, onSelect }) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={[
        'w-full rounded-[22px] border p-4 text-left transition',
        active ? 'border-brand-300 bg-brand-50 shadow-sm' : 'border-slate-200 bg-white hover:bg-slate-50',
      ].join(' ')}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Badge severity={finding.severity || 'info'}>{finding.severity || 'info'}</Badge>
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">{finding.type || 'Hallazgo'}</span>
          </div>
          <h4 className="mt-3 truncate text-base font-semibold text-slate-900">
            {finding.title || finding.message || finding.column || 'Sin título'}
          </h4>
          <p className="mt-1 max-h-12 overflow-hidden text-sm leading-6 text-slate-600">
            {finding.message || finding.description || 'Sin descripción.'}
          </p>
        </div>

        <div className="flex shrink-0 flex-col items-end gap-2">
          <div className="text-sm font-bold text-slate-900">
            {finding.count ?? finding.metric ?? '—'}
          </div>
          <ChevronRight className="h-4 w-4 text-slate-400" />
        </div>
      </div>

      <div className="mt-4 flex items-center gap-2 text-xs text-slate-500">
        {finding.column ? <span className="rounded-full bg-slate-100 px-2.5 py-1">{finding.column}</span> : null}
        {finding.risk ? (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-1 text-amber-700">
            <TriangleAlert className="h-3.5 w-3.5" /> {finding.risk}
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1">
            <Info className="h-3.5 w-3.5" /> Detalle disponible
          </span>
        )}
      </div>
    </button>
  )
}
