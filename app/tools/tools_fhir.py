import requests
import subprocess
import platform
from datetime import datetime
from google.adk.tools import ToolContext
from app.utils.utils_fhir import (
    extract_basic_resource_info, organize_fhir_data, 
    format_patient_demographics, format_conditions, format_medications, 
    format_observations, format_allergies, format_procedures, format_encounters, 
    format_family_history, format_other_resources
)

# Configuration constants
PROJECT_ID = 'ci-repofhir-dev'
DATASET_ID = 'ci-hcset-interop-dataset'
LOCATION = 'us-east1'
FHIR_STORE_ID = 'ci-hcstore-interop-final'

def _get_auth_token() -> str:
    """Get Google Cloud authentication token."""
    # Use gcloud.cmd on Windows, gcloud on Linux/Mac
    gcloud_cmd = 'gcloud.cmd' if platform.system() == 'Windows' else 'gcloud'
    
    result = subprocess.run(
        [gcloud_cmd, 'auth', 'print-access-token'], 
        check=True, 
        stdout=subprocess.PIPE, 
        text=True
    )
    return result.stdout.strip()

def _get_fhir_base_url() -> str:
    """Get the base FHIR store URL."""
    return (f"https://healthcare.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}"
            f"/datasets/{DATASET_ID}/fhirStores/{FHIR_STORE_ID}/fhir")

def _get_auth_headers() -> dict:
    """Get authentication headers for API requests."""
    return {
        'Authorization': f'Bearer {_get_auth_token()}',
        'Content-Type': 'application/fhir+json'
    }

def _get_all_patient_data_sync(patient_id: str) -> dict:
    """Synchronously fetch ALL data for a patient using $everything operation."""
    url = f"{_get_fhir_base_url()}/Patient/{patient_id}/$everything"
    headers = _get_auth_headers()
    
    params = {
        '_count': '500'
    }
    
    print(f"Fetching complete patient data...")
    
    all_resources = []
    next_url = url
    page = 1
    
    while next_url:
        print(f"  Page {page}...")
        
        if next_url == url:
            response = requests.get(next_url, headers=headers, params=params)
        else:
            response = requests.get(next_url, headers=headers)
        
        response.raise_for_status()
        bundle = response.json()
        
        if 'entry' in bundle:
            all_resources.extend(bundle['entry'])
        
        next_url = None
        for link in bundle.get('link', []):
            if link.get('relation') == 'next':
                next_url = link.get('url')
                page += 1
                break
    
    print(f"Total resources: {len(all_resources)}")
    return organize_fhir_data(all_resources)

def _get_patient_specific_resource_sync(patient_id: str, resource_type: str) -> list:
    """Synchronously get specific resource type for a patient WITHOUT using $everything."""
    url = f"{_get_fhir_base_url()}/{resource_type}"
    headers = _get_auth_headers()
    
    params = {
        'patient': patient_id,
        '_count': '500'
    }
    
    print(f"Fetching {resource_type} data for patient {patient_id}...")
    
    all_resources = []
    next_url = url
    page = 1
    
    while next_url:
        print(f"  Page {page}...")
        
        if next_url == url:
            response = requests.get(next_url, headers=headers, params=params)
        else:
            response = requests.get(next_url, headers=headers)
        
        response.raise_for_status()
        bundle = response.json()
        
        if 'entry' in bundle:
            all_resources.extend([entry['resource'] for entry in bundle['entry']])
        
        next_url = None
        for link in bundle.get('link', []):
            if link.get('relation') == 'next':
                next_url = link.get('url')
                page += 1
                break
    
    print(f"Total {resource_type} resources: {len(all_resources)}")
    return all_resources

# =============================================================================
# PATIENT REPORT TOOLS (Using State)
# =============================================================================

