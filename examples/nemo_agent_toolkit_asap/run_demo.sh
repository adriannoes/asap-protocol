#!/usr/bin/env bash
# Launcher for NeMo Agent Toolkit ↔ ASAP Path A demo (v2.5.3 S1c).
# Usage (from anywhere):
#   ./examples/nemo_agent_toolkit_asap/run_demo.sh smoke|smoke-stdio|nat|help
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"

usage() {
  cat <<'EOF'
Usage: run_demo.sh <command>

  smoke         ASAP-side in-process smoke (no nvidia-nat, no NIM)
  smoke-stdio   ASAP-side smoke + stdio MCPClient subprocess
  nat           Run nat with configs/config-mcp-client-stdio.yml (needs nvidia-nat + NIM)
  help          Show this help

Examples:
  ./examples/nemo_agent_toolkit_asap/run_demo.sh smoke
  ./examples/nemo_agent_toolkit_asap/run_demo.sh smoke-stdio
  NVIDIA_API_KEY=... ./examples/nemo_agent_toolkit_asap/run_demo.sh nat
EOF
}

cmd="${1:-help}"

case "${cmd}" in
  smoke)
    exec uv run python examples/nemo_agent_toolkit_asap/smoke_asap_side.py
    ;;
  smoke-stdio)
    exec uv run python examples/nemo_agent_toolkit_asap/smoke_asap_side.py --stdio
    ;;
  nat)
    if ! command -v nat >/dev/null 2>&1; then
      echo "SKIP: 'nat' CLI not found. Install optional pin:" >&2
      echo "  uv pip install -r examples/nemo_agent_toolkit_asap/requirements.txt" >&2
      echo "ASAP-side smoke does not need NAT: ./examples/nemo_agent_toolkit_asap/run_demo.sh smoke" >&2
      exit 0
    fi
    if [[ -z "${NVIDIA_API_KEY:-}" ]]; then
      echo "WARNING: NVIDIA_API_KEY unset — NIM react_agent will likely fail." >&2
      echo "Prefer ASAP smoke without NIM: ./examples/nemo_agent_toolkit_asap/run_demo.sh smoke" >&2
    fi
    exec nat run \
      --config_file examples/nemo_agent_toolkit_asap/configs/config-mcp-client-stdio.yml \
      --input "${NAT_INPUT:-Call echo with message hello, then secure_action with action demo}"
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    echo "Unknown command: ${cmd}" >&2
    usage >&2
    exit 2
    ;;
esac
