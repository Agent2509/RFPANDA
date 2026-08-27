"""
Sample Enterprise RFP Documents for ApexTender v2.0 E2E Testing.
Includes comprehensive Defense, Healthcare, and Cloud Migration RFP specifications with complex tables.
"""

DOD_CYBERSECURITY_RFP = """# Department of Defense (DoD) Cyber Defense RFP 2026-HQ-09
## 1.0 Executive Overview & Scope
The Department of Defense requires an enterprise-scale Zero Trust Architecture (ZTA) and continuous automated threat detection platform. The contractor shall supply software, engineering deployment, and 24/7/365 Security Operations Center (SOC) tier-3 support.

## 2.0 Mandatory Security Clearances & Certifications
| Requirement ID | Standard / Regulation | Required Compliance Level | Penalty for Non-Compliance |
| :--- | :--- | :--- | :--- |
| SEC-001 | FedRAMP High Authorization | Full Authorization at award | Immediate contract termination |
| SEC-002 | DoD IL5 / IL6 Hosting | Active CMMC Level 3 | 10% milestone withholding |
| SEC-003 | Personnel Clearances | Top Secret / SCI Eligible | Barred from government facility |
| SEC-004 | Encryption at Rest & In Transit | FIPS 140-3 Validated AES-256 | Non-responsive proposal rejection |

## 3.0 Service Level Agreements (SLAs) & Uptime Penalties
The contractor shall adhere to the following SLA terms in Section 3.2:
1. **System Availability**: The platform must maintain a minimum of **99.999% (five nines)** monthly availability, excluding scheduled maintenance windows.
2. **Critical Severity Incidents (P1)**: Initial response time < 10 minutes; mean time to remediation (MTTR) < 1 hour.
3. **High Severity Incidents (P2)**: Response time < 30 minutes; MTTR < 4 hours.
4. **Liquidated Damages & Penalties**:
   - Availability falling between 99.9% and 99.99%: 5% invoice credit deduction.
   - Availability falling below 99.9%: 15% invoice credit deduction plus potential default declaration.

## 4.0 Pricing Structure & Milestone Deliverables
| Phase | Milestone Description | Target Timeline | Not-To-Exceed (NTE) Cost |
| :--- | :--- | :--- | :--- |
| Phase 1 | Baseline Security Architecture & STIG Hardening | Month 1 | $450,000 |
| Phase 2 | Threat Intelligence Ingestion & Sensor Rollout | Months 2-4 | $1,200,000 |
| Phase 3 | Red Team Assessment & Operational Cutover | Month 6 | $850,000 |
| Phase 4 | Annual Operations & Maintenance (O&M) | Year 1-3 | $2,400,000 / year |

## 5.0 Proposal Submission & Evaluation Criteria
Proposals will be evaluated based on:
1. Technical Capability & STIG Compliance (40% weighting)
2. Past Performance on Federal DoD Contracts (30% weighting)
3. Cost Realism & Price Evaluation (30% weighting)
"""

HEALTHCARE_HIPAA_RFP = """# HealthNet Enterprise EMR & AI Analytics RFP 2026
## 1.0 General Information & Privacy Framework
HealthNet Alliance operates 42 hospitals and over 300 ambulatory clinics across 8 states. This RFP solicits proposals for an interoperable clinical decision support and patient records indexing engine.

## 2.0 HIPAA & GDPR Compliance Safeguards
| Regulation | Specific Requirement | Contractor Obligation | Audit Frequency |
| :--- | :--- | :--- | :--- |
| HIPAA Omnibus Rule | Business Associate Agreement (BAA) | Mandatory execution prior to data access | Annual third-party SOC 2 |
| GDPR Article 28 | Data Processor Security Safeguards | Explicit consent tracking & right to erasure | Quarterly compliance review |
| HITECH Act | Breach Notification Protocol | Mandatory notice within 24 hours of breach | Continuous logging |

## 3.0 Clinical Workflow & Query Response SLAs
- Average Vector Search Latency: Under 250ms for 95th percentile requests.
- EHR HL7 / FHIR Integration: Support for FHIR R4 standard with bi-directional syncing.
- Disaster Recovery RPO / RTO: RPO <= 5 minutes; RTO <= 15 minutes across geo-redundant regions.
"""

CLOUD_MIGRATION_RFP = """# State Department of Transportation Cloud Migration RFP
## Section 1: Project Objective
Migrate legacy mainframe tolling and traffic management applications to a secure hybrid-cloud environment.

## Section 2: Technical Specifications & SLA Terms
| Metric | Specification | Minimum Acceptance Threshold |
| :--- | :--- | :--- |
| Database Migration Downtime | Maximum allowable maintenance window | <= 2 hours cutover |
| API Throughput | Peak transactions per second (TPS) | >= 15,000 TPS |
| Latency Target | Edge API Gateway response time | <= 45ms P99 |

## Section 3: Pricing & Cost Breakdown
Total budget allocated is $3,500,000 over 24 months. Vendor proposals exceeding this ceiling will be disqualified.
"""
