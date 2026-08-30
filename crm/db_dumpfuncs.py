#!/usr/bin/env python3
"""Dump full definitions of the 4 portal RPCs + table ACLs (read-only)."""
import pg8000.native

C = pg8000.native.Connection('root', host='213.199.62.248', port=5434,
                             database='lge', password='Itachi933641')

for sig in ["client_analytics(text,integer)", "client_assets(text)",
            "client_tickets(text)", "client_create_ticket(text,text,text)"]:
    print('=' * 20, sig, '=' * 20)
    rows = C.run(f"select pg_get_functiondef('{sig}'::regprocedure)")
    print(rows[0][0])

print('=' * 20, 'owner check', '=' * 20)
rows = C.run("""select p.proname, pg_get_userbyid(p.proowner) as owner
                from pg_proc p join pg_namespace n on n.oid=p.pronamespace
                where n.nspname='public' and p.proname like 'client%'
                order by p.proname""")
for r in rows:
    print(r)

print('=' * 20, 'clients/credentials ACL', '=' * 20)
rows = C.run("select relname, relacl from pg_class where relname in ('clients','credentials') and relnamespace='public'::regnamespace")
for r in rows:
    print(r)
