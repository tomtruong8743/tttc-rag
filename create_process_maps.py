"""
Generate Mermaid flowchart process maps for cooperating with VIFC.
These render as visual diagrams in Obsidian and on the website.

Each page contains:
- A Mermaid flowchart of the full cooperation process
- Step-by-step written description
- Required documents at each stage
- Key contacts and decree references

Usage:
    python3 create_process_maps.py
"""

import os
import sys
from datetime import date
from pathlib import Path
from wiki_writer import WIKI_DIR, get_known_pages, append_update_entry

FOLDER = "projects"
TODAY = date.today().isoformat()


def save_process_map(filename: str, content: str):
    dest = WIKI_DIR / FOLDER / filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    update_log = f"## Update Log\n- **{TODAY}**: Page created.\n"
    last_updated = f"\n\n*Last updated: {TODAY}*\n\n"
    dest.write_text(content + last_updated + update_log, encoding="utf-8")
    print(f"  [saved] {dest}")


# ── Process Maps ──────────────────────────────────────────────────

GENERAL_FOREIGN_COMPANY = """
# Process Map — How Foreign Companies Cooperate With VIFC

This page maps the full process for any foreign company wishing to establish
operations or cooperate with the Vietnam International Financial Centre (VIFC/TTTC).

## Cooperation Process Flowchart

```mermaid
flowchart TD
    A([🏢 Foreign Company\nDecides to Enter VIFC]) --> B[Research VIFC\nLegal Framework]
    B --> C{Choose\nOrganization Type}

    C -->|Bank| D1[See:\nHow Foreign Banks Can Work With VIFC]
    C -->|Investment Bank /\nSecurities Firm| D2[See:\nHow Investment Banks Can Work With VIFC]
    C -->|Import / Export| D3[See:\nHow Import and Export Companies\nCan Work With VIFC]
    C -->|Fintech| D4[See:\nHow Fintech Companies Can Work With VIFC]
    C -->|Insurance| D5[See:\nHow Insurance Companies Can Work With VIFC]
    C -->|Other Company| D6[General Foreign\nCompany Registration]

    D6 --> E[Step 1: Prepare Documents\n• Charter / Articles of Incorporation\n• Proof of foreign legal status\n• Business plan\n• Capital proof]

    E --> F[Step 2: Submit Application\nto VIFC Management Authority]

    F --> G{Application\nReview}
    G -->|Incomplete| H[Revise & Resubmit\nWithin 30 Days]
    H --> F
    G -->|Approved| I[Step 3: Receive\nInvestment Registration Certificate]

    I --> J[Step 4: Register Tax Code\nWith Tax Authority]
    J --> K[Step 5: Open Bank Account\nin Vietnam]
    K --> L[Step 6: Apply for\nWork Permits for Foreign Staff]
    L --> M[Step 7: Register Office /\nLand Use at VIFC Zone]
    M --> N[Step 8: Apply for\nTax Incentives Under Decree 324]
    N --> O[Step 9: Complete AML/KYC\nRegistration — Decree 329]
    O --> P([✅ Fully Operational\nat VIFC])

    P --> Q[Ongoing: Annual Compliance\nReporting & License Renewal]

    style A fill:#1c2f72,color:#fff
    style P fill:#00aeef,color:#fff
    style G fill:#f0f7ff,color:#1c2f72
    style Q fill:#fff7e6,color:#b45309
```

## Stage-by-Stage Description

### Stage 1 — Pre-Application
- Study applicable decrees: [[Decree 323 Establishment of TTTC]], [[Decree 324 Financial Policies of TTTC]]
- Identify which VIFC zone applies: Ho Chi Minh City or Da Nang
- Engage legal counsel familiar with Vietnamese corporate law

### Stage 2 — Document Preparation
Required documents:
- Certified copy of company charter / articles of incorporation
- Proof of legal existence in home country (apostilled)
- Audited financial statements (last 2 years)
- Business plan outlining VIFC activities
- Proof of minimum capital requirement
- Board resolution authorising VIFC establishment

### Stage 3 — Submission and Review
- Submit to VIFC Management Authority
- Review period: typically 15–30 working days
- Authority may request additional documents once

### Stage 4 — Registration and Setup
- Receive Investment Registration Certificate
- Register for tax code
- Open corporate bank account in Vietnam
- Apply for work permits for foreign staff (Decree 325)
- Secure office premises within VIFC zone (Decree 326)

### Stage 5 — Incentive Applications
- Apply for corporate income tax incentives (Decree 324)
- Apply for personal income tax incentives for key staff
- Register for special customs procedures if applicable (Decree 330)

### Stage 6 — Compliance Setup
- Complete AML/KYC registration (Decree 329)
- Establish internal compliance programme
- Register reporting obligations with supervisory authority

### Stage 7 — Ongoing Operations
- Annual compliance reports
- License renewal as required
- Update registration on material changes

## Key Decrees
| Decree | Covers |
|--------|--------|
| [[Decree 323 Establishment of TTTC]] | VIFC establishment, governance |
| [[Decree 324 Financial Policies of TTTC]] | Tax incentives, financial policies |
| [[Decree 325 Labor and Social Security in TTTC]] | Labor, work permits, social insurance |
| [[Decree 326 Land and Environment in TTTC]] | Land use, office premises |
| [[Decree 327 Immigration Policy]] | Visas, entry for foreign staff |
| [[Decree 329 Banking and Foreign Exchange]] | Banking licenses, FX, AML |
| [[Decree 330 Commodities Exchange in TTTC]] | Commodities trading |

## Cross-Reference for IFC Benchmarking
| Step | VIFC | Singapore MAS | Hong Kong SFC | Dubai DIFC |
|------|------|--------------|---------------|------------|
| Application review period | 15–30 days | 6–12 months | 3–6 months | 2–4 months |
| Minimum capital (general) | Per decree | SGD varies | HKD varies | USD varies |
| Tax rate | Per Decree 324 | 17% | 16.5% | 0% (DIFC) |
| Dispute resolution | [[Arbitration in the Vietnam International Financial Centre]] | SIAC | HKIAC | DIAC |

## Related Topics
- [[How Foreign Banks Can Work With VIFC Step By Step Onboarding Guide]]
- [[How Investment Banks Can Work With VIFC Step By Step Onboarding Guide]]
- [[How Import And Export Companies Can Work With VIFC Step By Step Onboarding Guide]]
- [[How Fintech Companies Can Work With VIFC Step By Step Onboarding Guide]]
- [[Tax Incentives In The Vietnam International Financial Centre]]
- [[Compliance Requirements In The Vietnam International Financial Centre]]
- [[Foreign Worker Regulations]]
- [[Vifc Onboarding Requirements Ifc Benchmarking And Cross-Reference Guide]]
"""

