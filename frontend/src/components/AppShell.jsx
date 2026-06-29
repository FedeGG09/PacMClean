import React from 'react'
import { Database, Sparkles, ShieldCheck, Activity, History, FileDown } from 'lucide-react'

const items = [
  { key: 'analyze', label: 'Análisis', icon: Sparkles },
  { key: 'actions', label: 'Acciones', icon: ShieldCheck },
  { key: 'comparison', label: 'Comparación', icon: Activity },
  { key: 'batch', label: 'Batch', icon: Database },
  { key: 'powerbi', label: 'Power BI', icon: FileDown },
  { key: 'history', label: 'Historial', icon: History },
]

export default function AppShell({ activeTab, setActiveTab, children, health }) {
  return (
    <div className="min-h-screen text-slate-900">
      <header className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-[1600px] items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-brand-600 text-white shadow-soft">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <div className="text-sm font-semibold uppercase tracking-[0.22em] text-brand-700">
                Evaluador de Calidad de Datos
              </div>
              <div className="text-xs text-slate-500">
                Diagnóstico determinista + acciones aplicables + exportación
              </div>
            </div>
          </div>

          <div className="hidden items-center gap-3 md:flex">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-2 text-sm text-slate-600">
              API: <span className="font-medium text-slate-900">{health ? 'Online' : 'Verificando...'}</span>
            </div>
            <button
              className="rounded-2xl bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white shadow-soft transition hover:bg-brand-700"
              onClick={() => setActiveTab('analyze')}
            >
              Nuevo análisis
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-[1600px] px-4 py-4 sm:px-6 lg:px-8">
        <nav className="mb-5 flex gap-2 overflow-x-auto rounded-3xl border border-slate-200 bg-white p-2 shadow-soft lg:hidden">
          {items.map(({ key, label, icon: Icon }) => {
            const active = activeTab === key
            return (
              <button
                key={key}
                onClick={() => setActiveTab(key)}
                className={[
                  'flex shrink-0 items-center gap-2 rounded-2xl px-4 py-2.5 text-sm font-medium transition',
                  active
                    ? 'bg-brand-50 text-brand-700 ring-1 ring-brand-100'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900',
                ].join(' ')}
              >
                <Icon className="h-4 w-4" />
                {label}
              </button>
            )
          })}
        </nav>

        <div className="flex gap-6">
        <aside className="hidden w-[250px] shrink-0 lg:block">
          <nav className="sticky top-24 space-y-2 rounded-3xl border border-slate-200 bg-white p-3 shadow-soft">
            {items.map(({ key, label, icon: Icon }) => {
              const active = activeTab === key
              return (
                <button
                  key={key}
                  onClick={() => setActiveTab(key)}
                  className={[
                    'flex w-full items-center gap-3 rounded-2xl px-4 py-3 text-left text-sm font-medium transition',
                    active
                      ? 'bg-brand-50 text-brand-700 ring-1 ring-brand-100'
                      : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900',
                  ].join(' ')}
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </button>
              )
            })}
          </nav>
        </aside>

        <main className="min-w-0 flex-1">{children}</main>
        </div>
      </div>
    </div>
  )
}
