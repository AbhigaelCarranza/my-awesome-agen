"""
Utility functions for FHIR data processing and report formatting.
Extracted from patient_report_functions.py for better organization.
"""

from typing import Dict, Any, List, Optional
from collections import defaultdict


# =============================================================================
# FHIR DATA EXTRACTION HELPER FUNCTIONS
# =============================================================================

def get_coding_display(codeable_concept: Optional[Dict]) -> str:
    """Extract display text from FHIR CodeableConcept."""
    if not codeable_concept:
        return ''
    
    if 'text' in codeable_concept:
        return codeable_concept['text']
    
    codings = codeable_concept.get('coding', [])
    if codings:
        return codings[0].get('display', codings[0].get('code', ''))
    
    return ''

def get_observation_category(observation: Dict) -> str:
    """Get observation category."""
    categories = observation.get('category', [])
    if categories:
        for cat in categories:
            codings = cat.get('coding', [])
            for coding in codings:
                return coding.get('code', '')
    return ''

def get_observation_value(observation: Dict) -> str:
    """Extract observation value in human-readable format."""
    if 'valueQuantity' in observation:
        qty = observation['valueQuantity']
        return f"{qty.get('value', '')} {qty.get('unit', '')}"
    elif 'valueCodeableConcept' in observation:
        return get_coding_display(observation['valueCodeableConcept'])
    elif 'valueString' in observation:
        return observation['valueString']
    elif 'valueBoolean' in observation:
        return str(observation['valueBoolean'])
    elif 'valueInteger' in observation:
        return str(observation['valueInteger'])
    elif 'valueRange' in observation:
        range_val = observation['valueRange']
        low = range_val.get('low', {}).get('value', '')
        high = range_val.get('high', {}).get('value', '')
        unit = range_val.get('low', {}).get('unit', '')
        return f"{low} - {high} {unit}"
    return 'No value recorded'

def get_components(observation: Dict) -> List[str]:
    """Get observation components."""
    components = []
    for comp in observation.get('component', []):
        comp_name = get_coding_display(comp.get('code'))
        comp_value = get_observation_value(comp)
        if comp_name and comp_value:
            components.append(f"{comp_name}: {comp_value}")
    return components

def get_reference_range(observation: Dict) -> str:
    """Get reference range for observation."""
    ref_ranges = observation.get('referenceRange', [])
    if ref_ranges:
        range_info = ref_ranges[0]
        low = range_info.get('low', {}).get('value', '')
        high = range_info.get('high', {}).get('value', '')
        unit = range_info.get('low', {}).get('unit', range_info.get('high', {}).get('unit', ''))
        if low or high:
            return f"{low} - {high} {unit}".strip()
    return ''

def get_medication_name(medication: Dict) -> str:
    """Extract medication name."""
    if 'medicationCodeableConcept' in medication:
        return get_coding_display(medication['medicationCodeableConcept'])
    elif 'medicationReference' in medication:
        return medication['medicationReference'].get('display', 'Unknown medication')
    return 'Unknown medication'

def get_dosage_instruction(medication: Dict) -> str:
    """Extract dosage instruction."""
    dosages = medication.get('dosageInstruction', medication.get('dosage', []))
    if dosages:
        dosage = dosages[0]
        if 'text' in dosage:
            return dosage['text']
        
        # Build dosage from components
        parts = []
        if 'doseAndRate' in dosage:
            for dose_rate in dosage['doseAndRate']:
                if 'doseQuantity' in dose_rate:
                    qty = dose_rate['doseQuantity']
                    parts.append(f"{qty.get('value', '')} {qty.get('unit', '')}")
        
        if 'timing' in dosage:
            timing = dosage['timing']
            if 'repeat' in timing:
                repeat = timing['repeat']
                if 'frequency' in repeat:
                    parts.append(f"{repeat['frequency']} times per {repeat.get('period', '')} {repeat.get('periodUnit', '')}")
        
        return ' '.join(parts) if parts else ''
    return ''