BANKS_PROCESS = """
# Process Map — How Banks Cooperate With VIFC

## Banking Cooperation Flowchart

```mermaid
flowchart TD
    A([🏦 Bank Decides\nto Enter VIFC]) --> B{Foreign or\nDomestic Bank?}

    B -->|Foreign Bank| C[Prepare Foreign Bank\nApplication Package]
    B -->|Domestic Bank| D[Prepare Domestic Bank\nApplication Package]

    C --> E[Documents Required:\n• Home country banking license\n• Audited financials 3 years\n• Fit & proper for directors\n• Capital adequacy proof\n• Business plan for VIFC]

    D --> F[Documents Required:\n• SBV operating license\n• Board resolution\n• Capital allocation plan\n• Compliance programme]

    E --> G[Submit to State Bank\nof Vietnam — SBV\nvia VIFC Authority]
    F --> G

    G --> H{SBV Review\n30–60 Days}
    H -->|Rejected| I[Address\nDeficiencies]
    I --> G
    H -->|Approved| J[Receive Banking\nLicense for VIFC]

    J --> K[Register with\nVIFC Management Authority]
    K --> L[Apply for Foreign\nExchange License — Decree 329]
    L --> M[Establish AML/KYC\nProgramme]
    M --> N[Register Reporting\nObligations with SBV]
    N --> O[Open VIFC Branch /\nSubsidiary Operations]
    O --> P([✅ Bank Operational\nat VIFC])

    P --> Q[Ongoing:\nQuarterly SBV Reports\nAnnual License Renewal\nAML Monitoring]

    style A fill:#1c2f72,color:#fff
    style P fill:#00aeef,color:#fff
    style H fill:#f0f7ff,color:#1c2f72
    style Q fill:#fff7e6,color:#b45309
```

## Key Requirements for Banks

### Foreign Banks
- Valid banking license from home jurisdiction
- Minimum 3 years of profitable operation
- Minimum capital as specified under Decree 329
- Fit and proper assessment for all directors and key executives
- Demonstrated compliance programme (AML/CFT)

### Domestic Banks
- Existing SBV license
- Board resolution to establish VIFC presence
- Capital ring-fenced for VIFC operations
- Designated VIFC compliance officer

## Applicable Decrees
- [[Decree 329 Banking and Foreign Exchange]] — primary licensing decree
- [[Decree 324 Financial Policies of TTTC]] — tax incentives
- [[Decree 323 Establishment of TTTC]] — governance framework

## Related Topics
- [[Foreign Banks In The Vietnam International Financial Centre]]
- [[Domestic Banks In The Vietnam International Financial Centre]]
- [[Foreign Exchange Rules In The Vietnam International Financial Centre]]
- [[Aml And Compliance Summary For Investment Banks In Tttc]]
- [[Process Map How Foreign Companies Cooperate With Vifc]]
"""

