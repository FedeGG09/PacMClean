import React from 'react'
import { Clock3, FileJson, FileSpreadsheet } from 'lucide-react'

export default function HistoryList({ items }) {
  if (!items?.length) {
    return (
      <div className="rounded-[22px] border border-dashed border-slate-200 bg-white p-5 text-sm text-slate-500">
        Todavía no hay ejecuciones en el historial.
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {items.map((item, idx) => (
        <div key={item.id ?? idx} className="rounded-[22px] border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
                <Clock3 className="h-3.5 w-3.5" />
                {item.created_at || item.date || 'Sin fecha'}
              </div>
              <h4 className="mt-2 text-sm font-semibold text-slate-900">{item.title || item.dataset_name || 'Ejecución'}</h4>
              <p className="mt-1 text-sm text-slate-600">{item.message || item.summary || 'Sin descripción.'}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {item.run_id ? (
                <>
                  <a className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50" href={item.report_json_url || '#'} target="_blank" rel="noreferrer">
                    <FileJson className="mr-2 inline h-4 w-4" /> JSON
                  </a>
                  <a className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50" href={item.cleaned_csv_url || '#'} target="_blank" rel="noreferrer">
                    <FileSpreadsheet className="mr-2 inline h-4 w-4" /> CSV
                  </a>
                </>
              ) : null}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
