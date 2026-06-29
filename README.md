# Evaluador de Calidad de Datos

Proyecto con backend FastAPI y frontend React (Vite), manteniendo el motor determinista, acciones aplicables, comparación, batch y exportación a Power BI.

## Estructura

- `backend/` : API FastAPI
- `frontend/` : React + Vite
- `data_quality_evaluator/` : motor de análisis, limpieza y reportes
- `main.py` : CLI
- `sample_rules.yaml` : reglas base

## Backend

### Instalar
```powershell
pip install -r requirements.txt
```

### Ejecutar API
```powershell
uvicorn backend.app:app --reload --port 8000
```

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

## Variables de entorno

### LLM local (LM Studio)
```powershell
$env:OPENAI_API_BASE="http://127.0.0.1:1234/v1"
$env:OPENAI_API_KEY="lm-studio"
$env:LMSTUDIO_MODEL="your-local-model-name"
```

### Power BI
```powershell
$env:POWERBI_ACCESS_TOKEN="..."
```

### Frontend
```powershell
$env:VITE_API_URL="http://127.0.0.1:8000"
```

## Flujo

1. Subís un archivo CSV/XLSX.
2. El backend hace perfilado, hallazgos, comparación y acciones sugeridas.
3. Elegís qué correcciones aplicar.
4. Descargás el archivo corregido.
5. Exportás a Power BI con un botón.

## Notas

- El front usa una estética azul/blanco/gris inspirada en la referencia adjunta.
- No se incluyen logos ni marcas.
- Los gráficos se omitieron a propósito para que Power BI sea el lugar final de visualización.