IMPORT_EXPORT_PROCESS = """
# Process Map — How Import and Export Companies Cooperate With VIFC

## Import / Export Cooperation Flowchart

```mermaid
flowchart TD
    A([📦 Import/Export Company\nDecides to Work With VIFC]) --> B{Type of\nActivity?}

    B -->|Physical Commodities\nTrading| C[Commodities Exchange\nMembership Path]
    B -->|Trade Finance /\nCross-Border Payments| D[Financial Services\nRegistration Path]
    B -->|General Import\nExport Operations| E[General Business\nRegistration Path]

    C --> F[Apply for Membership:\nVIFC Commodities Exchange\nDecree 330]
    F --> G[Documents:\n• Company registration\n• Trading history\n• Capital proof\n• Compliance programme]
    G --> H{Exchange\nReview — 15 Days}
    H -->|Approved| I[Receive Exchange\nMembership Certificate]

    D --> J[Register with\nVIFC Financial Authority]
    J --> K[Apply for Trade\nFinance License]
    K --> L[AML/KYC Registration\nDecree 329]

    E --> M[Standard VIFC\nBusiness Registration]
    M --> N[Apply for Import/Export\nBusiness License]
    N --> O[Register with\nCustoms Authority]

    I --> P[Access VIFC\nCommodities Trading Floor]
    L --> Q[Access Cross-Border\nPayment Services]
    O --> R[Access Special Customs\nProcedures at VIFC]

    P --> S([✅ Operational\nat VIFC])
    Q --> S
    R --> S

    S --> T[Ongoing:\nTransaction Reporting\nLicense Renewal\nCustoms Compliance]

    style A fill:#1c2f72,color:#fff
    style S fill:#00aeef,color:#fff
    style H fill:#f0f7ff,color:#1c2f72
    style T fill:#fff7e6,color:#b45309
```

## Key Requirements

### Commodities Exchange Members (Decree 330)
- Registered company in Vietnam or foreign branch
- Minimum capital as specified in Decree 330
- Designated compliance officer
- Trading system compatibility

### Trade Finance Operators
- Financial services license or banking partnership
- AML/KYC programme compliant with Decree 329
- Foreign exchange registration for cross-border transactions

### General Import/Export Companies
- Valid business registration certificate
- Import/export business license
- Customs registration with General Department of Vietnam Customs

## Applicable Decrees
- [[Decree 330 Commodities Exchange In Tttc]] — commodities trading
- [[Decree 329 Banking And Foreign Exchange]] — cross-border payments
- [[Decree 324 Financial Policies Of Tttc]] — tax incentives on trade
- [[Decree 326 Land And Environment In Tttc]] — warehousing and logistics zones

## Related Topics
- [[Cross Border Payments In The Vietnam International Financial Centre]]
- [[Financial Products And Instruments In The Vietnam International Financial Centre]]
- [[Tax Incentives In The Vietnam International Financial Centre]]
- [[Process Map How Foreign Companies Cooperate With Vifc]]
"""

