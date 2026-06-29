import React from 'react'
import { CheckCircle2, Eye, Play } from 'lucide-react'
import Badge from './Badge'

export default function ActionCard({ action, checked, onToggle, onPreview }) {
  return (
    <label className="block cursor-pointer rounded-[22px] border border-slate-200 bg-white p-4 shadow-sm transition hover:border-slate-300 hover:bg-slate-50">
      <div className="flex items-start gap-3">
        <input
          type="checkbox"
          className="mt-1 h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
          checked={checked}
          onChange={onToggle}
        />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h4 className="text-sm font-semibold text-slate-900">{action.title || action.label || 'Acción sugerida'}</h4>
            <Badge severity={action.severity || 'info'}>{action.severity || 'info'}</Badge>
          </div>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            {action.description || action.detail || action.message || 'Sin descripción.'}
          </p>

          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault()
                onPreview?.(action)
              }}
              className="inline-flex items-center rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
            >
              <Eye className="mr-2 h-4 w-4" /> Vista previa
            </button>
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault()
                onToggle?.(e)
              }}
              className="inline-flex items-center rounded-xl bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700"
            >
              <CheckCircle2 className="mr-2 h-4 w-4" /> {checked ? 'Seleccionada' : 'Seleccionar'}
            </button>
          </div>
        </div>
      </div>
    </label>
  )
}
