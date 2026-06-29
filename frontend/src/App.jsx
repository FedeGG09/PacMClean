import React, { useEffect, useMemo, useState } from 'react'
import { AlertCircle, ArrowRight, CheckCircle2, FileDown, Loader2, RefreshCw, ShieldCheck, Sparkles } from 'lucide-react'

import AppShell from './components/AppShell'
import SectionCard from './components/SectionCard'
import MetricCard from './components/MetricCard'
import Badge from './components/Badge'
import FileDropzone from './components/FileDropzone'
import FindingCard from './components/FindingCard'
import ActionCard from './components/ActionCard'
import HistoryList from './components/HistoryList'

import {
  analyzeDataset,
  applyActions,
  buildRunUrl,
  exportToPowerBI,
  getHealth,
  getHistory,
  runBatch,
} from './api'

function asArray(value) {
  if (Array.isArray(value)) return value
  if (typeof value === 'string' && value.trim()) {
    try {
      const parsed = JSON.parse(value)
      if (Array.isArray(parsed)) return parsed
    } catch {
      // ignore
    }
    return [value]
  }
  return []
}

function flattenText(value) {
  if (Array.isArray(value)) return value.map(flattenText).filter(Boolean).join('\n')
  if (value && typeof value === 'object') return JSON.stringify(value, null, 2)
  return String(value ?? '')
}

function normalizeFinding(item, idx) {
  const examples = asArray(item?.examples).length
    ? asArray(item.examples).map(flattenText)
    : asArray(item?.sample).map(flattenText)

  return {
    id: item?.id ?? `${item?.type ?? 'finding'}_${idx}`,
    type: item?.type ?? item?.category ?? 'finding',
    severity: item?.severity ?? 'info',
    title: item?.title ?? item?.message ?? item?.column ?? 'Hallazgo',
    column: item?.column ?? item?.field ?? '',
    count: item?.count ?? item?.n ?? item?.rows_affected ?? 0,
    metric: item?.metric ?? item?.score ?? null,
    message: item?.message ?? item?.description ?? '',
    examples,
    risk: item?.risk ?? item?.impact ?? '',
    action: item?.action ?? item?.suggested_action ?? '',
    raw: item,
  }
}

function normalizeAction(item, idx) {
  return {
    id: item?.id ?? item?.action_id ?? `action_${idx}`,
    title: item?.title ?? item?.label ?? item?.name ?? 'Acción sugerida',
    description: item?.description ?? item?.detail ?? item?.message ?? '',
    severity: item?.severity ?? 'info',
    column: item?.column ?? item?.target_column ?? '',
    risk: item?.risk ?? item?.impact ?? '',
    raw: item,
  }
}

function normalizeReport(report) {
  const root = report?.report ?? report ?? {}
  const findingsRaw =
    root.findings_display ??
    root.after_findings ??
    root.before_findings ??
    root.findings ??
    root.issues ??
    []

  const actionsRaw =
    root.actions ??
    root.available_actions ??
    root.suggested_actions ??
    root.recommended_actions ??
    []

  const recommendationsRaw = root.recommendations ?? root.llm_recommendations ?? root.summary_bullets ?? []

  const findings = findingsRaw.map(normalizeFinding)
  const actions = actionsRaw.map(normalizeAction)
  const recommendations = recommendationsRaw.map((r, idx) => ({
    id: r?.id ?? `rec_${idx}`,
    title: r?.title ?? r?.label ?? flattenText(r),
    detail: r?.detail ?? r?.description ?? r?.message ?? '',
    severity: r?.severity ?? 'info',
  }))

  const summary = root.summary ?? {}
  const score = root.score ?? summary.score ?? root.quality_score ?? 0
  const rows = root.rows ?? summary.rows ?? root.summary_rows ?? 0
  const columns = root.columns ?? summary.cols ?? root.summary_cols ?? 0
  const status = root.status ?? (score >= 85 ? 'Healthy with warnings' : 'Needs attention')
  const runId = root.run_id ?? root.runId ?? null

  return {
    raw: root,
    score,
    rows,
    columns,
    status,
    summaryText: root.summary_text ?? root.executive_summary ?? root.summary ?? '',
    findings,
    actions,
    recommendations,
    runId,
    reportHtmlUrl: runId ? buildRunUrl(runId, 'report.html') : root.report_html_url ?? null,
    reportPdfUrl: runId ? buildRunUrl(runId, 'report.pdf') : root.report_pdf_url ?? null,
    reportJsonUrl: runId ? buildRunUrl(runId, 'report.json') : root.report_json_url ?? null,
    cleanedCsvUrl: runId ? buildRunUrl(runId, 'cleaned.csv') : root.cleaned_csv_url ?? null,
    cleanedXlsxUrl: runId ? buildRunUrl(runId, 'cleaned.xlsx') : root.cleaned_xlsx_url ?? null,
    message: root.message ?? '',
    datasetName: root.dataset_name ?? root.filename ?? '',
    previousScore: root.previous_score ?? null,
    nextScore: root.next_score ?? null,
  }
}