FINTECH_PROCESS = """
# Process Map — How Fintech Companies Cooperate With VIFC

## Fintech Cooperation Flowchart

```mermaid
flowchart TD
    A([💻 Fintech Company\nDecides to Enter VIFC]) --> B{Sandbox or\nFull License?}

    B -->|Regulatory Sandbox\nFirst| C[Apply for Controlled\nTesting Mechanism\ncơ chế thử nghiệm có kiểm soát]
    B -->|Full License\nDirect| D[Full Financial\nLicense Path]

    C --> E[Sandbox Documents:\n• Technology description\n• Risk assessment\n• Consumer protection plan\n• Exit strategy\n• Capital proof]

    E --> F[Submit to VIFC\nFintech Regulatory Authority]
    F --> G{Authority Review\n30 Days}
    G -->|Rejected| H[Revise Proposal]
    H --> F
    G -->|Approved| I[Enter Sandbox\nMax 2 Year Period]

    I --> J[Operate Under\nControlled Conditions:\n• Limited user base\n• Transaction caps\n• Monthly reporting]

    J --> K{Sandbox\nResults}
    K -->|Successful| L[Apply for\nFull Operating License]
    K -->|Issues Found| M[Remediate &\nExtend Sandbox]
    M --> J

    D --> L
    L --> N[Full AML/KYC\nCompliance Setup]
    N --> O[Data Protection\nRegistration]
    O --> P([✅ Fintech Fully\nLicensed at VIFC])

    P --> Q[Ongoing:\nMonthly Reports\nAnnual Audit\nLicense Renewal]

    style A fill:#1c2f72,color:#fff
    style P fill:#00aeef,color:#fff
    style G fill:#f0f7ff,color:#1c2f72
    style K fill:#f0f7ff,color:#1c2f72
    style Q fill:#fff7e6,color:#b45309
```

## Key Requirements

### Regulatory Sandbox Entry
- Innovative financial technology with clear use case
- Consumer protection and risk mitigation plan
- Technical documentation of the solution
- Exit/wind-down strategy
- Minimum capital as required

### Full License Requirements
- Completed sandbox (or equivalent overseas track record)
- Full AML/KYC compliance programme
- Data localisation compliance
- Cybersecurity assessment

## Applicable Decrees
- [[Special Legal Mechanisms In The Vietnam International Financial Centre]] — sandbox framework
- [[Decree 329 Banking And Foreign Exchange]] — payment fintech
- [[Decree 324 Financial Policies Of Tttc]] — tax incentives

## Related Topics
- [[Co Che Thu Nghiem Co Kiem Soat In The Context Of Tttc]]
- [[Compliance Requirements In The Vietnam International Financial Centre]]
- [[Process Map How Foreign Companies Cooperate With Vifc]]
"""

