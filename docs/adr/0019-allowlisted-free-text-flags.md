# 0019. Allowlisted free-text KLEE flags

**Status:** Accepted, 2026-07-05

## Context

ADR-0005 shipped a narrow `KleeFlags` and deferred general flag broadening for power users to a later, concrete decision. This is that decision. The ask is broad flag access for power users, so a curated field per flag (the ADR-0005 pattern, extended once in ADR-0012) does not scale: it caps users at the flags we happened to build a control for.

The tension is safety, but one fact reframes it. The runner already executes attacker-influenced native code. KLEE's default `--external-calls=concrete` lets a program call real libc with concrete arguments, so a user's own C can reach `system("...")` today, with no flags at all. The runner container is therefore already a boundary for running untrusted code, independent of this feature. Broadening flags does not create a new class of risk, it tunes KLEE inside a container that must already be assumed hostile.

## Decision

Add one field, `extra_flags: str` (default `""`), to `KleeFlags`, alongside the existing curated fields. It is a free-text box for power users, validated **default-deny against an allowlist** of vetted flags.

- Validation tokenises with `shlex` and checks each token against the allowlist. Value flags use the `--flag=value` form, so every token validates on its own with no look-ahead. Three value policies: boolean (bare or `=true|false`), bounded integer, and fixed enum. Anything not on the list is rejected with a 422, which the results panel surfaces as the reason a run could not start.
- The initial list is small (the common exploration and solver knobs) and grows only as a flag is reviewed in. The concrete list lives in the code, not here, so it can move without an ADR per flag.
- The channel stays shell-free: `extra_flags` travels as an env var, and the entrypoint `shlex`-splits it into an argv list spliced before the bitcode. No user text is ever interpolated into a shell.
- We pin `--external-calls=concrete` ourselves and keep it, and the other flags we manage (`--output-dir`, `--max-time`, `--max-memory`, `--libc`, `--posix-runtime`, `--write-kqueries`), off the allowlist, so a user can neither override our contract nor broaden the external-call policy.

## Consequences

**Positive**

- Power users get broad, extensible flag access without a UI control per flag.
- Default-deny means unknown, future, or dangerous flags are refused by construction. There is no denylist to keep exhaustive.
- Two independent layers guard the runner: the input allowlist and the container sandbox. We do not lean on the sandbox alone.

**Negative**

- This revises the property ADR-0005 leaned on. A free-text string now does reach the invocation, tokenised. Injection safety no longer comes from forbidding free text, it comes from the no-shell channel plus the allowlist. That is a deliberate weakening of a guarantee 0005 stated absolutely.
- The allowlist is curation work. Every new flag is a manual review, and users will hit "flag not allowed" for flags that are safe but not yet vetted. That friction is the cost of default-deny.
- The allowlist bounds the flag surface, not the base surface. Native execution via a user's own C stays reachable, so this feature does not make the container safe to run untrusted code. The sandbox stays mandatory, and public exposure waits on the Stage 3 hardening (gVisor, `--net=none`, non-root, dropped capabilities, resource caps, a secretless image).
- Value-bearing flags carry a per-flag value policy, a small surface to maintain.

## References

- ADR-0005: narrow KleeFlags schema (the stance this broadens, and whose no-free-text property it revises).
- ADR-0012: query_format flag (the prior scoped addition to the schema).
- ADR-0009: per-job containers (the sandbox layer this leans on for containment).
- ADR-0001: stage-based additive architecture (build the capability now, expose it once Stage 3 makes the sandbox sufficient).
