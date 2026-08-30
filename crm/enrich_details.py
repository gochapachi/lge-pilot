#!/usr/bin/env python3
"""enrich_details.py — make crm_lead fully independent of Odoo.

Reads secrets/odoo_leads_export.json (full Odoo export) and upserts every
detail field into crm_lead matched on odoo_id. Idempotent — safe to re-run.

Mapping:
  partner_name -> business        contact_name -> contact_name
  phone        -> phone           mobile       -> mobile
  email_from   -> email           description  -> description
  user_id[1]   -> owner           stage_name   -> odoo_stage
  source_id[1] -> source_ref      is_test      -> odoo_id==10421 (owner WA test lead)

Usage: python3 enrich_details.py
"""
import json, os, sys
import pg8000.native

HERE = os.path.dirname(os.path.abspath(__file__))
EXPORT = os.path.join(HERE, "..", "secrets", "odoo_leads_export.json")
DB = dict(user="root", host="213.199.62.248", port=5434, database="lge", password="Itachi933641")

def val(x):
    return None if x in (False, None, "") else x

def main():
    leads = json.load(open(EXPORT))
    if isinstance(leads, dict):
        leads = leads.get("leads", [])
    con = pg8000.native.Connection(**DB)
    updated = inserted = skipped = 0
    for l in leads:
        oid = l.get("id")
        if not oid:
            skipped += 1
            continue
        stage = l.get("stage_id") or [None, None]
        source = l.get("source_id") or [None, None]
        args = dict(
            p_oid=oid,
            p_name=val(l.get("name")) or f"Odoo lead {oid}",
            p_biz=val(l.get("partner_name")),
            p_contact=val(l.get("contact_name")),
            p_phone=val(l.get("phone")),
            p_mobile=val(l.get("mobile")),
            p_email=val(l.get("email_from")),
            p_desc=val(l.get("description")),
            p_owner=val(l.get("owner") or (l.get("user_id") or [None, None])[1]),
            p_ostage=val(l.get("stage_name")),
            p_sref=val(source[1]) if len(source) > 1 else None,
        )
        # UPDATE existing row by odoo_id; INSERT if missing
        row = con.run(
            "update crm_lead set name=:p_name, business=coalesce(:p_biz, business),"
            " contact_name=coalesce(:p_contact, contact_name), phone=coalesce(:p_phone, phone),"
            " mobile=coalesce(:p_mobile, mobile), email=coalesce(:p_email, email),"
            " description=:p_desc, owner=coalesce(:p_owner, owner),"
            " odoo_stage=:p_ostage, source_ref=:p_sref,"
            " is_test=(:p_oid = 10421)"
            " where odoo_id=:p_oid returning id", **args)
        if row:
            updated += 1
        else:
            con.run(
                "insert into crm_lead (odoo_id, name, business, contact_name, phone, mobile,"
                " email, description, owner, stage, source, source_ref, odoo_stage, is_test)"
                " values (:p_oid, :p_name, :p_biz, :p_contact, :p_phone, :p_mobile, :p_email,"
                " :p_desc, :p_owner, 'new', 'odoo_import', :p_sref, :p_ostage, (:p_oid = 10421))",
                **args)
            inserted += 1
    total = con.run("select count(*) from crm_lead")[0][0]
    with_details = con.run("select count(*) from crm_lead where description is not null")[0][0]
    con.close()
    print(f"updated={updated} inserted={inserted} skipped={skipped} total={total} with_description={with_details}")

if __name__ == "__main__":
    sys.exit(main())
