# Product Specs Directory Guide

The `product-specs` directory contains **strategic and product-level documentation** for the ASAP Protocol.

## Directory Structure

```
product-specs/
├── README.md                      # This file
├── strategy/                      # Strategic vision and long-term planning
│   ├── vision-agent-marketplace.md
│   ├── roadmap-to-marketplace.md
│   ├── repository-strategy.md
│   ├── deferred-backlog.md
│   ├── v0-original-specs.md
│   └── user-flow.md
├── decision-records/              # Architecture Decision Records (ADR)
│   ├── README.md                  # Index of decisions
│   ├── 01-architecture.md
│   ├── 02-protocol.md
│   ├── 03-security.md
│   ├── 04-technology.md
│   └── 05-product-strategy.md
└── prd/                           # Product Requirements Documents
    ├── prd-v1-roadmap.md
    ├── prd-v1.1-roadmap.md
    ├── prd-v1.2-roadmap.md
    ├── prd-v1.3-roadmap.md
    ├── prd-v1.4-roadmap.md
    ├── prd-v2.0-roadmap.md
    └── prd-review-schedule.md
```

## Key Documents

### Strategy (`strategy/`)
- **[Vision](./strategy/vision-agent-marketplace.md)**: North Star for the Agent Marketplace.
- **[Roadmap](./strategy/roadmap-to-marketplace.md)**: Version sequencing from v1.0 to v2.0.
- **[Deferred Backlog](./strategy/deferred-backlog.md)**: Features deprioritized for the Lean Pivot.

### Decisions (`decision-records/`)
- **[Decision Index](./decision-records/README.md)**: Categorized list of all architectural and product decisions.
- Replaces the old monolithic `ADR.md`.

### Requirements (`prd/`)
- Detailed requirements for each version version.