def get_allergy_reactions(allergy: Dict) -> List[str]:
    """Extract allergy reactions."""
    reactions = []
    for reaction in allergy.get('reaction', []):
        manifestations = reaction.get('manifestation', [])
        for manifestation in manifestations:
            reaction_text = get_coding_display(manifestation)
            severity = reaction.get('severity', '')
            if severity:
                reaction_text += f" (Severity: {severity})"
            reactions.append(reaction_text)
    return reactions

def get_encounter_type(encounter: Dict) -> str:
    """Get encounter type."""
    enc_types = encounter.get('type', [])
    if enc_types:
        return get_coding_display(enc_types[0])
    
    enc_class = encounter.get('class')
    if enc_class:
        return get_coding_display(enc_class)
    
    return ''

def get_encounter_reasons(encounter: Dict) -> str:
    """Get encounter reasons."""
    reasons = []
    
    # Check reasonCode
    reason_codes = encounter.get('reasonCode', [])
    for reason in reason_codes:
        reasons.append(get_coding_display(reason))
    
    return ', '.join(reasons) if reasons else ''

def extract_basic_resource_info(resource: Dict) -> str:
    """Extract basic information from any resource type."""
    resource_type = resource.get('resourceType', '')
    
    # Try to get some basic identifying information
    info_parts = []
    
    # Common fields
    if 'status' in resource:
        info_parts.append(f"Status: {resource['status']}")
    
    # Type-specific fields
    if resource_type == 'DiagnosticReport':
        code = get_coding_display(resource.get('code'))
        if code:
            info_parts.append(f"Type: {code}")
        
        date = resource.get('effectiveDateTime', resource.get('issued', ''))
        if date:
            info_parts.append(f"Date: {date.split('T')[0]}")
    
    elif resource_type == 'DocumentReference':
        doc_type = get_coding_display(resource.get('type'))
        if doc_type:
            info_parts.append(f"Type: {doc_type}")
        
        date = resource.get('created', resource.get('indexed', ''))
        if date:
            info_parts.append(f"Date: {date.split('T')[0]}")
    
    elif resource_type == 'Appointment':
        date = resource.get('start', '')
        if date:
            info_parts.append(f"Date: {date.split('T')[0]}")
        
        service_types = resource.get('serviceType', [])
        if service_types:
            service_type = get_coding_display(service_types[0])
            if service_type:
                info_parts.append(f"Service: {service_type}")
    
    elif resource_type == 'Coverage':
        coverage_type = get_coding_display(resource.get('type'))
        if coverage_type:
            info_parts.append(f"Type: {coverage_type}")
        
        period = resource.get('period', {})
        if 'start' in period:
            info_parts.append(f"Start: {period['start'].split('T')[0]}")
    
    return ' | '.join(info_parts) if info_parts else f"{resource_type} record"

def organize_fhir_data(entries: List[Dict]) -> Dict[str, Any]:
    """Organize FHIR resources by type."""
    organized_data = {}
    
    for entry in entries:
        resource = entry.get('resource', {})
        resource_type = resource.get('resourceType', 'Unknown')
        
        if resource_type not in organized_data:
            organized_data[resource_type] = []
        
        organized_data[resource_type].append(resource)
    
    return organized_data


# =============================================================================
# RESOURCE FORMATTING FUNCTIONS
# =============================================================================

def format_patient_demographics(patient_data: List[Dict]) -> List[str]:
    """Format patient demographics section."""
    if not patient_data:
        return []
    
    patient = patient_data[0]
    report = []
    report.append("DEMOGRAPHICS")
    report.append("-" * 50)
    report.append(f"Gender: {patient.get('gender', 'Not specified')}")
    report.append(f"Birth Date: {patient.get('birthDate', 'Not specified')}")
    report.append(f"Marital Status: {get_coding_display(patient.get('maritalStatus'))}")
    report.append("")
    
    return report

