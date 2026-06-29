# Evaluador de Calidad de Datos "PacMClean"

Proyecto con backend FastAPI y frontend React (Vite), manteniendo el motor determinista, acciones aplicables, comparación, batch y exportación a Power BI.

PacClean AI es una herramienta de limpieza y preparación de datos que combina inteligencia artificial con reglas determinísticas para transformar datasets crudos en información lista para análisis.

Inspirado en la estética arcade de los 80s, PacClean “devora” inconsistencias, valores nulos y errores, convirtiendo procesos complejos de data cleaning en una experiencia simple, visual y controlada.

<img width="1254" height="1254" alt="image" src="https://github.com/user-attachments/assets/ccb92dda-1936-4004-bfc4-e3266434b7eb" />



## Estructura

- `backend/` : API FastAPI
- `frontend/` : React + Vite
- `data_quality_evaluator/` : motor de análisis, limpieza y reportes
- `main.py` : CLI
- `sample_rules.yaml` : reglas base

<img width="1682" height="907" alt="image" src="https://github.com/user-attachments/assets/c4e3ca60-037d-489f-a8d8-0ee6cee039c8" />


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

## 🎥 Demo

Mirá cómo funciona PacMClean AI en acción:


[![PacClean Demo](https://img.youtube.com/vi/yfrD19grPUw/maxresdefault.jpg)](https://youtu.be/yfrD19grPUw)
