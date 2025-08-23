# 🏥 Multiple Medical Agents Deployment Guide

Este proyecto ahora soporta múltiples agentes especializados en diferentes aspectos de la atención médica, siguiendo la estructura estándar de ADK (Agent Development Kit).

## 📋 Estructura del Proyecto

```
my-awesome-agent/
├── patient_report_agent/           # Agente para reportes de pacientes FHIR
│   ├── __init__.py
│   ├── agent.py                   # root_agent especializado en reportes
│   └── tools/
│       └── tools_fhir.py          # Herramientas FHIR
├── diagnostic_agent/              # Agente para diagnóstico diferencial
│   ├── __init__.py
│   └── agent.py                   # root_agent especializado en diagnóstico
├── medication_agent/              # Agente para gestión de medicamentos
│   ├── __init__.py
│   └── agent.py                   # root_agent especializado en medicamentos
├── shared_utils/                  # Utilidades compartidas
│   ├── __init__.py
│   ├── gcs.py
│   ├── tracing.py
│   ├── typing.py
│   └── utils_fhir.py
├── deployment/                    # Scripts de despliegue
│   └── deploy_multiple_agents.py  # Script principal de despliegue
├── test_multiple_agents.py        # Script de pruebas locales
└── app/                          # Estructura legacy (mantenida para compatibilidad)
```

## 🤖 Agentes Disponibles

### 1. Patient Report Agent (`patient_report_agent`)
- **Especialidad**: Generación de reportes clínicos comprensivos desde datos FHIR
- **Herramientas**: 
  - `generate_complete_patient_report()` - Reportes completos del paciente
  - `generate_specific_resource_report(resource_type)` - Reportes específicos por tipo de recurso
- **Casos de uso**: Resúmenes clínicos, reportes médicos, análisis de historia clínica

### 2. Diagnostic Agent (`diagnostic_agent`)
- **Especialidad**: Diagnóstico diferencial y análisis de síntomas
- **Herramientas**:
  - `analyze_symptoms(symptoms, patient_history)` - Análisis de síntomas
  - `google_search` - Investigación médica actualizada
- **Casos de uso**: Diagnóstico diferencial, análisis de síntomas, recomendaciones de pruebas

### 3. Medication Agent (`medication_agent`)
- **Especialidad**: Gestión de medicamentos e interacciones farmacológicas
- **Herramientas**:
  - `check_drug_interactions(medications, new_medication)` - Verificación de interacciones
  - `medication_dosing_guide(medication, patient_weight, kidney_function)` - Guías de dosificación
  - `google_search` - Investigación farmacológica
- **Casos de uso**: Revisión de interacciones, dosificación personalizada, seguridad farmacológica

## 🚀 Despliegue en Vertex AI Agent Engine

### Opción 1: Desplegar Todos los Agentes

```bash
# Instalar dependencias
make install

# Desplegar todos los agentes médicos
make deploy-multiple
```

### Opción 2: Desplegar Agentes Específicos

```bash
# Desplegar solo agentes específicos
make deploy-agents AGENTS="patient_report_agent diagnostic_agent"
```

### Opción 3: Despliegue Manual con Opciones Avanzadas

```bash
# Exportar dependencias
uv export --no-hashes --no-header --no-dev --no-emit-project > .requirements.txt

# Desplegar con configuración personalizada
uv run python deployment/deploy_multiple_agents.py \
  --project YOUR_PROJECT_ID \
  --location us-central1 \
  --agents patient_report_agent diagnostic_agent \
  --set-env-vars "CUSTOM_VAR=value,ANOTHER_VAR=value2"
```

## 🧪 Pruebas Locales

Antes del despliegue, es recomendable probar los agentes localmente:

```bash
# Probar todos los agentes
make test-agents

# O ejecutar manualmente
uv run python test_multiple_agents.py
```

## 📊 Monitoreo y Observabilidad

Cada agente desplegado incluye:

