import csv
import random
from datetime import datetime, timedelta

def generate_ebola_claims(filename, num_rows=1000):
    headers = [
        "claim_id", "member_id", "provider_id", "plan_id", "service_date", "claim_amount", 
        "allowed_amount", "paid_amount", "status", "diagnosis_code", "procedure_code", 
        "charges", "allowed", "clean_claim_status", "claim_from", "clean_claim_out", 
        "utilization", "hcg_units_days", "claim_type", "major_service_category", 
        "provider_specialty", "detailed_service_category", "ms_drg", "ms_drg_description", 
        "ms_drg_mdc", "ms_drg_mdc_desc", "cpt", "cpt_consumer_description", 
        "procedure_level_1", "procedure_level_2", "procedure_level_3", "procedure_level_4", 
        "procedure_level_5", "channel", "drug_name", "drug_class", "drug_subclass", 
        "drug", "is_oon", "best_contracting_entity_name", "provider_group_name", 
        "ccsr_system_description", "ccsr_description"
    ]

    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 12, 31)

    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)

        for i in range(num_rows):
            claim_id = f"CLM2024{i+10000:07d}" # Offset to avoid collision
            member_id = f"MBR2024{random.randint(1, 1000):06d}"
            provider_id = "PRV00101"
            plan_id = f"PLN2024{random.randint(1, 10):04d}"
            
            days_offset = random.randint(0, (end_date - start_date).days)
            service_date = start_date + timedelta(days=days_offset)
            service_date_str = service_date.strftime("%Y-%m-%d")
            
            # Expensive claims
            claim_amount = round(random.uniform(50000, 500000), 2)
            allowed_amount = round(claim_amount * random.uniform(0.7, 0.9), 2)
            paid_amount = round(allowed_amount * random.uniform(0.8, 1.0), 2)
            
            status = "approved"
            diagnosis_code = "A98.4" # Ebola virus disease
            procedure_code = "99214" # Office visit (placeholder)
            
            charges = claim_amount
            allowed = allowed_amount
            
            clean_claim_status = "PAID"
            claim_from = service_date_str
            clean_claim_out = (service_date + timedelta(days=random.randint(15, 45))).strftime("%Y-%m-%d")
            
            utilization = 1.0
            hcg_units_days = random.randint(1, 10)
            
            claim_type = "Facility"
            major_service_category = "Inpatient"
            provider_specialty = "Infectious Disease"
            detailed_service_category = "Isolation Unit"
            
            ms_drg = "865" # Viral Illness
            ms_drg_description = "Viral Illness with MCC"
            ms_drg_mdc = "18"
            ms_drg_mdc_desc = "Infectious and Parasitic Diseases"
            
            cpt = "99291" # Critical care
            cpt_consumer_description = "Critical care, evaluation and management"
            
            procedure_level_1 = "Medicine"
            procedure_level_2 = "Critical Care"
            procedure_level_3 = "Inpatient"
            procedure_level_4 = "N/A"
            procedure_level_5 = "N/A"
            
            channel = "IP"
            
            drug_name = ""
            drug_class = ""
            drug_subclass = ""
            drug = ""
            
            is_oon = 0
            best_contracting_entity_name = "Strategic Alliance A"
            provider_group_name = "Regional Health Network"
            
            ccsr_system_description = "Certain infectious and parasitic diseases"
            ccsr_description = "INF002 - Viral infection"

            row = [
                claim_id, member_id, provider_id, plan_id, service_date_str, claim_amount,
                allowed_amount, paid_amount, status, diagnosis_code, procedure_code,
                charges, allowed, clean_claim_status, claim_from, clean_claim_out,
                utilization, hcg_units_days, claim_type, major_service_category,
                provider_specialty, detailed_service_category, ms_drg, ms_drg_description,
                ms_drg_mdc, ms_drg_mdc_desc, cpt, cpt_consumer_description,
                procedure_level_1, procedure_level_2, procedure_level_3, procedure_level_4,
                procedure_level_5, channel, drug_name, drug_class, drug_subclass,
                drug, is_oon, best_contracting_entity_name, provider_group_name,
                ccsr_system_description, ccsr_description
            ]
            writer.writerow(row)

if __name__ == "__main__":
    generate_ebola_claims("/home/garth/garage/aca_health/transform/seeds/claims_ebola.csv")
