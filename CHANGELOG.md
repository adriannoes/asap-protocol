# Changelog

All notable changes to the ASAP Protocol specification will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to hybrid versioning: `Major.YYYY.MM`.

## [Unreleased]

### Added
- Initial protocol specification (DRAFT v1.2025.01)
- Core concepts: Agent, Manifest, Conversation, Task, Message, Part, Artifact, StateSnapshot
- Message types: TaskRequest, TaskResponse, TaskUpdate, TaskCancel, StateQuery, StateRestore
- MCP integration payloads: McpToolCall, McpToolResult, McpResourceFetch, McpResourceData
- Task state machine with 8 states: submitted, working, input_required, paused, completed, failed, cancelled, rejected
- Deployment patterns: direct, orchestrated, mesh
- Error taxonomy with 6 categories and 18 error codes
- Security considerations with optional request signing
- Observability with correlation IDs and metrics exposure

### Decided (via Critical Analysis)
- State persistence: Mode-selectable (snapshot default, event-sourced opt-in)
- Transport binding: JSON-RPC prioritized for A2A/MCP alignment
- Topology: Replaced fixed P2P default with context-based deployment patterns
- Consistency model: Causal consistency for task state
- Versioning: Hybrid Major.YYYY.MM format
- MCP integration: Envelope approach with streaming for large results
- MVP security: Added optional HMAC request signing

## [1.2025.01-draft] - 2025-01-15

- Initial draft specification
