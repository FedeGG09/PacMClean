const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function requestJson(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, options)
  const contentType = response.headers.get('content-type') || ''

  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try {
      if (contentType.includes('application/json')) {
        const data = await response.json()
        message = data?.detail || data?.message || JSON.stringify(data)
      } else {
        message = await response.text()
      }
    } catch {
      // ignore
    }
    throw new Error(message)
  }

  if (contentType.includes('application/json')) {
    return response.json()
  }

  return response.text()
}

function appendFormValue(formData, key, value) {
  if (value === undefined || value === null) return
  if (typeof value === 'boolean') {
    formData.append(key, value ? 'true' : 'false')
    return
  }
  formData.append(key, String(value))
}

function buildUploadForm({
  file,
  goldenFile,
  rulesText,
  useLlm,
  comparePrevious,
  llmModel,
}) {
  const formData = new FormData()
  if (file) formData.append('file', file)
  if (goldenFile) formData.append('golden_file', goldenFile)
  appendFormValue(formData, 'rules_text', rulesText || '')
  appendFormValue(formData, 'use_llm', Boolean(useLlm))
  appendFormValue(formData, 'compare_previous', Boolean(comparePrevious))
  appendFormValue(formData, 'llm_model', llmModel || '')
  return formData
}

export function getApiBaseUrl() {
  return API_URL
}

export async function getHealth() {
  return requestJson('/api/health')
}

export async function getHistory(limit = 50) {
  return requestJson(`/api/history?limit=${encodeURIComponent(limit)}`)
}

export async function analyzeDataset(payload) {
  const formData = buildUploadForm(payload)
  return requestJson('/api/analyze', {
    method: 'POST',
    body: formData,
  })
}

export async function applyActions(payload) {
  const formData = buildUploadForm(payload)
  const actionIds = Array.isArray(payload.selectedActionIds) ? payload.selectedActionIds : []
  formData.append('selected_action_ids', JSON.stringify(actionIds))
  return requestJson('/api/apply-actions', {
    method: 'POST',
    body: formData,
  })
}

export async function exportToPowerBI(payload) {
  const formData = buildUploadForm(payload)
  const actionIds = Array.isArray(payload.selectedActionIds) ? payload.selectedActionIds : []
  formData.append('selected_action_ids', JSON.stringify(actionIds))
  appendFormValue(formData, 'powerbi_token', payload.powerbiToken || '')
  appendFormValue(formData, 'dataset_name', payload.datasetName || 'EvaluadorCalidadDatos')
  appendFormValue(formData, 'table_name', payload.tableName || 'clean_data')
  return requestJson('/api/export/powerbi', {
    method: 'POST',
    body: formData,
  })
}

export async function runBatch({ inputDir, outputDir, rulesText, llmModel }) {
  const formData = new FormData()
  appendFormValue(formData, 'input_dir', inputDir)
  appendFormValue(formData, 'output_dir', outputDir)
  appendFormValue(formData, 'rules_text', rulesText || '')
  appendFormValue(formData, 'llm_model', llmModel || '')
  return requestJson('/api/batch', {
    method: 'POST',
    body: formData,
  })
}

export function buildRunUrl(runId, fileName) {
  return `${API_URL}/api/runs/${runId}/${fileName}`
}

export async function downloadBinary(path) {
  const response = await fetch(`${API_URL}${path}`)
  if (!response.ok) {
    throw new Error(`Failed to download ${path}`)
  }
  return response.blob()
}
