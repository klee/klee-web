# Patch-Based Source Transitions

All patches apply to baseline [`0fb7942`](https://github.com/FinnLeh/klee-web/commit/0fb794282143206af18a78ca6d1f79ec7bba3a3b). Counts are additions plus deletions.

| ID | Scope | Patch | Files | Additions | Deletions | Changed lines | SHA-256 |
|---|---|---|---:|---:|---:|---:|---|
| P01 | Focused Ubuntu 22.04 host substitution | [`ubuntu-22.04.patch`](patches/ubuntu-22.04.patch) | 3 | 10 | 10 | 20 | `0166905ad58681d456c12ebc6c0c7a3ec27df828150a3addcd236bd4c382d203` |
| P02 | Focused Ubuntu 26.04 host substitution | [`ubuntu-26.04.patch`](patches/ubuntu-26.04.patch) | 3 | 10 | 10 | 20 | `cca6e0a5d95fcdc3570c3e40d64f7ed063bedc30dea19b45dc06643528789159` |
| P03 | Focused Debian 13 host substitution | [`debian-13.patch`](patches/debian-13.patch) | 4 | 26 | 26 | 52 | `ca7f5457d048a0bb257ef4c8c1e810ec8b8106888f54643887f924ffb679916d` |
| P04 | Focused AWS ElastiCache substitution | [`aws-elasticache.patch`](patches/aws-elasticache.patch) | 6 | 241 | 20 | 261 | `4d363966dde1d82461543e52f698991661ec05d84d9b5ea77f4c31831c1ff674` |
| P05 | AWS Fargate Runner-only screen | [`aws-fargate.patch`](patches/aws-fargate.patch) | 3 | 399 | 0 | 399 | `0eed6ab85d26b201b9a28353109151618596b64f0543faa0f21f78f57357c2b4` |
| P06 | Azure Container Apps Jobs Runner-only screen | [`azure-container-apps.patch`](patches/azure-container-apps.patch) | 3 | 352 | 0 | 352 | `37fb02ebd42a6af687e2fe79191eaedf1dde905587ef016cbef6e8d8b0c2c77d` |
| P07 | Google Cloud Run Jobs Runner-only screen | [`google-cloud-run.patch`](patches/google-cloud-run.patch) | 3 | 380 | 0 | 380 | `9a70c0d598b513cff05bf1ce8bbdeb26d6b9e0bfef8e2187276fc8f9c141b951` |

P01 through P03 exercised the complete single-VM application under a focused host-system contract. P04 changed only the state-service boundary. P05 through P07 launched the unchanged Runner directly and did not implement complete application ports.

The patches contain source only. They exclude provider state, credentials, generated plans, runtime records, and operational observations.