def generate_complete_patient_report(tool_context: ToolContext) -> dict:
    """Generates a comprehensive clinical summary report for the current patient.

    This tool fetches all clinical data using the FHIR $everything operation and creates 
    a complete, structured report including demographics, conditions, medications, 
    observations, allergies, procedures, encounters, and family history.

    Use this tool when you need a complete overview of the patient's entire clinical 
    history and all related medical information.

    Returns:
        A dictionary containing the report generation results with keys:
        - status: 'success' or 'error'
        - report: The complete formatted clinical report as a string (if successful)
        - patient_id: The patient ID that was processed
        - total_resources: Number of FHIR resources processed
        - error_message: Error description (if status is 'error')
        - generated_at: Timestamp when the report was generated
    """
    try:
        # Get patient ID from state
        patient_id = tool_context.state.get('patient_id')
        
        if not patient_id:
            return {
                'status': 'error',
                'patient_id': None,
                'error_message': 'No patient ID found in session state. Please provide a patient ID first.',
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        
        # Get all patient data synchronously using requests
        all_data = _get_all_patient_data_sync(patient_id)
        
        # Generate report using existing formatting functions
        report = []
        report.append("=" * 80)
        report.append("COMPLETE CLINICAL SUMMARY REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        report.append("")
        
        # Patient Demographics
        if 'Patient' in all_data:
            report.extend(format_patient_demographics(all_data['Patient']))
        
        # Conditions
        if 'Condition' in all_data:
            report.extend(format_conditions(all_data['Condition']))
        
        # Medications
        medication_requests = all_data.get('MedicationRequest', [])
        medication_statements = all_data.get('MedicationStatement', [])
        if medication_requests or medication_statements:
            report.extend(format_medications(medication_requests, medication_statements))
        
        # Observations
        if 'Observation' in all_data:
            report.extend(format_observations(all_data['Observation'], show_all=True))
        
        # Allergies
        if 'AllergyIntolerance' in all_data:
            report.extend(format_allergies(all_data['AllergyIntolerance']))
        
        # Procedures
        if 'Procedure' in all_data:
            report.extend(format_procedures(all_data['Procedure']))
        
        # Encounters
        if 'Encounter' in all_data:
            report.extend(format_encounters(all_data['Encounter']))
        
        # Family History
        if 'FamilyMemberHistory' in all_data:
            report.extend(format_family_history(all_data['FamilyMemberHistory']))
        
        # Other Resources
        excluded_types = {
            'Patient', 'Condition', 'MedicationRequest', 'MedicationStatement', 
            'Observation', 'AllergyIntolerance', 'Procedure', 'Encounter', 'FamilyMemberHistory',
            'Account', 'Appointment', 'AppointmentResponse', 'ClinicalImpression', 
            'Composition', 'Coverage', 'DocumentReference', 'ExplanationOfBenefit', 
            'Person', 'Organization', 'ServiceRequest'
        }
        
        other_resources = {}
        for resource_type, resources in all_data.items():
            if resource_type not in excluded_types:
                other_resources[resource_type] = resources
        
        if other_resources:
            report.extend(format_other_resources(other_resources))
        
        # Summary
        report.append("=" * 80)
        report.append("CLINICAL SUMMARY")
        report.append("-" * 50)
        
        # Count clinical resources for summary
        clinical_counts = [
            ('Conditions', len(all_data.get('Condition', []))),
            ('Medications', len(all_data.get('MedicationRequest', [])) + len(all_data.get('MedicationStatement', []))),
            ('Observations', len(all_data.get('Observation', []))),
            ('Allergies', len(all_data.get('AllergyIntolerance', []))),
            ('Procedures', len(all_data.get('Procedure', []))),
            ('Encounters', len(all_data.get('Encounter', []))),
            ('Family History', len(all_data.get('FamilyMemberHistory', [])))
        ]
        
        for category, count in clinical_counts:
            if count > 0:
                report.append(f"• {category}: {count} records")
        
        # Show other clinical resources if any
        for resource_type, resources in sorted(other_resources.items()):
            report.append(f"• {resource_type}: {len(resources)} records")
        
        total_clinical = sum(len(resources) for resources in other_resources.values()) + sum(count for _, count in clinical_counts)
        
        report.append(f"\nTOTAL CLINICAL RECORDS: {total_clinical}")
        report.append("=" * 80)
        
        report_content = "\n".join(report)
        
        return {
            'status': 'success',
            'report': report_content,
            'patient_id': patient_id,
            'total_resources': total_clinical,
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
            
    except Exception as e:
        return {
            'status': 'error',
            'patient_id': tool_context.state.get('patient_id'),
            'error_message': str(e),
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

def generate_specific_resource_report(resource_type: str, tool_context: ToolContext) -> dict:
    """Generates a focused clinical report for a specific FHIR resource type for the current patient.

    This tool fetches only the specified resource type (without using $everything) and creates 
    a targeted report focused on that specific clinical data category. This is more efficient 
    when you only need information about a particular aspect of the patient's care.

    Use this tool when you need detailed information about a specific type of clinical data 
    rather than a complete patient overview.

    Args:
        resource_type: The specific FHIR resource type to focus on. Common types include:
                      'Condition', 'Observation', 'MedicationRequest', 'MedicationStatement',
                      'AllergyIntolerance', 'Procedure', 'Encounter', 'FamilyMemberHistory',
                      'DiagnosticReport', 'DocumentReference', 'Appointment', 'Coverage'.

    Returns:
        A dictionary containing the report generation results with keys:
        - status: 'success' or 'error'
        - report: The formatted clinical report for the specific resource type (if successful)
        - patient_id: The patient ID that was processed
        - resource_type: The FHIR resource type that was queried
        - resource_count: Number of resources of this type found for the patient
        - error_message: Error description (if status is 'error')
        - generated_at: Timestamp when the report was generated
    """
    try:
        # Get patient ID from state
        patient_id = tool_context.state.get('patient_id')
        
        if not patient_id:
            return {
                'status': 'error',
                'patient_id': None,
                'resource_type': resource_type,
                'error_message': 'No patient ID found in session state. Please provide a patient ID first.',
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        
        # Get specific resource data synchronously using requests
        resource_data = _get_patient_specific_resource_sync(patient_id, resource_type)
        
        if not resource_data:
            return {
                'status': 'error',
                'patient_id': patient_id,
                'resource_type': resource_type,
                'error_message': f'No {resource_type} data found for patient {patient_id}',
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        
        # Generate report using existing formatting functions
        report = []
        report.append("=" * 80)
        report.append(f"{resource_type.upper()} SUMMARY")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        report.append("")
        
        # Format based on resource type
        if resource_type == 'Condition':
            report.extend(format_conditions(resource_data))
        elif resource_type == 'MedicationRequest':
            report.extend(format_medications(resource_data, []))
        elif resource_type == 'MedicationStatement':
            report.extend(format_medications([], resource_data))
        elif resource_type == 'Observation':
            report.extend(format_observations(resource_data, show_all=False))  # More concise for single resource
        elif resource_type == 'AllergyIntolerance':
            report.extend(format_allergies(resource_data))
        elif resource_type == 'Procedure':
            report.extend(format_procedures(resource_data))
        elif resource_type == 'Encounter':
            report.extend(format_encounters(resource_data, limit=10))  # Limit for conciseness
        elif resource_type == 'FamilyMemberHistory':
            report.extend(format_family_history(resource_data))
        else:
            # Generic formatting for other resource types
            report.append(f"{resource_type.upper()} ({len(resource_data)} records)")
            report.append("-" * 50)
            
            # Show only first 10 resources for conciseness
            for i, resource in enumerate(resource_data[:10], 1):
                info = extract_basic_resource_info(resource)
                report.append(f"• {info}")
            
            if len(resource_data) > 10:
                report.append(f"... and {len(resource_data) - 10} more")
            
            report.append("")
        
        # Summary
        report.append("=" * 80)
        report.append(f"TOTAL {resource_type.upper()} RECORDS: {len(resource_data)}")
        report.append("=" * 80)
        
        report_content = "\n".join(report)
        
        return {
            'status': 'success',
            'report': report_content,
            'patient_id': patient_id,
            'resource_type': resource_type,
            'resource_count': len(resource_data),
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
            
    except Exception as e:
        return {
            'status': 'error',
            'patient_id': tool_context.state.get('patient_id'),
            'resource_type': resource_type,
            'error_message': str(e),
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

def get_all_tools():
    """Return all available tools for the patient report agent."""
    return [
        generate_complete_patient_report,
        generate_specific_resource_report
    ]