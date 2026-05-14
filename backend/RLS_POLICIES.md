# Supabase RLS Policies

This document records the row-level security policy set that was applied manually in the Supabase dashboard during Phase 1.

Purpose:
- preserve an auditable copy of the exact policy intent before it is captured in Alembic
- give Phase 3 work a stable reference for auth and tenant-scoping assumptions
- reduce the risk of policy drift between the live Supabase project and git

Status:
- operational source of truth: Supabase dashboard state
- repository source of truth: pending `backend/migrations/versions/009_rls_policies.py`
- related plan item: `P1-010-ALEMBIC`

## Scope

RLS is enabled on these 17 application tables:

- `tenants`
- `users`
- `contracts`
- `schedules`
- `contract_items`
- `running_bills`
- `bill_lines`
- `recoveries`
- `carry_forwards`
- `index_series`
- `index_observations`
- `pvc_rule_sets`
- `pvc_runs`
- `pvc_components`
- `revision_snapshots`
- `extra_item_decisions`
- `documents`

## Policy SQL

### Block 1: Enable RLS

```sql
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE contracts ENABLE ROW LEVEL SECURITY;
ALTER TABLE schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE contract_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE running_bills ENABLE ROW LEVEL SECURITY;
ALTER TABLE bill_lines ENABLE ROW LEVEL SECURITY;
ALTER TABLE recoveries ENABLE ROW LEVEL SECURITY;
ALTER TABLE carry_forwards ENABLE ROW LEVEL SECURITY;
ALTER TABLE index_series ENABLE ROW LEVEL SECURITY;
ALTER TABLE index_observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE pvc_rule_sets ENABLE ROW LEVEL SECURITY;
ALTER TABLE pvc_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE pvc_components ENABLE ROW LEVEL SECURITY;
ALTER TABLE revision_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE extra_item_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
```

### Block 2: Helper Function

This function maps `auth.uid()` to the current tenant via the local `users` table.

```sql
CREATE OR REPLACE FUNCTION public.current_tenant_id()
RETURNS UUID
LANGUAGE sql STABLE SECURITY DEFINER
AS $$
  SELECT tenant_id FROM public.users WHERE supabase_auth_id = auth.uid()
$$;
```

Recommended hardening when codified in Alembic:
- add `SET search_path = public`
- explicitly control function ownership and execute permissions

### Block 3: Table Policies