def format_conditions(conditions_data: List[Dict]) -> List[str]:
    """Format conditions section."""
    if not conditions_data:
        return []
    
    report = []
    condition_groups = defaultdict(list)
    
    for cond in conditions_data:
        name = get_coding_display(cond.get('code'))
        date = cond.get('recordedDate', cond.get('onsetDateTime', ''))
        if date:
            date = date.split('T')[0]
        
        clinical_status = get_coding_display(cond.get('clinicalStatus'))
        verification_status = get_coding_display(cond.get('verificationStatus'))
        severity = get_coding_display(cond.get('severity'))
        notes = [note.get('text', '') for note in cond.get('note', [])]
        
        condition_groups[name].append({
            'date': date,
            'clinical_status': clinical_status,
            'verification_status': verification_status,
            'severity': severity,
            'notes': notes
        })
    
    report.append(f"ALL CONDITIONS ({len(conditions_data)} records)")
    report.append("-" * 50)
    
    for condition, records in sorted(condition_groups.items()):
        report.append(f"• {condition} ({len(records)} records)")
        
        # Sort by date, most recent first
        records.sort(key=lambda x: x.get('date', ''), reverse=True)
        
        for record in records:
            details = []
            if record['date']:
                details.append(f"Date: {record['date']}")
            if record['clinical_status']:
                details.append(f"Status: {record['clinical_status']}")
            if record['verification_status']:
                details.append(f"Verified: {record['verification_status']}")
            if record['severity']:
                details.append(f"Severity: {record['severity']}")
            
            if details:
                report.append(f"  - {' | '.join(details)}")
            
            for note in record['notes']:
                if note:
                    report.append(f"    Note: {note}")
        
        report.append("")
    
    return report

def format_medications(medication_requests: List[Dict], medication_statements: List[Dict] = None) -> List[str]:
    """Format medications section."""
    if medication_statements is None:
        medication_statements = []
    
    all_meds = []
    all_meds.extend(medication_requests)
    all_meds.extend(medication_statements)
    
    if not all_meds:
        return []
    
    report = []
    med_groups = defaultdict(list)
    
    for med in all_meds:
        name = get_medication_name(med)
        date = med.get('authoredOn', med.get('effectiveDateTime', med.get('dateAsserted', '')))
        if date:
            date = date.split('T')[0]
        
        status = med.get('status', '')
        intent = med.get('intent', '')
        dosage = get_dosage_instruction(med)
        
        med_groups[name].append({
            'date': date,
            'status': status,
            'intent': intent,
            'dosage': dosage,
            'type': med.get('resourceType', '')
        })
    
    report.append(f"ALL MEDICATIONS ({len(all_meds)} records)")
    report.append("-" * 50)
    
    for med_name, records in sorted(med_groups.items()):
        report.append(f"• {med_name} ({len(records)} records)")
        
        # Sort by date, most recent first
        records.sort(key=lambda x: x.get('date', ''), reverse=True)
        
        for record in records:
            details = []
            if record['date']:
                details.append(f"Date: {record['date']}")
            if record['status']:
                details.append(f"Status: {record['status']}")
            if record['intent']:
                details.append(f"Intent: {record['intent']}")
            if record['type']:
                details.append(f"Type: {record['type']}")
            
            if details:
                report.append(f"  - {' | '.join(details)}")
            
            if record['dosage']:
                report.append(f"    Dosage: {record['dosage']}")
        
        report.append("")
    
    return report

