-- harden-api.sql — LGE pilot API hardening (applied 2026-08-30)
-- Context: PostgREST (/api via Traefik) authenticates as lge_anon. This script:
--   1. creates the missing crm_activity table (was never applied to live DB)
--   2. adds least-privilege authenticator role lge_rest (connection role for lge-rest)
--   3. revokes direct lge_anon access to clients + credentials (portal RPCs are
--      SECURITY DEFINER owned by itachi_admin (superuser), so portal keeps working)
--   4. grants lge_anon minimal DML on crm_lead/crm_activity for dashboard Sales wiring
--   5. adds updated_at trigger on crm_lead
-- Idempotent. ON_ERROR_STOP recommended.

-- 1. crm_activity ------------------------------------------------------------
create table if not exists crm_activity (
  id          bigserial primary key,
  lead_id     bigint references crm_lead(id) on delete cascade,
  kind        text not null check (kind in ('note','wa_msg','call','demo','payment','stage','escalation')),
  detail      text,
  meta        jsonb,
  created_at  timestamptz default now()
);
create index if not exists crm_activity_lead_ix on crm_activity(lead_id, created_at desc);

-- 2. authenticator role ------------------------------------------------------
do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'lge_rest') then
    create role lge_rest login password 'LgeRestPilot26';
  end if;
end $$;
grant lge_anon to lge_rest;

-- 3. tighten lge_anon --------------------------------------------------------
revoke all privileges on table clients    from lge_anon;
revoke all privileges on table credentials from lge_anon;
revoke truncate, references on crm_lead     from lge_anon;
revoke truncate, references on crm_activity from lge_anon;

-- 4. crm grants for the dashboard -------------------------------------------
grant select, update on crm_lead    to lge_anon;
grant select, insert on crm_activity to lge_anon;
grant usage, select on sequence crm_lead_id_seq     to lge_anon;
grant usage, select on sequence crm_activity_id_seq to lge_anon;

-- 5. updated_at touch trigger ------------------------------------------------
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
