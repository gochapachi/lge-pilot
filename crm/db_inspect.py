#!/usr/bin/env python3
"""Inspect current RPC definitions + roles/grants in lge DB (read-only)."""
import json
import pg8000.native

C = pg8000.native.Connection('root', host='213.199.62.248', port=5434,
                             database='lge', password='Itachi933641')

print('=== portal RPCs in pg_proc ===')
rows = C.run("""select p.oid::regprocedure::text, l.lanname, p.prosecdef,
                       p.proconfig, p.proacl
                from pg_proc p join pg_namespace n on n.oid = p.pronamespace
                join pg_language l on l.oid = p.prolang
                where n.nspname = 'public'
                  and p.proname in ('client_analytics','client_assets',
                                    'client_tickets','client_create_ticket')""")
for r in rows:
    print(r)

print('=== roles ===')
rows = C.run("""select rolname, rolsuper, rolcanlogin from pg_roles
                where rolname in ('root','lge_anon','lge_rest','lge_admin','authenticated')""")
for r in rows:
    print(r)

print('=== lge_anon memberships of others ===')
rows = C.run("""select r.rolname as member, g.rolname as granted
                from pg_auth_members m
                join pg_roles r on r.oid = m.member
                join pg_roles g on g.oid = m.roleid
                where g.rolname = 'lge_anon' or r.rolname = 'lge_anon'""")
for r in rows:
    print(r)

print('=== grants on clients/credentials ===')
rows = C.run("""select grantee, privilege_type from information_schema.role_table_grants
                where table_schema='public' and table_name in ('clients','credentials')
                order by table_name, grantee""")
for r in rows:
    print(r)

print('=== full functiondef client_analytics ===')
try:
    rows = C.run("select pg_get_functiondef('client_analytics(jsonb)'::regprocedure)")
    print(rows[0][0])
except Exception as e:
    print('ERR', e)
