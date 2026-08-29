-- ============================================================
-- GTM Control Tower — Supabase schema v1
-- Run this ONCE in Supabase Dashboard ▸ SQL Editor ▸ New query
-- ============================================================

-- ---------- Clients (closed/won customers; also powers client portal) ----------
create table if not exists clients (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  business text,
  niche text,
  city text default 'Kanpur',
  phone text,
  email text,
  access_code text unique,                -- client portal login (share with client)
  package text check (package in ('trial','annual','custom')) default 'trial',
  status text check (status in ('onboarding','active','paused','churned')) default 'onboarding',
  started_at timestamptz default now(),
  notes text,
  created_at timestamptz default now()
);

-- ---------- Leads (sales pipeline) ----------
create table if not exists leads (
  id uuid primary key default gen_random_uuid(),
  name text,
  business text,
  niche text,
  city text default 'Kanpur',
  phone text,
  email text,
  stage text check (stage in ('new','contacted','replied','probing','demo_sent','negotiating','closed_won','closed_lost')) default 'new',
  source text default 'manual',
  score int default 0,                    -- 0-100, hot lead heat
  next_action text,
  next_action_at timestamptz,
  odoo_id text,
  tags text[] default '{}',
  notes text,
  is_test boolean default false,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- ---------- Messages (chunked human-style chat log) ----------
create table if not exists messages (
  id uuid primary key default gen_random_uuid(),
  lead_id uuid references leads(id) on delete cascade,
  client_id uuid references clients(id) on delete set null,
  direction text check (direction in ('out','in')) not null,
  kind text check (kind in ('text','image','video','pdf','audio')) default 'text',
  body text,
  chunks jsonb default '[]',              -- array of {text, delay_s} sent as separate bubbles
  wa_id text,                             -- Evolution API message id
  status text check (status in ('queued','sent','delivered','read','failed','received')) default 'queued',
  created_at timestamptz default now()
);

-- ---------- Outreach log ----------
create table if not exists outreach_log (
  id uuid primary key default gen_random_uuid(),
  lead_id uuid references leads(id) on delete cascade,
  template text,
  variant int default 1,
  day_no int default 1,
  channel text default 'whatsapp',
  status text check (status in ('sent','failed','skipped')) default 'sent',
  detail text,
  created_at timestamptz default now()
);

-- ---------- Demos ----------
create table if not exists demos (
  id uuid primary key default gen_random_uuid(),
  lead_id uuid references leads(id) on delete cascade,
  type text check (type in ('video','custom_site','custom_blog','placard_sample','carousel_sample')) default 'video',
  title text,
  asset_url text,
  feedback text,
  sent_at timestamptz default now()
);

-- ---------- Payments ----------
create table if not exists payments (
  id uuid primary key default gen_random_uuid(),
  lead_id uuid references leads(id) on delete set null,
  client_id uuid references clients(id) on delete set null,
  amount numeric not null,
  currency text default 'INR',
  type text check (type in ('trial','annual','placard','setup','upsell')) default 'trial',
  gateway_ref text,
  status text check (status in ('link_sent','paid','failed','refunded')) default 'link_sent',
  created_at timestamptz default now()
);

-- ---------- Deliverable assets (service delivery) ----------
create table if not exists assets (
  id uuid primary key default gen_random_uuid(),
  client_id uuid references clients(id) on delete cascade,
  lead_id uuid references leads(id) on delete set null,
  type text check (type in ('blog','google_post','carousel','infographic','video','placard','report')) not null,
  title text,
  file_url text,
  status text check (status in ('draft','in_review','approved','published','delivered')) default 'draft',
  due_date date,
  created_at timestamptz default now()
);

-- ---------- Support tickets ----------
create table if not exists tickets (
  id uuid primary key default gen_random_uuid(),
  client_id uuid references clients(id) on delete cascade,
  lead_id uuid references leads(id) on delete set null,
  title text not null,
  description text,
  priority text check (priority in ('low','normal','high')) default 'normal',
  status text check (status in ('open','in_progress','resolved')) default 'open',
  sla_due timestamptz default (now() + interval '24 hours'),
  resolved_at timestamptz,
  created_at timestamptz default now()
);

-- ---------- Escalations (needs the boss) ----------
create table if not exists escalations (
  id uuid primary key default gen_random_uuid(),
  lead_id uuid references leads(id) on delete cascade,
  client_id uuid references clients(id) on delete set null,
  reason text check (reason in ('pricing_exception','custom_request','angry_customer','payment_issue','tech_blocker','other')) not null,
  detail text,
  status text check (status in ('open','handled')) default 'open',
  resolution text,
  resolved_at timestamptz,
  created_at timestamptz default now()
);

-- ---------- Daily delivery analytics (per client) ----------
create table if not exists analytics_daily (
  id uuid primary key default gen_random_uuid(),
  client_id uuid references clients(id) on delete cascade,
  day date not null default current_date,
  reviews_received int default 0,
  reviews_replied int default 0,
  avg_review_rating numeric(2,1),
  blogs_published int default 0,
  posts_published int default 0,
  assets_delivered int default 0,
  traffic_users int,
  leads_captured int default 0,
  notes jsonb,
  created_at timestamptz default now(),
  unique (client_id, day)
);

-- ---------- Credential vault (ENCRYPTED client-side; service-role only reads) ----------
create table if not exists credentials (
  id uuid primary key default gen_random_uuid(),
  client_id uuid references clients(id) on delete cascade,
  label text not null,                    -- e.g. "WordPress admin", "GBP login"
  secret_enc text not null,               -- "v1:salt_b64:iv_b64:ciphertext_b64" (AES-GCM)
  created_by text default 'owner',
  last_used_at timestamptz,
  created_at timestamptz default now()
);

-- ---------- Generic event stream (for Today feed) ----------
create table if not exists events (
  id uuid primary key default gen_random_uuid(),
  type text not null,
  lead_id uuid references leads(id) on delete set null,
  client_id uuid references clients(id) on delete set null,
  payload jsonb,
  created_at timestamptz default now()
);

-- ---------- Indexes ----------
create index if not exists idx_leads_stage on leads(stage);
create index if not exists idx_leads_next_action on leads(next_action_at);
create index if not exists idx_messages_lead on messages(lead_id, created_at);
create index if not exists idx_outreach_created on outreach_log(created_at);
create index if not exists idx_assets_client on assets(client_id, status);
create index if not exists idx_tickets_client_status on tickets(client_id, status);
create index if not exists idx_analytics_client_day on analytics_daily(client_id, day desc);
create index if not exists idx_events_created on events(created_at desc);

-- ============================================================
-- Row Level Security
-- ⚠️ v1 pragmatic mode: owner dashboard uses the anon key in-browser,
-- so these tables are readable/writable by anon. The tool is unlisted and
-- solo-use; lock down with Supabase Auth when you add teammates/clients.
-- credentials has NO anon policy on purpose — only service role (your
-- automations / Hermes) can ever read it, and values are AES-GCM ciphertext.
-- ============================================================
alter table clients         enable row level security;
alter table leads           enable row level security;
alter table messages        enable row level security;
alter table outreach_log    enable row level security;
alter table demos           enable row level security;
alter table payments        enable row level security;
alter table assets          enable row level security;
alter table tickets         enable row level security;
alter table escalations     enable row level security;
alter table analytics_daily enable row level security;
alter table credentials     enable row level security;
alter table events          enable row level security;

create policy "anon_all_clients"     on clients         for all using (true) with check (true);
create policy "anon_all_leads"       on leads           for all using (true) with check (true);
create policy "anon_all_messages"    on messages        for all using (true) with check (true);
create policy "anon_all_outreach"    on outreach_log    for all using (true) with check (true);
create policy "anon_all_demos"       on demos           for all using (true) with check (true);
create policy "anon_all_payments"    on payments        for all using (true) with check (true);
create policy "anon_all_assets"      on assets          for all using (true) with check (true);
create policy "anon_all_tickets"     on tickets         for all using (true) with check (true);
create policy "anon_all_escalations" on escalations     for all using (true) with check (true);
create policy "anon_all_analytics"   on analytics_daily for all using (true) with check (true);
create policy "anon_all_events"      on events          for all using (true) with check (true);
-- credentials: intentionally no policy → anon blocked; service role bypasses RLS.

-- ============================================================
-- Client portal RPCs (access-code scoped; safe for anon calls)
-- ============================================================
create or replace function client_analytics(p_access text, p_days int default 30)
returns table (day date, reviews_received int, reviews_replied int, avg_review_rating numeric,
               blogs_published int, posts_published int, assets_delivered int,
               traffic_users int, leads_captured int)
language sql security definer set search_path = public as $$
  select a.day, a.reviews_received, a.reviews_replied, a.avg_review_rating,
         a.blogs_published, a.posts_published, a.assets_delivered,
         a.traffic_users, a.leads_captured
  from analytics_daily a
  join clients c on c.id = a.client_id
  where c.access_code = p_access and a.day > current_date - p_days
  order by a.day desc;
$$;

create or replace function client_assets(p_access text)
returns table (type text, title text, file_url text, status text, due_date date, created_at timestamptz)
language sql security definer set search_path = public as $$
  select a.type, a.title, a.file_url, a.status, a.due_date, a.created_at
  from assets a join clients c on c.id = a.client_id
  where c.access_code = p_access
  order by a.created_at desc limit 100;
$$;

create or replace function client_tickets(p_access text)
returns table (id uuid, title text, description text, status text, priority text, created_at timestamptz)
language sql security definer set search_path = public as $$
  select t.id, t.title, t.description, t.status, t.priority, t.created_at
  from tickets t join clients c on c.id = t.client_id
  where c.access_code = p_access
  order by t.created_at desc limit 50;
$$;

create or replace function client_create_ticket(p_access text, p_title text, p_desc text default null)
returns uuid
language plpgsql security definer set search_path = public as $$
declare v_client uuid; v_id uuid;
begin
  select id into v_client from clients where access_code = p_access;
  if v_client is null then raise exception 'invalid access code'; end if;
  insert into tickets (client_id, title, description, status)
  values (v_client, p_title, p_desc, 'open') returning id into v_id;
  insert into escalations (client_id, reason, detail)
  values (v_client, 'other', 'New client ticket: ' || p_title);
  return v_id;
end;
$$;

-- ============================================================
-- SEED: your own test lead (full lifecycle drill)
-- ============================================================
insert into leads (name, business, niche, city, phone, stage, source, is_test, notes)
values ('Test Lead — Dental Wellness', 'Dental Wellness Clinic', 'dentist', 'Kanpur',
        'REPLACE_WITH_YOUR_WHATSAPP', 'new', 'test', true,
        'Owner-run full lifecycle drill: outreach→probing→demo→close→payment→onboarding→delivery→upsell')
on conflict do nothing;