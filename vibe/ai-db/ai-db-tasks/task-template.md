# AI-DB Task Plan: <task-id>

Tool: <tool-name>
Date: <yyyy-mm-dd>
State: planned

## Goal

<Exact data/schema outcome.>

## Authority And Boundary

- Product/task authority: <relative link>
- Project AI-DB rules: [../rules.md](../rules.md)
- Environment route: <registered route id or pending>
- Mutation authority: not granted by this document

## Evidence And Scope

| Claim/object | Source label | Evidence | Status |
| --- | --- | --- | --- |
|  |  |  | pending |

## Proposed Approach

1. Resolve environment identity and read-only precheck evidence.
2. Author the SQL/result handoff with DryRun, real execution, postcheck and recovery boundaries.
3. User/DBA reviews and separately authorizes any mutation.
4. Record supplied receipts in `sql.md`/`verify.md`; update stable memory only after verification.

## Risk And Recovery

- Maximum scope: <rows/objects/tenants>
- Idempotency/replay: <rule>
- Recovery authority: <accepted contract or blocked>
- Release dependency: <owner/order>

## Verification Plan

- Static SQL and reference checks.
- Read-only precheck in the registered route when separately authorized.
- User/DBA-supplied DryRun/execution/postcheck/recovery evidence.

## Documents

- Create `sql.md` from the global SQL/result template.
- Create `verify.md` for execution, deploy, recovery or handoff evidence.
