# ARCHITECTURE — LGE Pilot (v1.0, 31-Aug-2026)

> Companion to `crm/CHATFLOW.md` (the playbook) — this doc is the **structure**:
> how messages flow, how state advances, what lives where. All diagrams are mermaid
> (render natively on GitHub).

## 1) End-to-end outreach & sales sequence (the happy path)

```mermaid
sequenceDiagram
    participant P as Prospect (WhatsApp)
    participant E as Evolution API
    participant B as Bridge (bridge.py 60s poll)
    participant C as Chatflow Engine (FreeLLM)
    participant DB as Postgres (ops + crm)
    participant U as Dashboard UI

    Note over B: D1 morning batch (sender.py --send)
    B->>E: sendText D1 intro
    E-->>P: WhatsApp
    B->>DB: messages(out) + crm_activity + stage=contacted

    P->>E: reply
    B->>E: findMessages poll
    B->>DB: messages(in) + memory append
    B->>C: generate(stage, discovery, steering, history)
    C-->>B: next turn (question / value / asset / close)
    B->>E: sendText reply bubbles
    B->>DB: messages(out) + activity + stage/tag deltas

    Note over B,U: loop: reply → reply → … until closed_won / break-up

    U->>DB: GET /api/messages, /api/leads, /api/crm_lead (same-origin /api)
    U-->>U: Inbox thread · Sales pipeline · cockpit (steering/autopilot)
```

## 2) Conversation state machine (chatflow)

```mermaid
stateDiagram-v2
    [*] --> contacted: D1 sent (source-specific intro, no pitch)
    contacted --> replied: any reply (warm-up, DQ1)
    replied --> probing: discovery loop DQ2–DQ6, one per turn
    probing --> demo_sent: discovery complete + reaction earned → blank demo asset
    probing --> negotiating: price asked directly (skip demo)
    demo_sent --> negotiating: reaction / price ask
    demo_sent --> probing: follow-ups (D2 soft, D3 choice, D5 break-up)
    negotiating --> closed_won: "haan" → Cashfree link → payment confirmed
    negotiating --> probing: objection handled → back to value
    any --> closed_lost: opt-out / hard no (muted forever)
    closed_won --> [*]: onboarding chat (day-1 expectations)
```

## 3) Data flow states per message (write-path invariants)

```mermaid
flowchart LR
    A[inbound WhatsApp] -->|Evolution poll| B[jid → lead match<br/>s.whatsapp.net: phone match<br/>lid: adopt via state map]
    B -->|known/new| C[leads row]
    B --> D[messages row: direction=in]
    B --> E[crm_activity row: kind=wa_msg IN]
    B --> F[chatflow: stage + tags/notes delta]
    D --> G[Dashboard Inbox / drawer]
```

## 4) Entity map (current pilot schema)

```mermaid
erDiagram
    leads ||--o{ messages : "lead_id"
    leads ||--o{ outreach_log : ""
    leads ||--o{ demos : ""
    leads ||--o{ payments : ""
    leads ||--o{ tickets : ""
    leads ||--o{ escalations : ""
    leads ||--o{ crm_activity : "ops↔crm bridge by is_test/phone"
    crm_lead ||--o{ crm_activity : "agentic trail"
    clients ||--o{ messages : ""
    clients ||--o{ analytics_daily : ""
    clients ||--o{ assets : ""
    leads {
        uuid id PK
        text name
        text business
        text stage
        text source
        text phone
        text steering
        bool autopilot
        bool is_test
        text next_action
        timestamptz next_action_at
    }
    messages {
        uuid id PK
        uuid lead_id FK
        text direction
        text body
        jsonb chunks
        text wa_id
        text status
        timestamptz created_at
    }
    crm_lead {
        int id PK
        int odoo_id
        text stage
        text steering
        bool autopilot
        text ai_note
    }
    payments {
        uuid id PK
        uuid lead_id FK
        numeric amount
        text type
        text status
        text gateway_ref
    }
    clients {
        uuid id PK
        text name
        text access_code
        text package
        text status
    }
```

## 5) ERP view — modules of the whole agency (where LGE sits)

```mermaid
flowchart TB
    subgraph ACQ["Acquisition"]
        OUT[Outreach sender]
        BRIDGE[WhatsApp brain<br/>chatflow engine]
        ADS[Meta click-to-WhatsApp ads]
    end
    subgraph CRM2["CRM Core (this repo)"]
        LEADS[(leads + crm_lead)]
        ACT[(crm_activity / messages)]
        CHAT[Chatflow engine]
    end
    subgraph DELIV["Delivery (post-sale)"]
        ASSETS[(assets: blogs/posts/placards)]
        REV[Review gating + AI replies]
        PORTAL[Client portal]
    end
    subgraph FIN["Finance"]
        PAY[(payments: Cashfree)]
        INV[Invoices (manual, pilot)]
    end
    subgraph OPSX["Ops"]
        TCK[(tickets)]
        ESC[(escalations)]
        ANA[(analytics_daily)]
    end
    OUT --> LEADS
    ADS --> LEADS
    LEADS --> CHAT
    CHAT --> ACT
    CHAT -->|stage deltas| LEADS
    CHAT -->|won| PAY
    PAY --> DELIV
    DELIV --> ASSETS
    DELIV --> PORTAL
    DELIV --> TCK
    DELIV --> ESC
    DELIV --> ANA
    PORTAL -->|login code| CLIENTS2[clients]
```

## 6) Guardrails (hard, in bridge.py)
- test thread (`is_test`) → ingest-only, **no auto-replies ever**
- opt-out regex → `stopped` + never message again
- caps: 4/lead/day · 40/day global · 45s anti-burst
- quiet hours 21:30–08:00 IST · groups/status skipped
- single-flight flock (no concurrent passes)
- demo sends = blank assets only until design pipeline approved

## 7) Known gaps → next iterations
| Gap | Plan |
|---|---|
| Demo assets are blanks | design pipeline (ComfyUI/Canva API) later — pending owner check of chatflow first |
| Payment confirm is manual | Cashfree webhook → `payments.status=paid` → auto `closed_won` |
| Single test thread only | 5-thread dry pilot before ramp |
| Sender + bridge split | merge into one scheduling brain (v3) |
| No auth on dashboard | PIN gate before real client data |