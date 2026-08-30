-- v3-agentic.sql — Agentic CRM layer for crm_lead (idempotent)
-- Adds: per-lead AI steering + autopilot + AI status + next actions + score,
--       Odoo detail columns (import provenance), extended activity kinds,
--       credentials lockdown for the anon API role.
-- Applied: 2026-08-30 (pilot, staging phase)

-- 1. agentic columns ---------------------------------------------------------
alter table crm_lead add column if not exists steering        text;                 -- owner instruction to the AI
alter table crm_lead add column if not exists autopilot       boolean default true; -- AI allowed to act?
alter table crm_lead add column if not exists ai_note         text;                 -- what the AI is doing now
alter table crm_lead add column if not exists next_action     text;
alter table crm_lead add column if not exists next_action_at  timestamptz;
alter table crm_lead add column if not exists score           int default 0;

-- 2. odoo detail columns (full independence from Odoo) ------------------------
alter table crm_lead add column if not exists description     text;   -- odoo lead description/notes
alter table crm_lead add column if not exists odoo_stage      text;   -- original odoo stage name
alter table crm_lead add column if not exists source_ref      text;   -- odoo source_id name

-- 3. activity kinds: steering (owner prompts) + ai (AI actions) ---------------
alter table crm_activity drop constraint if exists crm_activity_kind_check;
alter table crm_activity add constraint crm_activity_kind_check
  check (kind in ('note','wa_msg','call','demo','payment','stage','escalation','steering','ai'));

-- 4. indexes for the autopilot scheduler -------------------------------------
create index if not exists crm_lead_next_action_ix on crm_lead(next_action_at) where next_action_at is not null;
create index if not exists crm_lead_autopilot_ix   on crm_lead(autopilot) where autopilot;

-- 5. updated_at touch trigger (idempotent re-apply) ---------------------------
create or replace function touch_updated_at() returns trigger
language plpgsql as $f$
begin
  new.updated_at = now();
  return new;
end $f$;
drop trigger if exists crm_lead_touch on crm_lead;
create trigger crm_lead_touch
  before update on crm_lead
  for each row execute function touch_updated_at();

-- 6. harden: the public anon role must NOT touch the credential vault ---------
revoke all privileges on table credentials from lge_anon;

-- NOTE (pilot risk, accepted): clients table stays readable by lge_anon so the
-- dashboard Analytics tab can show portal access codes. The whole dashboard is
-- unauthenticated in the pilot; add a PIN gate before real client data lands.
