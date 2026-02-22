# Registry Verification Review (Admin Guide)

This guide is for maintainers who review **Verified badge** requests for agents in the ASAP Lite Registry. Verification is manual: requests arrive as GitHub issues; after review, you approve or reject via issue comments and (once the protocol schema supports it) update `registry.json`.

## Finding verification requests

1. Open the repository’s **Issues** tab.
2. Filter by labels: `verification-request` and `pending-review`.
3. Each issue is created from the [Request Verification](https://github.com/adriannoes/asap-protocol/blob/main/.github/ISSUE_TEMPLATE/request_verification.yml) form and contains:
   - **Agent ID** (URN) — must already exist in the registry.
   - **Why should this agent be verified?** — justification and trust signals.
   - **How long has it been running?** — approximate duration.
   - **Evidence of reliability** — links to uptime, dashboards, SLA.
   - **Contact info** — how to reach the submitter.

## Review checklist

Use this to decide whether to approve or reject a verification request.

### 1. Agent is listed

- Confirm the **Agent ID** appears in `registry.json` (or the current registry source).
- If the agent is not listed, close the issue and comment that they must register the agent first (via the registration flow).

### 2. Uptime and reliability

- If the issue includes **evidence** (uptime URLs, status pages, dashboards), open the links and check they work and support the claims.
- Prefer agents that have been running for a meaningful period (e.g. weeks or months) and can show stability (e.g. uptime %, SLA).

### 3. Code and transparency (if open source)

- If the agent has a **repository_url** in the registry (or linked in the issue), do a lightweight review:
  - Repo is accessible and looks like a real project.
  - No obvious security or abuse concerns (e.g. hardcoded secrets, obviously malicious behavior).
- You are not required to do a full code audit; focus on basic trust and hygiene.

### 4. Contact and legitimacy

- Use **contact info** from the issue to confirm the submitter is reachable (e.g. GitHub user, email).
- If the request is vague, lacks evidence, or the agent is very new with no history, you may request more information in a comment or reject.

### 5. Decision

- **Approve**: Comment on the issue that the agent is approved for the Verified badge. Once the protocol schema supports a `verification` field (see below), add the verification details to the agent in `registry.json`.
- **Reject**: Comment clearly why (e.g. “Agent not listed”, “Insufficient evidence of uptime”, “Could not verify contact”). Close the issue.

## Updating the registry with verification (after schema support)

Today, the registry and protocol schema do not yet define a `verification` field. When they do (see Task 3.6 in the v2.0 roadmap):

1. Open `registry.json` in the repo.
2. Find the agent entry by **id** (URN).
3. Add a `verification` object, for example:

   ```json
   {
     "id": "urn:asap:agent:username:agent-name",
     "name": "My Agent",
     "verification": {
       "status": "verified",
       "verified_at": "2025-02-21T12:00:00Z"
     }
   }
   ```

4. Commit and push (or open a PR). The web app and clients can then show the Verified badge for that agent.

Until the schema is updated, recording approval in the issue comment is sufficient; you can add the `verification` block to `registry.json` once the codebase supports it.

## Summary

| Step | Action |
|------|--------|
| Find requests | Issues with labels `verification-request`, `pending-review` |
| Vet | Uptime/reliability evidence, code review if open source, contact/legitimacy |
| Respond | Comment approve or reject; close the issue |
| Persist (later) | After 3.6, add `verification` to the agent in `registry.json` |
