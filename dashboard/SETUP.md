# Setup Guide — Dashboard + Supabase + Bridge + Coolify pipeline

## A. Supabase (10 min)
1. supabase.com → New project (free tier fine) → pick a password, region Mumbai
2. SQL Editor → New query → paste ALL of `supabase-schema.sql` → Run
3. Settings ▸ API → copy **Project URL** + **anon public key**
4. Open dashboard → ⚙️ Settings → paste both → Save & test → "✓ connected"

## B. Open the dashboard
- Local: double-click `index.html` (works as plain file)
- Or deploy (next section) and open the URL
- Client portal for clients: `https://your-domain/#/portal` (+ their access code from Analytics tab)

## C. Deploy the dashboard (Coolify, 5 min)
1. Push this folder to a git repo (or use Coolify "upload")
2. Coolify → New resource → Static site → point to repo → deploy…
3. …or fastest: use this Dockerfile concept (nginx serving the folder):
```dockerfile
FROM nginx:alpine
COPY index.html /usr/share/nginx/html/index.html
EXPOSE 80
```
4. Set your domain + Let's Encrypt SSL in Coolify. Done.

## D. Test-lead drill (today, with YOUR WhatsApp)
1. Odoo: your number as lead "Dental Wellness" (or use Supabase seed row — set REPLACE_WITH_YOUR_WHATSAPP in schema or edit the row)
2. Outreach-sender `--test +91XXXXXXXXXX` → you receive the D1 chunks as a lead
3. Reply like a real lead (happy path + one objection)
4. Dashboard ▸ Inbox → open the lead → watch chunks/history → continue conversation
5. Walk the full runbook checklist in `07-test-lead-runbook.md` → fix → rerun

## E. Bridge (n8n ⇄ dashboard/agent) — once Evolution keys arrive
- n8n webhook e.g. `/webhook/wa-bridge` → paste into ⚙️ Settings "bridge URL"
- Contract (dashboards → n8n): `{type:'send_chunks', lead_id, messages:[{text,delay_s}], message_id}`
  n8n loop: Wait(delay_s) → Evolution `sendText` → Supabase PATCH `messages.status='sent'`
- Inbound (Evolution → n8n → Supabase): POST `messages` `{direction:'in', status:'received', lead_id (match by phone→leads.phone)}` + PATCH lead.stage if 'contacted' → stage 'replied' + POST event `{type:'msg_received'}`
- Rate limit: cold sends respect `daily_cap` in outreach-sender config; warm replies unlimited

## F. Coolify → WordPress per client (the "can you build sites?" answer: yes, like this)
1. DNS: wildcard `*.clients.yourdomain.com` A → your VPS IP (one-time)
2. Per client (scriptable via Coolify API — give me the token & I'll drive it):
   - create project → new resource → Docker Compose: `wordpress:latest` + `mariadb`
   - env: WORDPRESS_DB_*, virtual host `clientName.clients.yourdomain.com`, SSL via Let's Encrypt wildcard
   - WP setup: install, create admin, generate **Application Password** (REST publishing)
3. Site population (me, via WP REST `/wp-json/wp/v2/pages|posts`): pages from client logo/details/prompt, theme starter, menus, contact form → n8n webhook
4. Blog publishing: my cron writes → REST POST `posts` with featured image → live
5. Client sees progress in portal; assets pipeline tracks every piece

## G. Security posture (v1 pragmatism)
- Vault secrets: AES-GCM **client-side**, passphrase never leaves your device; DB stores ciphertext only; no anon policy on `credentials` (service-role only)
- Dashboard anon-key mode = OK while solo + unlisted URL; when clients get portal-only access later, add Supabase Auth and tighten RLS (15-min job, listed in schema comments)
- Rotate all platform keys after first 30 days; never paste keys into chat logs you don't control

## H. What runs where (map)
| Piece | Where | Trigger |
|---|---|---|
| Outreach sending (cold, capped) | outreach-sender.py | you/cron daily |
| Conversation agent (replies, follow-ups, closing) | Hermes session/cron + this dashboard | every 10–15 min |
| Instant ack + inbound storage | n8n bridge | Evolution webhook |
| Site/content delivery | Hermes + WP REST + your n8n media workflows | weekly cron per client |
| Reporting to you (hourly) | Hermes cron → your WA | hourly |
| Client portal | #/portal + access code | client anytime |