def format_observations(observations_data: List[Dict], show_all: bool = True) -> List[str]:
    """Format observations section (vitals, labs, others)."""
    if not observations_data:
        return []
    
    report = []
    
    # Separate by category
    vitals = []
    labs = []
    other_obs = []
    
    for obs in observations_data:
        category = get_observation_category(obs)
        if category == 'vital-signs':
            vitals.append(obs)
        elif category in ['laboratory', 'exam']:
            labs.append(obs)
        else:
            other_obs.append(obs)
    
    # Process Vitals
    if vitals:
        vital_groups = defaultdict(list)
        for vital in vitals:
            vital_type = get_coding_display(vital.get('code'))
            date = vital.get('effectiveDateTime', vital.get('issued', ''))
            if date:
                date = date.split('T')[0]
            
            value = get_observation_value(vital)
            status = vital.get('status', '')
            interpretation = get_coding_display(vital.get('interpretation', [{}])[0] if vital.get('interpretation') else {})
            
            vital_groups[vital_type].append({
                'date': date,
                'value': value,
                'status': status,
                'interpretation': interpretation
            })
        
        report.append(f"VITAL SIGNS ({len(vitals)} records)")
        report.append("-" * 50)
        
        for vital_type, records in sorted(vital_groups.items()):
            report.append(f"• {vital_type} ({len(records)} records)")
            
            # Sort by date, most recent first
            records.sort(key=lambda x: x.get('date', ''), reverse=True)
            
            # Show all or just recent based on flag
            display_records = records if show_all else records[:3]
            
            for record in display_records:
                details = []
                if record['date']:
                    details.append(f"Date: {record['date']}")
                if record['value']:
                    details.append(f"Value: {record['value']}")
                if record['status']:
                    details.append(f"Status: {record['status']}")
                if record['interpretation']:
                    details.append(f"Interpretation: {record['interpretation']}")
                
                if details:
                    report.append(f"  - {' | '.join(details)}")
            
            if not show_all and len(records) > 3:
                report.append(f"  ... and {len(records) - 3} more")
            
            report.append("")
    
    # Process Labs
    if labs:
        lab_groups = defaultdict(list)
        for lab in labs:
            lab_type = get_coding_display(lab.get('code'))
            date = lab.get('effectiveDateTime', lab.get('issued', ''))
            if date:
                date = date.split('T')[0]
            
            value = get_observation_value(lab)
            status = lab.get('status', '')
            interpretation = get_coding_display(lab.get('interpretation', [{}])[0] if lab.get('interpretation') else {})
            ref_range = get_reference_range(lab)
            
            lab_groups[lab_type].append({
                'date': date,
                'value': value,
                'status': status,
                'interpretation': interpretation,
                'ref_range': ref_range
            })
        
        report.append(f"LABORATORY RESULTS ({len(labs)} records)")
        report.append("-" * 50)
        
        for lab_type, records in sorted(lab_groups.items()):
            report.append(f"• {lab_type} ({len(records)} records)")
            
            # Sort by date, most recent first
            records.sort(key=lambda x: x.get('date', ''), reverse=True)
            
            # Show all or just recent based on flag
            display_records = records if show_all else records[:3]
            
            for record in display_records:
                details = []
                if record['date']:
                    details.append(f"Date: {record['date']}")
                if record['value']:
                    details.append(f"Value: {record['value']}")
                if record['status']:
                    details.append(f"Status: {record['status']}")
                if record['interpretation']:
                    details.append(f"Interpretation: {record['interpretation']}")
                if record['ref_range']:
                    details.append(f"Reference: {record['ref_range']}")
                
                if details:
                    report.append(f"  - {' | '.join(details)}")
            
            if not show_all and len(records) > 3:
                report.append(f"  ... and {len(records) - 3} more")
            
            report.append("")
    
    # Process Other Observations
    if other_obs:
        other_groups = defaultdict(list)
        for obs in other_obs:
            obs_type = get_coding_display(obs.get('code'))
            date = obs.get('effectiveDateTime', obs.get('issued', ''))
            if date:
                date = date.split('T')[0]
            
            value = get_observation_value(obs)
            status = obs.get('status', '')
            category = get_observation_category(obs)
            components = get_components(obs)
            
            other_groups[obs_type].append({
                'date': date,
                'value': value,
                'status': status,
                'category': category,
                'components': components
            })
        
        report.append(f"OTHER OBSERVATIONS ({len(other_obs)} records)")
        report.append("-" * 50)
        
        for obs_type, records in sorted(other_groups.items()):
            report.append(f"• {obs_type} ({len(records)} records)")
            
            # Sort by date, most recent first
            records.sort(key=lambda x: x.get('date', ''), reverse=True)
            
            # Show all or just most recent
            display_records = records if show_all else records[:1]
            
            for record in display_records:
                details = []
                if record['date']:
                    details.append(f"Date: {record['date']}")
                if record['value'] and record['value'] != 'No value recorded':
                    details.append(f"Value: {record['value']}")
                if record['status']:
                    details.append(f"Status: {record['status']}")
                if record['category']:
                    details.append(f"Category: {record['category']}")
                
                if details:
                    report.append(f"  - {' | '.join(details)}")
                
                for component in record['components']:
                    report.append(f"    {component}")
            
            if not show_all and len(records) > 1:
                report.append(f"  ... and {len(records) - 1} more")
            
            report.append("")
    
    return report