INVESTMENT_BANKS_PROCESS = """
# Process Map — How Investment Banks Cooperate With VIFC

## Investment Banking Cooperation Flowchart

```mermaid
flowchart TD
    A([🏛️ Investment Bank\nDecides to Enter VIFC]) --> B[Determine Service Scope:\n• ECM / DCM\n• M&A Advisory\n• Fund Management\n• Securities Brokerage]

    B --> C[Prepare License\nApplication Package]

    C --> D[Documents Required:\n• Home country IB license\n• Audited financials 3 years\n• Fit & proper — directors\n• Compliance programme\n• Capital adequacy proof\n• Business plan]

    D --> E[Submit to State Securities\nCommission of Vietnam — SSC\nvia VIFC Authority]

    E --> F{SSC Review\n30–60 Days}
    F -->|Rejected| G[Address\nDeficiencies]
    G --> E
    F -->|Approved| H[Receive Securities\nOperating License]

    H --> I[Register Capital\nMarkets Activities with SSC]
    I --> J[Apply for Tax\nIncentives — Decree 324]
    J --> K[Establish AML/KYC\nProgramme — Decree 329]
    K --> L[Register Reporting\nObligations]
    L --> M[Hire / Transfer\nKey Personnel\nWork Permits — Decree 325]
    M --> N([✅ Investment Bank\nOperational at VIFC])

    N --> O[Ongoing:\nQuarterly SSC Reports\nAnnual Audit\nClient Asset Reporting]

    style A fill:#1c2f72,color:#fff
    style N fill:#00aeef,color:#fff
    style F fill:#f0f7ff,color:#1c2f72
    style O fill:#fff7e6,color:#b45309
```

## Key Requirements

- Valid securities / investment banking license from home jurisdiction
- Minimum 3 years operating history
- Capital adequacy meeting VIFC requirements
- Fit and proper assessment for all licensed representatives
- Segregated client asset accounts
- Compliance officer designated for VIFC operations

## Services Permitted at VIFC
- Equity and debt capital markets underwriting
- Mergers and acquisitions advisory
- Securities brokerage and market making
- Fund structuring and management
- Derivatives and structured products (subject to approval)

## Applicable Decrees
- [[Decree 329 Banking And Foreign Exchange]] — securities and FX
- [[Decree 324 Financial Policies Of Tttc]] — tax incentives
- [[Decree 323 Establishment Of Tttc]] — governance
- [[Decree 325 Labor And Social Security In Tttc]] — key personnel

## Related Topics
- [[Investment Banking Opportunities In The Vietnam International Financial Centre]]
- [[Equity Capital Markets In The Vietnam International Financial Centre]]
- [[Debt Capital Markets In The Vietnam International Financial Centre]]
- [[Securities Activities In The Vietnam International Financial Centre]]
- [[Process Map How Foreign Companies Cooperate With Vifc]]
"""

