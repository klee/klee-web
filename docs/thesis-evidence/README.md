# Thesis Source Evidence

This directory supplies source-level traceability for the portability evaluation of KLEE Web. The thesis states the method, results, and limitations without requiring this bundle.

## Contents

- [`committed-transitions.md`](committed-transitions.md) identifies each committed source comparison and its scope.
- [`patch-transitions.md`](patch-transitions.md) identifies experiments whose exact endpoints are retained as patches.
- [`file-inventory.csv`](file-inventory.csv) assigns every changed file to the source categories used in the thesis.
- [`patches/`](patches/) contains those exact patches and their SHA-256 checksums.

Git ranges use `baseline..endpoint`. A single-commit change therefore uses `parent..commit`.

Source and image identities are separate controls. The conventional provider and topology experiments used the immutable application image set built from `500dab0` as their shared control. AWS also exercised an upgrade candidate built from `8f31663`. No frontend, backend, or Runner product source changed between those revisions, although rebuilding unchanged source does not imply byte-identical images. The maintained DoC deployment later adopted the application image set from `7dfc433`.

The inventory categories are application product source, shared deployment, target-specific infrastructure, validation and tooling, documentation, and generated tracked source. Runtime observations, provider state, operational-action accounting, performance, and human effort remain in the thesis evaluation rather than this source bundle.
