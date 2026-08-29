-- Import Odoo export into LGE-CRM (idempotent upsert on odoo_id)
-- Usage: psql -d lge -v leads="'/abs/path/odoo_leads_export.json'" -f import_leads.sql
create temp table stage_map (odoo_stage text primary key, our_stage text);
insert into stage_map values
  ('New','new'), ('Contacted','contacted'), ('FollowUp','contacted'),
  ('Replied','replied'), ('Probing','probing'), ('Demo Sent','demo_sent'),
  ('Negotiating','negotiating'), ('Won','closed_won'), ('Lost','closed_lost')
on conflict do nothing;

\if :{?leads}
\else
\echo ERROR: pass -v leads="'/path/odoo_leads_export.json'"
\quit
\endif

insert into crm_lead (odoo_id, name, business, contact_name, phone, mobile, email, stage, source, owner, is_test)
select
  (x->>'id')::bigint,
  coalesce(nullif(x->>'name',''), nullif(x->>'partner_name',''), 'Lead ' || (x->>'id')),
  nullif(x->>'partner_name',''),
  nullif(x->>'contact_name',''),
  nullif(x->>'phone',''),
  nullif(x->>'mobile',''),
  nullif(x->>'email_from',''),
  coalesce(sm.our_stage, 'new'),
  'odoo-import',
  'sanjeev',
  (x->>'id')::bigint = 10421
from jsonb_array_elements(:'leads'::jsonb) as x
left join stage_map sm on sm.odoo_stage = (x->'stage_id'->>1)
on conflict (odoo_id) do update
  set name = excluded.name,
      business = excluded.business,
      contact_name = excluded.contact_name,
      phone = excluded.phone,
      mobile = excluded.mobile,
      email = excluded.email,
      updated_at = now();