BENCHMARKING_MAP = """
# VIFC Cooperation Process — IFC Benchmarking Map

This page maps VIFC's cooperation process against other major international financial centres
for cross-reference and regulatory improvement purposes.

## High-Level Process Comparison

```mermaid
flowchart LR
    subgraph VIFC ["🇻🇳 VIFC (Vietnam)"]
        V1[Application\nSubmission] --> V2[Authority Review\n15–60 Days]
        V2 --> V3[License\nIssued]
        V3 --> V4[Tax Incentive\nApplication]
        V4 --> V5[AML/KYC\nSetup]
        V5 --> V6[Operational]
    end

    subgraph SGP ["🇸🇬 MAS (Singapore)"]
        S1[Application\nSubmission] --> S2[MAS Review\n6–12 Months]
        S2 --> S3[License\nIssued]
        S3 --> S4[MAS Ongoing\nSupervision]
        S4 --> S5[Operational]
    end

    subgraph HKG ["🇭🇰 SFC (Hong Kong)"]
        H1[Application\nSubmission] --> H2[SFC Review\n3–6 Months]
        H2 --> H3[License\nIssued]
        H3 --> H4[Ongoing\nReporting]
        H4 --> H5[Operational]
    end

    subgraph DIFC ["🇦🇪 DFSA (Dubai)"]
        D1[Application\nSubmission] --> D2[DFSA Review\n2–4 Months]
        D2 --> D3[License\nIssued]
        D3 --> D4[Ongoing\nSupervision]
        D4 --> D5[Operational]
    end

    style VIFC fill:#e8f4fd,stroke:#1c2f72
    style SGP fill:#f0fff4,stroke:#276749
    style HKG fill:#fff5f5,stroke:#c53030
    style DIFC fill:#fffff0,stroke:#b7791f
```

## Detailed Benchmarking Table

| Criteria | VIFC 🇻🇳 | Singapore MAS 🇸🇬 | Hong Kong SFC 🇭🇰 | Dubai DIFC 🇦🇪 |
|----------|----------|------------------|------------------|----------------|
| **Review Period** | 15–60 days | 6–12 months | 3–6 months | 2–4 months |
| **Corporate Tax Rate** | Incentivised (Decree 324) | 17% | 16.5% | 0% (DIFC zone) |
| **Min. Capital (Bank)** | Per Decree 329 | SGD 1.5B+ | HKD 300M+ | USD 10M+ |
| **Foreign Ownership** | Per decree | 100% allowed | 100% allowed | 100% allowed |
| **Dispute Resolution** | Vietnamese courts / arbitration | SIAC | HKIAC | DIAC |
| **Regulatory Sandbox** | Available (Decree mechanism) | MAS Fintech Sandbox | HKMA Sandbox | DFSA Innovation Testing |
| **Language** | Vietnamese / English | English | English / Chinese | English |
| **AML Standard** | FATF-aligned | FATF | FATF | FATF |
| **Passporting** | ASEAN frameworks | ASEAN / global | ASEAN / global | Limited |

## Areas for VIFC Regulatory Improvement
*(To be completed by VIFC team based on benchmarking findings)*

- [ ] Review application timeline vs regional peers
- [ ] Assess capital requirements competitiveness
- [ ] Evaluate dispute resolution framework vs SIAC/HKIAC
- [ ] Consider English-language regulatory documentation
- [ ] Review sandbox duration and scope vs MAS/HKMA

## Related Topics
- [[Process Map How Foreign Companies Cooperate With Vifc]]
- [[Process Map How Banks Cooperate With Vifc]]
- [[Dispute Resolution In The Vietnam International Financial Centre]]
- [[Special Legal Mechanisms In The Vietnam International Financial Centre]]
- [[Legal Framework Of Tttc]]
"""


def main():
    WIKI_DIR.mkdir(exist_ok=True)
    (WIKI_DIR / FOLDER).mkdir(exist_ok=True)

    maps = [
        ("process_map_how_foreign_companies_cooperate_with_vifc.md", GENERAL_FOREIGN_COMPANY),
        ("process_map_how_banks_cooperate_with_vifc.md",             BANKS_PROCESS),
        ("process_map_how_import_export_companies_cooperate_with_vifc.md", IMPORT_EXPORT_PROCESS),
        ("process_map_how_fintech_companies_cooperate_with_vifc.md", FINTECH_PROCESS),
        ("process_map_how_investment_banks_cooperate_with_vifc.md",  INVESTMENT_BANKS_PROCESS),
        ("vifc_cooperation_process_ifc_benchmarking_map.md",         BENCHMARKING_MAP),
    ]

    print(f"Creating {len(maps)} process map wikis in wiki/{FOLDER}/\n")
    for filename, content in maps:
        save_process_map(filename, content)

    print(f"\n[done] Process maps created.")
    print("\nNext steps:")
    print("  cd wiki && git add . && git commit -m 'Add VIFC cooperation process maps' && git push")
    print("\nIn Obsidian: open any process map page to see the rendered flowchart.")


if __name__ == "__main__":
    main()