def format_allergies(allergies_data: List[Dict]) -> List[str]:
    """Format allergies section."""
    if not allergies_data:
        return []
    
    report = []
    allergy_groups = defaultdict(list)
    
    for allergy in allergies_data:
        substance = get_coding_display(allergy.get('code'))
        date = allergy.get('recordedDate', '')
        if date:
            date = date.split('T')[0]
        
        clinical_status = get_coding_display(allergy.get('clinicalStatus'))
        verification_status = get_coding_display(allergy.get('verificationStatus'))
        allergy_type = allergy.get('type', '')
        category = ', '.join(allergy.get('category', []))
        criticality = allergy.get('criticality', '')
        reactions = get_allergy_reactions(allergy)
        
        allergy_groups[substance].append({
            'date': date,
            'clinical_status': clinical_status,
            'verification_status': verification_status,
            'type': allergy_type,
            'category': category,
            'criticality': criticality,
            'reactions': reactions
        })
    
    report.append(f"ALL ALLERGIES ({len(allergies_data)} records)")
    report.append("-" * 50)
    
    for substance, records in sorted(allergy_groups.items()):
        report.append(f"• {substance} ({len(records)} records)")
        
        # Sort by date, most recent first
        records.sort(key=lambda x: x.get('date', ''), reverse=True)
        
        for record in records:
            details = []
            if record['date']:
                details.append(f"Date: {record['date']}")
            if record['clinical_status']:
                details.append(f"Status: {record['clinical_status']}")
            if record['verification_status']:
                details.append(f"Verified: {record['verification_status']}")
            if record['type']:
                details.append(f"Type: {record['type']}")
            if record['category']:
                details.append(f"Category: {record['category']}")
            if record['criticality']:
                details.append(f"Criticality: {record['criticality']}")
            
            if details:
                report.append(f"  - {' | '.join(details)}")
            
            for reaction in record['reactions']:
                report.append(f"    Reaction: {reaction}")
        
        report.append("")
    
    return report

def format_procedures(procedures_data: List[Dict]) -> List[str]:
    """Format procedures section."""
    if not procedures_data:
        return []
    
    report = []
    procedure_groups = defaultdict(list)
    
    for procedure in procedures_data:
        name = get_coding_display(procedure.get('code'))
        date = procedure.get('performedDateTime', '')
        if not date and 'performedPeriod' in procedure:
            date = procedure['performedPeriod'].get('start', '')
        if date:
            date = date.split('T')[0]
        
        status = procedure.get('status', '')
        body_sites = [get_coding_display(site) for site in procedure.get('bodySite', [])]
        outcome = get_coding_display(procedure.get('outcome'))
        
        procedure_groups[name].append({
            'date': date,
            'status': status,
            'body_sites': body_sites,
            'outcome': outcome
        })
    
    report.append(f"ALL PROCEDURES ({len(procedures_data)} records)")
    report.append("-" * 50)
    
    for procedure_name, records in sorted(procedure_groups.items()):
        report.append(f"• {procedure_name} ({len(records)} records)")
        
        # Sort by date, most recent first
        records.sort(key=lambda x: x.get('date', ''), reverse=True)
        
        for record in records:
            details = []
            if record['date']:
                details.append(f"Date: {record['date']}")
            if record['status']:
                details.append(f"Status: {record['status']}")
            if record['outcome']:
                details.append(f"Outcome: {record['outcome']}")
            
            if details:
                report.append(f"  - {' | '.join(details)}")
            
            if record['body_sites']:
                report.append(f"    Body sites: {', '.join(record['body_sites'])}")
        
        report.append("")
    
    return report

