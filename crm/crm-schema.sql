-- LGE-CRM core schema (replaces the Odoo lead layer)
-- Data fully exported to secrets/odoo_leads_export.{json,csv} BEFORE this goes live.
-- Idempotent. Applied after the data stack (infra/lge-stack.yml) is deployed.

create table if not exists crm_lead (
  id            bigserial primary key,
  odoo_id       bigint,
  name          text not null,
  business      text,
  contact_name  text,
  phone         text,
  mobile        text,
  email         text,
  stage text not null default 'new'
    check (stage in ('new','contacted','replied','probing','demo_sent','negotiating','closed_won','closed_lost','followup')),
  source        text default 'manual',
  owner         text,
  is_test       boolean default false,
  created_at    timestamptz default now(),
  updated_at    timestamptz default now()
);

create unique index if not exists crm_lead_odoo_uq on crm_lead(odoo_id) where odoo_id is not null;
create index if not exists crm_lead_stage_ix on crm_lead(stage);
create index if not exists crm_lead_phone_ix on crm_lead(phone);
create index if not exists crm_lead_mobile_ix on crm_lead(mobile);

create table if not exists crm_activity (
  id          bigserial primary key,
  lead_id     bigint references crm_lead(id) on delete cascade,
  kind        text not null check (kind in ('note','wa_msg','call','demo','payment','stage','escalation')),
  detail      text,
  meta        jsonb,
  created_at  timestamptz default now()
);
create index if not exists crm_activity_lead_ix on crm_activity(lead_id, created_at desc);

-- Import (run with: psql -v leads="'/path/odoo_leads_export.json'" -f import_leads.sql)