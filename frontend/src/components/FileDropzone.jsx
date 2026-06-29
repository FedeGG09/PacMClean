import React, { useRef, useState } from 'react'
import { Upload, FileSpreadsheet } from 'lucide-react'

export default function FileDropzone({
  label,
  description,
  file,
  onChange,
  accept = '.csv,.xlsx,.xls',
}) {
  const inputRef = useRef(null)
  const [dragging, setDragging] = useState(false)

  const handleFiles = (files) => {
    const picked = files?.[0]
    if (picked) onChange(picked)
  }

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault()
        setDragging(false)
        handleFiles(e.dataTransfer.files)
      }}
      className={[
        'rounded-[24px] border border-dashed p-4 transition',
        dragging ? 'border-brand-300 bg-brand-50' : 'border-slate-200 bg-slate-50/70',
      ].join(' ')}
    >
      <div className="flex items-start gap-3">
        <div className="rounded-2xl bg-white p-3 text-brand-700 shadow-sm">
          <FileSpreadsheet className="h-5 w-5" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-sm font-semibold text-slate-900">{label}</div>
          <div className="mt-1 text-sm leading-6 text-slate-500">{description}</div>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <button
              type="button"
              className="rounded-2xl bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white shadow-soft hover:bg-brand-700"
              onClick={() => inputRef.current?.click()}
            >
              <Upload className="mr-2 inline h-4 w-4" />
              Seleccionar archivo
            </button>
            <div className="text-sm text-slate-500">
              {file ? (
                <span className="font-medium text-slate-900">{file.name}</span>
              ) : (
                'Sin archivo seleccionado'
              )}
            </div>
          </div>
        </div>
      </div>

      <input
        ref={inputRef}
        type="file"
        className="hidden"
        accept={accept}
        onChange={(e) => handleFiles(e.target.files)}
      />
    </div>
  )
}
