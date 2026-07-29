# docs/

In-repo documentation. Currently:

- **`architecture.md`**: how the pieces fit together, the map for a new contributor. Complements the ADRs (why) and the README (how to run).
- **`adr/`**: Architecture Decision Records. One short markdown per major design decision. See `adr/README.md`.
- **`deployment/aws.md`**: provision, activate, upgrade, roll back, and destroy the single-VM AWS EC2 deployment.
- **`deployment/aws-multi-vm.md`**: deploy one web/state VM and one or two private Worker VMs on AWS EC2.
- **`deployment/azure.md`**: provision, operate, and destroy the single-VM Azure deployment.
- **`deployment/host-maintenance.md`**: apply Ubuntu updates to single-VM and role-separated deployments.

Cross-cutting diagrams, runbooks, and deployment guides live here. Component-specific details stay beside their implementation.
