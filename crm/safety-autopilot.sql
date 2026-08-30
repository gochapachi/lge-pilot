-- safety-autopilot.sql — blast-protection rail (2026-08-30)
-- The agentic columns defaulted every lead to autopilot=true. Until the pilot
-- drill passes, ONLY the test lead (odoo_id 10421, owner's own WhatsApp) may
-- be on autopilot. Re-enable others deliberately, in batches, after the gate.

update crm_lead set autopilot = is_test;

-- verify: expect autopilot=true -> 1 row (Dental Wellness), false -> 1330