- **Logging estructurado** con Google Cloud Logging
- **Tracing distribuido** con OpenTelemetry y Cloud Trace
- **Métricas personalizadas** para análisis de rendimiento
- **Feedback collection** para mejora continua

## 🔧 Configuración Avanzada

### Variables de Entorno

Los agentes soportan las siguientes variables de entorno:

```bash
# Configuración de Google Cloud
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_GENAI_USE_VERTEXAI=True

# Configuración de workers
NUM_WORKERS=1

# Variables personalizadas por agente
CUSTOM_AGENT_CONFIG=value
```

### Personalización de Buckets

```bash
# Personalizar prefijo de buckets
uv run python deployment/deploy_multiple_agents.py \
  --staging-bucket-prefix "my-medical-agents"
```

### Gestión de Recursos

El script de despliegue crea automáticamente:

- **Staging Bucket**: `{project}-agents-staging` (para artifacts de despliegue)
- **Artifacts Bucket**: `{project}-agents-artifacts` (para datos de sesión)
- **Agent Engines**: Uno por cada agente especializado

## 📋 Metadatos de Despliegue

Después del despliegue, se genera un archivo `deployment_metadata_multiple_agents.json` con:

```json
{
  "deployment_timestamp": "2025-01-XX...",
  "project": "your-project-id",
  "location": "us-central1",
  "agents": {
    "patient_report_agent": {
      "resource_name": "projects/.../locations/.../reasoningEngines/...",
      "display_name": "Patient Report Agent",
      "status": "deployed"
    },
    "diagnostic_agent": {
      "resource_name": "projects/.../locations/.../reasoningEngines/...",
      "display_name": "Diagnostic Agent", 
      "status": "deployed"
    }
  }
}
```

## 🔄 Actualizaciones y Versionado

Para actualizar agentes ya desplegados:

1. **Modificar el código** del agente en su directorio correspondiente
2. **Ejecutar el despliegue** nuevamente - el script detectará agentes existentes y los actualizará
3. **Verificar la actualización** en la consola de Vertex AI

```bash
# Actualizar agente específico
make deploy-agents AGENTS="patient_report_agent"
```

## 🚨 Solución de Problemas

### Error: "No configuration found for agent"
- Verificar que el agente esté listado en `_get_agent_config()` en `deploy_multiple_agents.py`
- Asegurar que el directorio del agente tenga `__init__.py` y `agent.py`

### Error: "Error importing agent"
- Verificar que todas las dependencias estén instaladas (`make install`)
- Revisar que las importaciones en `agent.py` sean correctas
- Verificar que `root_agent` esté definido en cada `agent.py`

### Error: "Bucket creation failed"
- Verificar permisos de Google Cloud (rol `Owner` o `Storage Admin`)
- Asegurar que el proyecto tenga habilitada la API de Cloud Storage

### Despliegue parcial
- Revisar el archivo `deployment_metadata_multiple_agents.json` para ver qué agentes fallaron
- Ejecutar nuevamente el despliegue - solo se actualizarán/crearán los agentes necesarios

## 📚 Recursos Adicionales

- [Documentación ADK](GEMINI.md) - Guía completa del Agent Development Kit
- [Vertex AI Agent Engine Documentation](https://cloud.google.com/vertex-ai/docs/agent-engine)
- [Google Cloud IAM Best Practices](https://cloud.google.com/iam/docs/best-practices)

## 🤝 Contribuciones

Para agregar nuevos agentes:

1. **Crear directorio** con la estructura: `new_agent/{__init__.py, agent.py}`
2. **Definir root_agent** en `agent.py` con nombre, modelo, instrucción y herramientas
3. **Agregar configuración** en `_get_agent_config()` en `deploy_multiple_agents.py`
4. **Actualizar documentación** y casos de prueba

---

¡Ahora tienes un sistema robusto de múltiples agentes médicos especializados listos para producción! 🏥✨