```sql
-- tenants: can only read own tenant row
CREATE POLICY tenant_self ON tenants
  FOR ALL USING (id = public.current_tenant_id());

-- users: can only see users within own tenant
CREATE POLICY users_own_tenant ON users
  FOR ALL USING (tenant_id = public.current_tenant_id());

-- contracts: direct tenant_id
CREATE POLICY contracts_own_tenant ON contracts
  FOR ALL
  USING (tenant_id = public.current_tenant_id())
  WITH CHECK (tenant_id = public.current_tenant_id());

-- schedules, contract_items: via contract_id
CREATE POLICY schedules_own_tenant ON schedules
  FOR ALL
  USING (
    contract_id IN (
      SELECT id FROM contracts WHERE tenant_id = public.current_tenant_id()
    )
  )
  WITH CHECK (
    contract_id IN (
      SELECT id FROM contracts WHERE tenant_id = public.current_tenant_id()
    )
  );

CREATE POLICY contract_items_own_tenant ON contract_items
  FOR ALL
  USING (
    contract_id IN (
      SELECT id FROM contracts WHERE tenant_id = public.current_tenant_id()
    )
  )
  WITH CHECK (
    contract_id IN (
      SELECT id FROM contracts WHERE tenant_id = public.current_tenant_id()
    )
  );

-- running_bills, pvc_rule_sets, pvc_runs, extra_item_decisions, documents, carry_forwards:
-- via contract_id
CREATE POLICY running_bills_own_tenant ON running_bills
  FOR ALL
  USING (
    contract_id IN (
      SELECT id FROM contracts WHERE tenant_id = public.current_tenant_id()
    )
  )
  WITH CHECK (
    contract_id IN (
      SELECT id FROM contracts WHERE tenant_id = public.current_tenant_id()
    )
  );

CREATE POLICY carry_forwards_own_tenant ON carry_forwards
  FOR ALL
  USING (
    contract_id IN (
      SELECT id FROM contracts WHERE tenant_id = public.current_tenant_id()
    )
  )
  WITH CHECK (
    contract_id IN (
      SELECT id FROM contracts WHERE tenant_id = public.current_tenant_id()
    )
  );

CREATE POLICY pvc_rule_sets_own_tenant ON pvc_rule_sets
  FOR ALL
  USING (
    contract_id IN (
      SELECT id FROM contracts WHERE tenant_id = public.current_tenant_id()
    )
  )
  WITH CHECK (
    contract_id IN (
      SELECT id FROM contracts WHERE tenant_id = public.current_tenant_id()
    )
  );

CREATE POLICY pvc_runs_own_tenant ON pvc_runs
  FOR ALL
  USING (
    contract_id IN (
      SELECT id FROM contracts WHERE tenant_id = public.current_tenant_id()
    )
  )
  WITH CHECK (
    contract_id IN (
      SELECT id FROM contracts WHERE tenant_id = public.current_tenant_id()
    )
  );

CREATE POLICY extra_item_decisions_own_tenant ON extra_item_decisions
  FOR ALL
  USING (
    contract_id IN (
      SELECT id FROM contracts WHERE tenant_id = public.current_tenant_id()
    )
  )
  WITH CHECK (
    contract_id IN (
      SELECT id FROM contracts WHERE tenant_id = public.current_tenant_id()
    )
  );

CREATE POLICY documents_own_tenant ON documents
  FOR ALL
  USING (
    contract_id IN (
      SELECT id FROM contracts WHERE tenant_id = public.current_tenant_id()
    )
  )
  WITH CHECK (
    contract_id IN (
      SELECT id FROM contracts WHERE tenant_id = public.current_tenant_id()
    )
  );

-- bill_lines, recoveries: via bill_id -> running_bills -> contracts
CREATE POLICY bill_lines_own_tenant ON bill_lines
  FOR ALL
  USING (
    bill_id IN (
      SELECT id FROM running_bills
      WHERE contract_id IN (
        SELECT id FROM contracts WHERE tenant_id = public.current_tenant_id()
      )
    )
  )
  WITH CHECK (
    bill_id IN (
      SELECT id FROM running_bills
      WHERE contract_id IN (
        SELECT id FROM contracts WHERE tenant_id = public.current_tenant_id()
      )
    )
  );

CREATE POLICY recoveries_own_tenant ON recoveries
  FOR ALL
  USING (
    bill_id IN (
      SELECT id FROM running_bills
      WHERE contract_id IN (
        SELECT id FROM contracts WHERE tenant_id = public.current_tenant_id()
      )
    )
  )
  WITH CHECK (
    bill_id IN (
      SELECT id FROM running_bills
      WHERE contract_id IN (
        SELECT id FROM contracts WHERE tenant_id = public.current_tenant_id()
      )
    )
  );

-- pvc_components: via run_id -> pvc_runs -> contracts
CREATE POLICY pvc_components_own_tenant ON pvc_components
  FOR ALL
  USING (
    run_id IN (
      SELECT id FROM pvc_runs
      WHERE contract_id IN (
        SELECT id FROM contracts WHERE tenant_id = public.current_tenant_id()
      )
    )
  )
  WITH CHECK (
    run_id IN (
      SELECT id FROM pvc_runs
      WHERE contract_id IN (
        SELECT id FROM contracts WHERE tenant_id = public.current_tenant_id()
      )
    )
  );

-- revision_snapshots: SELECT + INSERT only
CREATE POLICY revision_snapshots_select ON revision_snapshots
  FOR SELECT
  USING (
    run_id IN (
      SELECT id FROM pvc_runs
      WHERE contract_id IN (
        SELECT id FROM contracts WHERE tenant_id = public.current_tenant_id()
      )
    )
  );

CREATE POLICY revision_snapshots_insert ON revision_snapshots
  FOR INSERT
  WITH CHECK (
    run_id IN (
      SELECT id FROM pvc_runs
      WHERE contract_id IN (
        SELECT id FROM contracts WHERE tenant_id = public.current_tenant_id()
      )
    )
  );

-- index series and observations: global read for authenticated users
-- writes are expected to use the backend service key, which bypasses RLS
CREATE POLICY index_series_read ON index_series
  FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY index_observations_read ON index_observations
  FOR SELECT USING (auth.role() = 'authenticated');
```

## Audit Notes

- These policies are consistent with the current schema shape, where many tables do not carry `tenant_id` directly and must be scoped through `contracts`, `running_bills`, or `pvc_runs`.
- `revision_snapshots` is append-only for authenticated application users because there is no `UPDATE` or `DELETE` policy.
- `index_series` and `index_observations` are intentionally global-read because index data is shared across tenants.
- This document is not a substitute for migration-backed infrastructure. Phase 3 should not start until these policies are captured in Alembic as planned.
