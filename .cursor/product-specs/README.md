# Product Specs Directory Guide

This directory acts as the **Strategic Level** documentation, sitting above the Product Level (PRD) and Execution Level (Tasks).

## File Purposes

### 1. `vision-agent-marketplace.md` (The North Star)
*   **Purpose**: **Architectural Alignment**.
*   **When to use**: When facing complex technical design decisions (e.g., "Should we use JWT or opaque tokens?"). Consult this doc to verify which decision aligns with the v2.0 Marketplace vision.
*   **Role**: Prevents short-term decisions that could block future capabilities (e.g., creating an auth system that doesn't support federation).

### 2. `roadmap-to-marketplace.md` (The Strategic Map)
*   **Purpose**: **Version Sequencing**.
*   **When to use**: Planning the "theme" of each version (PRD). It explains *why* v1.1 focuses on Identity (to support Trust in v1.2, which supports Economy in v1.3).
*   **Role**: Connects current reality (v1.0) to the vision (v2.0), ensuring each release is a solid stepping stone.

---

## 💡 Previous Organization Note

This directory was previously named `vision`. It has been renamed to `product-specs` to better reflect its strategic nature. The tactical backlog file `v1.1-planned-features.md` has been moved to `tasks/v1.1.0/backlog-v1.1.md` to strictly separate Strategy (this folder) from Execution (tasks folder).