function downloadUrl(url) {
  if (!url) return
  window.open(url, '_blank', 'noopener,noreferrer')
}

export default function App() {
  const [activeTab, setActiveTab] = useState('analyze')
  const [health, setHealth] = useState(false)
  const [history, setHistory] = useState([])
  const [analysisRaw, setAnalysisRaw] = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [selectedFindingId, setSelectedFindingId] = useState(null)
  const [selectedActionIds, setSelectedActionIds] = useState([])
  const [loading, setLoading] = useState(false)
  const [busyAction, setBusyAction] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const [file, setFile] = useState(null)
  const [goldenFile, setGoldenFile] = useState(null)
  const [rulesText, setRulesText] = useState('required_columns: []\ncross_checks: []\ncolumn_rules: {}')
  const [useLlm, setUseLlm] = useState(true)
  const [comparePrevious, setComparePrevious] = useState(true)
  const [llmModel, setLlmModel] = useState('')
  const [powerbiToken, setPowerbiToken] = useState('')
  const [datasetName, setDatasetName] = useState('EvaluadorCalidadDatos')
  const [tableName, setTableName] = useState('clean_data')
  const [batchInputDir, setBatchInputDir] = useState('')
  const [batchOutputDir, setBatchOutputDir] = useState('artifacts/batch_output')

  const selectedFinding = useMemo(() => {
    if (!analysis?.findings?.length) return null
    return analysis.findings.find((f) => f.id === selectedFindingId) || analysis.findings[0]
  }, [analysis, selectedFindingId])

  const selectedActions = useMemo(() => {
    if (!analysis?.actions?.length) return []
    return analysis.actions.filter((a) => selectedActionIds.includes(a.id))
  }, [analysis, selectedActionIds])

  async function refreshHealthAndHistory() {
    try {
      const [healthData, historyData] = await Promise.all([
        getHealth().catch(() => null),
        getHistory(25).catch(() => ({ items: [] })),
      ])
      setHealth(Boolean(healthData?.status === 'ok'))
      setHistory(historyData?.items || [])
    } catch {
      setHealth(false)
    }
  }

  useEffect(() => {
    refreshHealthAndHistory()
  }, [])

  useEffect(() => {
    if (!analysis?.findings?.length) return
    setSelectedFindingId((prev) => prev || analysis.findings[0].id)
  }, [analysis])

  async function handleAnalyze() {
    if (!file) {
      setError('Seleccioná un archivo primero.')
      return
    }
    setError('')
    setSuccess('')
    setBusyAction('analyze')
    setLoading(true)
    try {
      const response = await analyzeDataset({
        file,
        goldenFile,
        rulesText,
        useLlm,
        comparePrevious,
        llmModel,
      })
      setAnalysisRaw(response)
      const normalized = normalizeReport(response)
      setAnalysis(normalized)
      setSelectedActionIds(normalized.actions.map((a) => a.id))
      setSelectedFindingId(normalized.findings[0]?.id || null)
      setSuccess('Análisis completado correctamente.')
      setActiveTab('actions')
      await refreshHealthAndHistory()
    } catch (e) {
      setError(e.message || 'No se pudo completar el análisis.')
    } finally {
      setLoading(false)
      setBusyAction('')
    }
  }

  async function handleApplyActions() {
    if (!file) {
      setError('Seleccioná un archivo primero.')
      return
    }
    setError('')
    setSuccess('')
    setBusyAction('apply')
    setLoading(true)
    try {
      const response = await applyActions({
        file,
        goldenFile,
        rulesText,
        useLlm,
        comparePrevious,
        llmModel,
        selectedActionIds,
      })
      const normalized = normalizeReport(response)
      setAnalysis(normalized)
      setSuccess('Acciones aplicadas y dataset corregido generado.')
      setActiveTab('comparison')
      await refreshHealthAndHistory()
    } catch (e) {
      setError(e.message || 'No se pudieron aplicar las acciones.')
    } finally {
      setLoading(false)
      setBusyAction('')
    }
  }

  async function handleExportPowerBI() {
    if (!file) {
      setError('Seleccioná un archivo primero.')
      return
    }
    setError('')
    setSuccess('')
    setBusyAction('powerbi')
    setLoading(true)
    try {
      const response = await exportToPowerBI({
        file,
        goldenFile,
        rulesText,
        useLlm,
        comparePrevious,
        llmModel,
        selectedActionIds,
        powerbiToken,
        datasetName,
        tableName,
      })
      const normalized = normalizeReport(response)
      setAnalysis(normalized)
      setSuccess('Exportación a Power BI completada.')
      await refreshHealthAndHistory()
    } catch (e) {
      setError(e.message || 'No se pudo exportar a Power BI.')
    } finally {
      setLoading(false)
      setBusyAction('')
    }
  }

  async function handleBatch() {
    setError('')
    setSuccess('')
    setBusyAction('batch')
    setLoading(true)
    try {
      const response = await runBatch({
        inputDir: batchInputDir,
        outputDir: batchOutputDir,
        rulesText,
        llmModel,
      })
      setSuccess('Procesamiento batch completado.')
      if (response?.output_dir) {
        setBatchOutputDir(response.output_dir)
      }
      await refreshHealthAndHistory()
    } catch (e) {
      setError(e.message || 'No se pudo ejecutar el batch.')
    } finally {
      setLoading(false)
      setBusyAction('')
    }
  }

  const apiReady = health ? (
    <span className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
      <CheckCircle2 className="h-3.5 w-3.5" /> API online
    </span>
  ) : (
    <span className="inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-700">
      <AlertCircle className="h-3.5 w-3.5" /> API no verificada
    </span>
  )

  return (
    <AppShell activeTab={activeTab} setActiveTab={setActiveTab} health={health}>
      <div className="space-y-6">
        {(error || success) && (
          <div
            className={[
              'rounded-[22px] border px-5 py-4 shadow-sm',
              error ? 'border-red-200 bg-red-50 text-red-800' : 'border-emerald-200 bg-emerald-50 text-emerald-800',
            ].join(' ')}
          >
            <div className="flex items-start gap-3">
              {error ? <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" /> : <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0" />}
              <div className="text-sm leading-6">{error || success}</div>
            </div>
          </div>
        )}

        <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <SectionCard
            title="Configuración de análisis"
            subtitle="Conectado a FastAPI · reglas, archivos, comparación y exportación."
            right={apiReady}
          >
            <div className="space-y-5">
              <FileDropzone
                label="Subí un CSV o Excel"
                description="Arrastrá el archivo principal del dataset."
                file={file}
                onChange={setFile}
              />

              <div className="grid gap-4 md:grid-cols-2">
                <FileDropzone
                  label="Golden / referencia"
                  description="Opcional: archivo para comparar drift o schema."
                  file={goldenFile}
                  onChange={setGoldenFile}
                />
                <div className="rounded-[24px] border border-slate-200 bg-slate-50 p-4">
                  <div className="text-sm font-semibold text-slate-900">Ajustes de análisis</div>
                  <div className="mt-4 space-y-3 text-sm">
                    <label className="flex items-center gap-3">
                      <input type="checkbox" checked={useLlm} onChange={(e) => setUseLlm(e.target.checked)} />
                      Usar LLM para recomendaciones
                    </label>
                    <label className="flex items-center gap-3">
                      <input type="checkbox" checked={comparePrevious} onChange={(e) => setComparePrevious(e.target.checked)} />
                      Comparar contra golden / versión previa
                    </label>
                  </div>
                </div>
              </div>

              <div className="grid gap-4 lg:grid-cols-2">
                <label className="space-y-2">
                  <div className="text-sm font-semibold text-slate-900">Modelo LLM</div>
                  <input
                    value={llmModel}
                    onChange={(e) => setLlmModel(e.target.value)}
                    placeholder="qwen2.5-14b-instruct"
                    className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none ring-0 transition focus:border-brand-300 focus:ring-4 focus:ring-brand-100"
                  />
                </label>
                <label className="space-y-2">
                  <div className="text-sm font-semibold text-slate-900">Reglas configurables (YAML/JSON)</div>
                  <textarea
                    rows={8}
                    value={rulesText}
                    onChange={(e) => setRulesText(e.target.value)}
                    className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none transition focus:border-brand-300 focus:ring-4 focus:ring-brand-100"
                  />
                </label>
              </div>

              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={handleAnalyze}
                  disabled={loading}
                  className="inline-flex items-center rounded-2xl bg-brand-600 px-5 py-3 text-sm font-semibold text-white shadow-soft transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-70"
                >
                  {busyAction === 'analyze' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Sparkles className="mr-2 h-4 w-4" />}
                  Analizar
                </button>

                <button
                  type="button"
                  onClick={handleApplyActions}
                  disabled={loading}
                  className="inline-flex items-center rounded-2xl border border-slate-200 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-70"
                >
                  {busyAction === 'apply' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ShieldCheck className="mr-2 h-4 w-4" />}
                  Aplicar acciones
                </button>

                <button
                  type="button"
                  onClick={handleExportPowerBI}
                  disabled={loading}
                  className="inline-flex items-center rounded-2xl border border-slate-200 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-70"
                >
                  {busyAction === 'powerbi' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ArrowRight className="mr-2 h-4 w-4" />}
                  Exportar a Power BI
                </button>
              </div>

              <div className="grid gap-4 md:grid-cols-3">
                <MetricCard label="Score" value={analysis?.score ?? '—'} hint="Calidad general" accent />
                <MetricCard label="Filas" value={analysis?.rows ? analysis.rows.toLocaleString() : '—'} hint="Registros procesados" />
                <MetricCard label="Columnas" value={analysis?.columns ?? '—'} hint="Variables analizadas" />
              </div>
            </div>
          </SectionCard>

          <SectionCard
            title="Vista rápida"
            subtitle="Resumen operativo del análisis y accesos a salidas."
            right={<Badge severity="info">{analysis?.status || 'Sin análisis'}</Badge>}
          >
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-[22px] border border-slate-200 bg-slate-50 p-4">
                <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Hallazgos</div>
                <div className="mt-2 text-3xl font-bold text-slate-900">{analysis?.findings?.length ?? 0}</div>
                <div className="mt-1 text-sm text-slate-500">Detectados por el motor</div>
              </div>
              <div className="rounded-[22px] border border-slate-200 bg-slate-50 p-4">
                <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Acciones</div>
                <div className="mt-2 text-3xl font-bold text-slate-900">{analysis?.actions?.length ?? 0}</div>
                <div className="mt-1 text-sm text-slate-500">Sugeridas o disponibles</div>
              </div>
            </div>

            <div className="mt-5 rounded-[24px] border border-slate-200 bg-white p-5">
              <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Resumen ejecutivo</div>
              <p className="mt-3 text-sm leading-7 text-slate-600">
                {analysis?.summaryText || 'Ejecutá un análisis para ver el resumen detallado del dataset y las recomendaciones.'}
              </p>
            </div>

            <div className="mt-5 flex flex-wrap gap-3">
              <button
                className="rounded-2xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                onClick={() => analysis?.reportHtmlUrl && downloadUrl(analysis.reportHtmlUrl)}
              >
                <FileDown className="mr-2 inline h-4 w-4" />
                Reporte HTML
              </button>
              <button
                className="rounded-2xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                onClick={() => analysis?.cleanedCsvUrl && downloadUrl(analysis.cleanedCsvUrl)}
              >
                <FileDown className="mr-2 inline h-4 w-4" />
                CSV limpio
              </button>
              <button
                className="rounded-2xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                onClick={() => analysis?.reportJsonUrl && downloadUrl(analysis.reportJsonUrl)}
              >
                <FileDown className="mr-2 inline h-4 w-4" />
                JSON
              </button>
            </div>
          </SectionCard>
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
          <SectionCard
            title="Hallazgos"
            subtitle="Seleccioná un ítem para ver detalle, ejemplos y propuesta de corrección."
            right={<Badge severity="info">{selectedActionIds.length} acciones marcadas</Badge>}
          >
            <div className="space-y-3">
              {(analysis?.findings || []).length ? (
                analysis.findings.map((finding) => (
                  <FindingCard
                    key={finding.id}
                    finding={finding}
                    active={selectedFinding?.id === finding.id}
                    onSelect={() => {
                      setSelectedFindingId(finding.id)
                      setActiveTab('actions')
                    }}
                  />
                ))
              ) : (
                <div className="rounded-[24px] border border-dashed border-slate-200 bg-slate-50 p-6 text-sm text-slate-500">
                  Todavía no hay hallazgos. Ejecutá un análisis para generar el reporte.
                </div>
              )}
            </div>

            {selectedFinding ? (
              <div className="mt-5 rounded-[24px] border border-slate-200 bg-slate-50 p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Detalle del hallazgo</div>
                    <h3 className="mt-2 text-lg font-semibold text-slate-900">{selectedFinding.title}</h3>
                    <p className="mt-1 text-sm leading-7 text-slate-600">{selectedFinding.message}</p>
                  </div>
                  <Badge severity={selectedFinding.severity}>{selectedFinding.severity}</Badge>
                </div>

                <div className="mt-4 grid gap-4 sm:grid-cols-3">
                  <div className="rounded-[18px] bg-white p-4 shadow-sm">
                    <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Columna</div>
                    <div className="mt-2 text-sm font-semibold text-slate-900">{selectedFinding.column || '—'}</div>
                  </div>
                  <div className="rounded-[18px] bg-white p-4 shadow-sm">
                    <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Casos</div>
                    <div className="mt-2 text-sm font-semibold text-slate-900">{selectedFinding.count ?? '—'}</div>
                  </div>
                  <div className="rounded-[18px] bg-white p-4 shadow-sm">
                    <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Riesgo</div>
                    <div className="mt-2 text-sm font-semibold text-slate-900">{selectedFinding.risk || '—'}</div>
                  </div>
                </div>

                <div className="mt-4 rounded-[18px] border border-slate-200 bg-white p-4">
                  <div className="text-sm font-semibold text-slate-900">Ejemplos</div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {(selectedFinding.examples || []).length ? (
                      selectedFinding.examples.map((ex, i) => (
                        <span key={i} className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-sm text-slate-700">
                          {flattenText(ex)}
                        </span>
                      ))
                    ) : (
                      <span className="text-sm text-slate-500">Sin ejemplos.</span>
                    )}
                  </div>
                </div>
              </div>
            ) : null}
          </SectionCard>

          <SectionCard
            title="Acciones sugeridas"
            subtitle="Marcá lo que querés aplicar al dataset antes de exportar."
            right={<Badge severity="info">{selectedActions.length} seleccionadas</Badge>}
          >
            <div className="space-y-3">
              {(analysis?.actions || []).length ? (
                analysis.actions.map((action) => (
                  <ActionCard
                    key={action.id}
                    action={action}
                    checked={selectedActionIds.includes(action.id)}
                    onToggle={() => {
                      setSelectedActionIds((prev) =>
                        prev.includes(action.id) ? prev.filter((id) => id !== action.id) : [...prev, action.id]
                      )
                    }}
                    onPreview={() => {
                      setSelectedFindingId(action.id)
                    }}
                  />
                ))
              ) : (
                <div className="rounded-[24px] border border-dashed border-slate-200 bg-slate-50 p-6 text-sm text-slate-500">
                  No hay acciones para mostrar todavía. Ejecutá el análisis o revisá el esquema del backend.
                </div>
              )}
            </div>

            {selectedActions.length ? (
              <div className="mt-5 rounded-[24px] border border-brand-100 bg-brand-50 p-5">
                <div className="text-sm font-semibold text-brand-900">Resumen de selección</div>
                <ul className="mt-3 space-y-2 text-sm leading-6 text-brand-900/80">
                  {selectedActions.map((a) => (
                    <li key={a.id} className="flex items-start gap-2">
                      <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
                      <span>{a.title}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </SectionCard>
        </section>

        <section className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
          <SectionCard
            title="Comparación"
            subtitle="Golden / versión previa / cambios de score."
          >
            <div className="grid gap-4 md:grid-cols-3">
              <MetricCard label="Score actual" value={analysis?.score ?? '—'} hint="Resultado vigente" accent />
              <MetricCard label="Score previo" value={analysis?.previousScore ?? '—'} hint="Si el backend lo envía" />
              <MetricCard label="Variación" value={analysis?.nextScore ?? '—'} hint="Inferido o calculado por el backend" />
            </div>

            <div className="mt-5 rounded-[24px] border border-slate-200 bg-slate-50 p-5 text-sm leading-7 text-slate-600">
              Si tu backend devuelve comparación contra golden o versión anterior, esta sección la mostrará de forma visual aquí.
            </div>
          </SectionCard>

          <SectionCard
            title="Batch, Power BI e historial"
            subtitle="Automatización, publicación y seguimiento."
          >
            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-[24px] border border-slate-200 bg-slate-50 p-4">
                <div className="text-sm font-semibold text-slate-900">Modo batch</div>
                <div className="mt-3 space-y-3">
                  <input
                    value={batchInputDir}
                    onChange={(e) => setBatchInputDir(e.target.value)}
                    placeholder="Ruta de carpeta de entrada"
                    className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-brand-300 focus:ring-4 focus:ring-brand-100"
                  />
                  <input
                    value={batchOutputDir}
                    onChange={(e) => setBatchOutputDir(e.target.value)}
                    placeholder="Ruta de salida"
                    className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-brand-300 focus:ring-4 focus:ring-brand-100"
                  />
                  <button
                    type="button"
                    onClick={handleBatch}
                    disabled={loading}
                    className="w-full rounded-2xl bg-brand-600 px-4 py-3 text-sm font-semibold text-white shadow-soft hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-70"
                  >
                    {busyAction === 'batch' ? <Loader2 className="mr-2 inline h-4 w-4 animate-spin" /> : null}
                    Ejecutar batch
                  </button>
                </div>
              </div>

              <div className="rounded-[24px] border border-slate-200 bg-slate-50 p-4">
                <div className="text-sm font-semibold text-slate-900">Power BI</div>
                <div className="mt-3 space-y-3">
                  <input
                    value={datasetName}
                    onChange={(e) => setDatasetName(e.target.value)}
                    placeholder="Nombre del dataset"
                    className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-brand-300 focus:ring-4 focus:ring-brand-100"
                  />
                  <input
                    value={tableName}
                    onChange={(e) => setTableName(e.target.value)}
                    placeholder="Nombre de la tabla"
                    className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-brand-300 focus:ring-4 focus:ring-brand-100"
                  />
                  <input
                    value={powerbiToken}
                    onChange={(e) => setPowerbiToken(e.target.value)}
                    placeholder="Token Power BI (si aplica)"
                    className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-brand-300 focus:ring-4 focus:ring-brand-100"
                  />
                  <button
                    type="button"
                    onClick={handleExportPowerBI}
                    disabled={loading}
                    className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-70"
                  >
                    Exportar a Power BI
                  </button>
                </div>
              </div>
            </div>
          </SectionCard>
        </section>

        <section className="grid gap-6 xl:grid-cols-[0.92fr_1.08fr]">
          <SectionCard title="Historial" subtitle="Últimas ejecuciones y artefactos guardados.">
            <HistoryList items={history} />
          </SectionCard>

          <SectionCard title="Artefactos del reporte" subtitle="Links directos al HTML, JSON y archivos limpios.">
            {analysis?.runId ? (
              <div className="space-y-3">
                <a className="block rounded-[22px] border border-slate-200 bg-white p-4 text-sm font-medium text-slate-700 hover:bg-slate-50" href={analysis.reportHtmlUrl} target="_blank" rel="noreferrer">
                  Reporte HTML
                </a>
                <a className="block rounded-[22px] border border-slate-200 bg-white p-4 text-sm font-medium text-slate-700 hover:bg-slate-50" href={analysis.reportJsonUrl} target="_blank" rel="noreferrer">
                  Reporte JSON
                </a>
                <a className="block rounded-[22px] border border-slate-200 bg-white p-4 text-sm font-medium text-slate-700 hover:bg-slate-50" href={analysis.cleanedCsvUrl} target="_blank" rel="noreferrer">
                  CSV limpio
                </a>
                <a className="block rounded-[22px] border border-slate-200 bg-white p-4 text-sm font-medium text-slate-700 hover:bg-slate-50" href={analysis.cleanedXlsxUrl} target="_blank" rel="noreferrer">
                  XLSX limpio
                </a>
              </div>
            ) : (
              <div className="rounded-[24px] border border-dashed border-slate-200 bg-slate-50 p-6 text-sm text-slate-500">
                Cuando el backend devuelva un run_id, acá aparecen los links directos a los artefactos.
              </div>
            )}
          </SectionCard>
        </section>
      </div>
    </AppShell>
  )
}
