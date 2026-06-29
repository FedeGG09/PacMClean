import React from 'react'

const styles = {
  high: 'border-red-200 bg-red-50 text-red-700',
  medium: 'border-amber-200 bg-amber-50 text-amber-700',
  low: 'border-sky-200 bg-sky-50 text-sky-700',
  info: 'border-slate-200 bg-slate-50 text-slate-700',
}

export default function Badge({ severity = 'info', children, className = '' }) {
  return (
    <span
      className={[
        'inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold capitalize',
        styles[severity] || styles.info,
        className,
      ].join(' ')}
    >
      {children}
    </span>
  )
}
