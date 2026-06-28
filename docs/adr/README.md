# Architecture Decision Records

One sequentially-numbered markdown per major design decision. ADRs are the durable record of decisions that live with the code.

## Format

[Michael Nygard](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions) style. Each ADR has:

1. **Title** (`0007-pick-database.md`, short kebab-case)
2. **Status** (Proposed / Accepted / Superseded by NNNN / Deprecated)
3. **Context** What forces are at play, what constraints exist
4. **Decision** What we chose
5. **Consequences** What becomes easier, what becomes harder, what's now load-bearing

Keep them short. One page is enough for almost every decision. If it needs more, split it.

## Numbering

Sequential, four-digit, never reused. If an ADR is superseded, the new one references the old one and the old one's status flips to `Superseded by NNNN`. Old ADRs stay in the repo as history.

## When to write one

Write an ADR when:

- A decision constrains future choices (picking React over Vue; Redis over RabbitMQ; gVisor over Firecracker).
- A choice is non-obvious enough that a future reader, or future me, will ask "why this?".
- A decision is reversed (write a new ADR explaining the reversal, supersede the old).

Don't write ADRs for:

- Bug fixes.
- Local tactical choices that don't constrain the rest of the system.
- Anything where the answer is obviously the only sensible option.

## Index

| # | Title | Status |
|---|-------|--------|
| 0001 | Stage-based additive architecture | Accepted |
| 0002 | JobStore protocol surface | Accepted |
| 0003 | Src-layout for the backend Python package | Accepted |
| 0004 | Monaco for the in-browser editor | Accepted |
| 0005 | Narrow KleeFlags schema for Stage 1 | Accepted |
| 0006 | Frontend tooling stack | Accepted |
| 0007 | POST /jobs returns JobCreated, not full Job | Accepted |
| 0008 | KleeRunner protocol surface | Accepted |
| 0009 | Per-job containers, not a long-lived runner process | Accepted |
| 0010 | Frontend data layer (openapi-typescript + openapi-fetch + React Query) | Accepted |
| 0011 | Frontend layered architecture (Types / API client / Hooks / Components) | Accepted |
| 0012 | Add query_format to the flag schema | Accepted |
| 0013 | Cancel as a user-triggered halt | Accepted |
| 0014 | RedisJobStore on Redis hashes | Accepted |
| 0015 | Centralised configuration via a Settings object | Accepted |
| 0016 | Job dispatch behind a JobDispatcher seam | Accepted |
| 0017 | Result cache keyed on the submission | Accepted |
| 0018 | At-least-once job delivery and worker-death recovery | Accepted |