def format_encounters(encounters_data: List[Dict], limit: Optional[int] = None) -> List[str]:
    """Format encounters section."""
    if not encounters_data:
        return []
    
    report = []
    
    # Sort encounters by date, most recent first
    encounters_sorted = []
    for enc in encounters_data:
        date = enc.get('period', {}).get('start', '')
        if date:
            date = date.split('T')[0]
        encounters_sorted.append((date, enc))
    
    encounters_sorted.sort(key=lambda x: x[0], reverse=True)
    
    report.append(f"ALL ENCOUNTERS ({len(encounters_data)} records)")
    report.append("-" * 50)
    
    # Apply limit if specified
    display_encounters = encounters_sorted[:limit] if limit else encounters_sorted
    
    for date, enc in display_encounters:
        enc_type = get_encounter_type(enc)
        status = enc.get('status', '')
        reasons = get_encounter_reasons(enc)
        period_end = enc.get('period', {}).get('end', '')
        if period_end:
            period_end = period_end.split('T')[0]
        
        details = []
        if date:
            details.append(f"Date: {date}")
        if period_end and period_end != date:
            details.append(f"End: {period_end}")
        if status:
            details.append(f"Status: {status}")
        if enc_type:
            details.append(f"Type: {enc_type}")
        
        report.append(f"• {' | '.join(details)}")
        
        if reasons:
            report.append(f"  Reason: {reasons}")
        
        # Diagnoses
        diagnoses = enc.get('diagnosis', [])
        if diagnoses:
            for diag in diagnoses:
                condition_ref = diag.get('condition', {}).get('display', diag.get('condition', {}).get('reference', ''))
                use = get_coding_display(diag.get('use'))
                if condition_ref:
                    diag_info = f"  Diagnosis: {condition_ref}"
                    if use:
                        diag_info += f" ({use})"
                    report.append(diag_info)
        
        report.append("")
    
    if limit and len(encounters_data) > limit:
        report.append(f"... and {len(encounters_data) - limit} more encounters")
        report.append("")
    
    return report

def format_family_history(family_history_data: List[Dict]) -> List[str]:
    """Format family history section."""
    if not family_history_data:
        return []
    
    report = []
    report.append(f"FAMILY HISTORY ({len(family_history_data)} records)")
    report.append("-" * 50)
    
    for family_member in family_history_data:
        relationship = get_coding_display(family_member.get('relationship'))
        date = family_member.get('date', '')
        if date:
            date = date.split('T')[0]
        
        # Get conditions
        conditions = []
        for condition in family_member.get('condition', []):
            cond_name = get_coding_display(condition.get('code'))
            onset = condition.get('onsetAge', {})
            if 'value' in onset:
                cond_name += f" (age {onset['value']} {onset.get('unit', 'years')})"
            conditions.append(cond_name)
        
        details = []
        if relationship:
            details.append(f"Relationship: {relationship}")
        if date:
            details.append(f"Date: {date}")
        
        if details:
            report.append(f"• {' | '.join(details)}")
        
        for condition in conditions:
            report.append(f"  - {condition}")
        
        report.append("")
    
    return report

def format_other_resources(other_resources: Dict[str, List[Dict]], limit: int = 5) -> List[str]:
    """Format other clinical resources section."""
    if not other_resources:
        return []
    
    report = []
    report.append("OTHER CLINICAL RESOURCES")
    report.append("-" * 50)
    
    for resource_type, resources in sorted(other_resources.items()):
        report.append(f"{resource_type.upper()} ({len(resources)} records)")
        
        # Show only first few resources
        for i, resource in enumerate(resources[:limit], 1):
            info = extract_basic_resource_info(resource)
            report.append(f"  • {info}")
        
        if len(resources) > limit:
            report.append(f"  ... and {len(resources) - limit} more")
        
        report.append("")
    
    return report