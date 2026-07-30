# Delayed Shipments and Exception Handling Policy
**Document type:** Internal Standard Operating Procedure
**Version:** 2.1
**Effective date:** 1 March 2024
**Owner:** Head of Operations
**Review cycle:** Annual

---

## 1. Purpose

This policy defines how delayed shipments and logistics exceptions are classified, investigated, communicated, and resolved. It applies to all domestic and cross-border shipments managed by or on behalf of the company.

The goal is to ensure that every exception is handled consistently, communicated to the affected customer or vendor within the required timeframe, and resolved with the minimum possible additional delay.

---

## 2. Exception classification

All shipment exceptions are classified into one of five categories at the time of detection. Classification determines the notification timeline and escalation path.

### Category A — Documentation hold (customs)
**Definition:** Shipment held at a Saudi port by ZATCA due to missing, incorrect, or incomplete documentation.

Common triggers:
- Incorrect or missing HS code
- Missing importer CR number on commercial invoice
- Certificate of origin absent or expired
- SASO conformity certificate missing for regulated products
- Prior approval not obtained for restricted goods

**Response requirement:**
- Notify client within **1 hour** of receiving ZATCA hold notification on FASAH
- Identify the specific missing document and the responsible party (client or vendor)
- If client documentation is at fault: request the correct document with a deadline
- If vendor error: correct and resubmit within **4 hours**
- Provide revised clearance ETA with each update

### Category B — Carrier operational delay
**Definition:** Shipment delayed due to carrier capacity, vehicle breakdown, route disruption, or facility backlog.

**Response requirement:**
- Notify client within **4 hours** of identifying the delay
- Provide revised ETA
- If delay will exceed 12 hours beyond SLA: escalate to operations manager; consider alternative carrier for remaining leg

### Category C — Cross-border / GCC border hold
**Definition:** Shipment held at a GCC land border (Saudi-UAE, Saudi-Kuwait, Saudi-Jordan, Saudi-Bahrain) for reasons not communicated by the border authority.

**Response requirement:**
- Notify client within **2 hours** of delay being identified at the border
- Contact the carrier's border representative for status; provide update within 4 hours
- If no resolution within 24 hours: escalate to senior operations and consider whether customs broker intervention is needed at the relevant border crossing
- Do not commit to a revised ETA until the hold reason is confirmed — communicate that the cause is under investigation

### Category D — Supplier / vendor delivery failure
**Definition:** Delay caused by the upstream supplier failing to deliver goods to the logistics hub on time, with incorrect quantities, or with missing documentation.

This category is distinct from carrier delays. The failure is at the point of origin, not in transit.

**Response requirement:**
- Notify client within **4 hours** of identifying the supplier failure
- Issue a formal written exception notice to the supplier within the same business day
- Record against the supplier's SLA scorecard (Category 3 — Compliance, Category 4 — Service Quality)
- Provide client with revised shipment pickup date once confirmed by supplier

### Category E — Holiday / force majeure delay
**Definition:** Delay caused by an officially declared Saudi public holiday, a GCC-wide closure, or a force majeure event (natural disaster, government-imposed border closure, port strike).

**Response requirement:**
- For anticipated holidays: notify client at least **48 hours before** the holiday begins with a revised ETA
- For unanticipated force majeure: notify client within **4 hours** of the event becoming known
- Document the event with the official announcement or news reference
- No SLA penalty applies; log as "force majeure" or "public holiday" in the system

---

## 3. Notification requirements

### 3.1 Customer notifications

All customer notifications regarding delayed shipments must include:

1. Shipment reference number
2. Original expected delivery date and time
3. Current status and location of the shipment
4. Exception category and cause (as specifically as known)
5. Revised estimated delivery date and time (if determinable)
6. Name and contact of the operations agent handling the exception
7. Next update time (when the customer can expect the next status communication)

Notifications must be sent via the agreed communication channel (email, WhatsApp, or customer portal). Verbal notifications must be followed by written confirmation within 1 hour.

### 3.2 Internal escalation

| Delay duration | Escalation level |
|---|---|
| 0–4 hours beyond SLA | Operations agent handles; standard communication |
| 4–12 hours beyond SLA | Team leader notified; joins communication chain |
| 12–24 hours beyond SLA | Operations Manager engaged; client relationship manager notified |
| More than 24 hours beyond SLA | Senior management informed; formal exception report required |
| More than 48 hours, cause unknown | Executive escalation; potential legal/insurance implications reviewed |

---

## 4. SLA penalty triggers and exemptions

### 4.1 SLA penalty applies when:

- Delay is caused by a carrier error or capacity failure (Category B)
- Delay is caused by a vendor documentation error in the customs declaration (Category A, vendor fault)
- Delay is caused by a supplier failure (Category D)
- Any exception where the company or its partners are responsible for the root cause

### 4.2 SLA penalty does NOT apply when:

- Delay is caused by an officially declared Saudi public holiday (Category E)
- Delay is caused by incomplete or incorrect documentation provided by the client (Category A, client fault)
- Delay is caused by a force majeure event (Category E)
- Delay is caused by the consignee being unavailable or providing an incorrect address
- Delay is caused by a GCC border closure ordered by a government authority

---

## 5. Documentation and record-keeping

Every exception must be logged in the system within **1 hour** of detection with:

- Shipment reference
- Exception category
- Time of detection
- Responsible party (vendor / client / carrier / external authority)
- Notifications sent (with timestamps)
- Resolution actions taken (with timestamps)
- Final resolution time
- Whether SLA penalty applies (yes / no / pending)

Exceptions are reviewed monthly by the operations manager and used to update vendor SLA scorecards and identify systemic issues.

---

## 6. Repeat exception analysis

If the same exception type recurs three or more times in a calendar month for the same vendor or route:

- A formal root cause analysis is initiated
- The vendor is issued a written performance notice
- A corrective action plan is required within 5 working days
- The vendor's SLA scorecard is updated and reviewed at the next monthly meeting

If the issue recurs for two consecutive months despite a corrective action plan, the contract review process is initiated per the vendor contract terms.