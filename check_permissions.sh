#!/bin/bash

# Script para verificar permisos necesarios
echo "🔍 VERIFICANDO PERMISOS NECESARIOS..."
echo "======================================"

PROJECT_ID=$1
if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: Debes proporcionar el PROJECT_ID"
    echo "Uso: ./check_permissions.sh YOUR_PROJECT_ID"
    exit 1
fi

echo "📋 Proyecto: $PROJECT_ID"
echo "👤 Usuario: $(gcloud config get-value account)"
echo ""

# Verificar APIs habilitadas
echo "🔧 Verificando APIs habilitadas..."
REQUIRED_APIS=(
    "aiplatform.googleapis.com"
    "cloudbuild.googleapis.com" 
    "cloudresourcemanager.googleapis.com"
    "bigquery.googleapis.com"
    "storage-component.googleapis.com"
    "logging.googleapis.com"
    "cloudtrace.googleapis.com"
    "serviceusage.googleapis.com"
    "iam.googleapis.com"
    "discoveryengine.googleapis.com"
)

for api in "${REQUIRED_APIS[@]}"; do
    if gcloud services list --enabled --project=$PROJECT_ID --filter="name:$api" --format="value(name)" | grep -q "$api"; then
        echo "✅ $api - Habilitada"
    else
        echo "❌ $api - NO habilitada"
    fi
done

echo ""
echo "👤 Verificando permisos del usuario..."

USER_EMAIL=$(gcloud config get-value account)

# Primero verificar si tiene Owner (que incluye todo)
if gcloud projects get-iam-policy $PROJECT_ID --flatten="bindings[].members" --format="table(bindings.role)" --filter="bindings.members:$USER_EMAIL AND bindings.role:roles/owner" | grep -q "roles/owner"; then
    echo "🎉 ¡PERFECTO! Tienes rol Owner (roles/owner)"
    echo "✅ Esto incluye TODOS los permisos necesarios para el proyecto"
    echo ""
    echo "🎯 RESULTADO: Tienes permisos suficientes para crear agentes ✅"
else
    echo "ℹ️  No tienes rol Owner. Verificando roles específicos..."
    
    # Verificar permisos específicos
    REQUIRED_ROLES=(
        "roles/aiplatform.admin"
        "roles/cloudbuild.builds.editor"
        "roles/storage.admin"
        "roles/bigquery.admin"
        "roles/logging.admin"
        "roles/cloudtrace.admin"
        "roles/iam.serviceAccountAdmin"
        "roles/resourcemanager.projectIamAdmin"
    )

    for role in "${REQUIRED_ROLES[@]}"; do
        if gcloud projects get-iam-policy $PROJECT_ID --flatten="bindings[].members" --format="table(bindings.role)" --filter="bindings.members:$USER_EMAIL AND bindings.role:$role" | grep -q "$role"; then
            echo "✅ $role - Asignado"
        else
            echo "❌ $role - NO asignado"
        fi
    done
fi

echo ""
echo "🎯 Si ves ❌, solicita esos permisos al administrador."
