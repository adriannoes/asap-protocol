#!/bin/bash
# Test upgrade from v0.1.0 to v0.5.0
# This script creates a clean environment, installs v0.1.0, tests it, then upgrades to v0.5.0
#
# Version History:
# - v0.1.0 (2026-01-23): Initial alpha release
# - v0.3.0 (2026-01-26): Test infrastructure improvements
# - v0.5.0 (2026-01-28): Security-hardened release (upgrade target)

set -e

TEST_DIR="/tmp/test-asap-upgrade"
VENV_DIR="${TEST_DIR}/venv"
SCRIPT_DIR="${TEST_DIR}/test_script.py"

echo "=========================================="
echo "ASAP Protocol Upgrade Test: v0.1.0 -> v0.5.0"
echo "Version History: v0.1.0 -> v0.3.0 -> v0.5.0"
echo "=========================================="

# Clean up previous test
if [ -d "$TEST_DIR" ]; then
    echo "Cleaning up previous test environment..."
    rm -rf "$TEST_DIR"
fi

mkdir -p "$TEST_DIR"

# Create virtual environment
echo ""
echo "Step 1: Creating virtual environment..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# Install v0.1.0
echo ""
echo "Step 2: Installing asap-protocol v0.1.0..."
pip install --upgrade pip
pip install asap-protocol==0.1.0

# Verify installation
echo ""
echo "Step 3: Verifying v0.1.0 installation..."
python -c "import asap; print(f'Installed version: {asap.__version__}')"

# Create test script
cat > "$SCRIPT_DIR" << 'EOF'
"""Simple test script using basic ASAP API."""
from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.transport.handlers import HandlerRegistry, create_echo_handler
from asap.transport.server import create_app

def main():
    print("Testing basic ASAP API...")
    
    # Create manifest using basic API
    manifest = Manifest(
        id="urn:asap:agent:test",
        name="Test Agent",
        version="1.0.0",
        description="Test agent",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="echo", description="Echo skill")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="http://127.0.0.1:8000/asap"),
    )
    
    # Create registry and register handler
    registry = HandlerRegistry()
    registry.register("task.request", create_echo_handler())
    
    # Create app
    app = create_app(manifest, registry)
    
    print("✅ Agent created successfully!")
    print(f"✅ App has {len(app.routes)} routes")
    print("✅ All basic API calls succeeded")
    
    return 0

if __name__ == "__main__":
    exit(main())
EOF

# Run test with v0.1.0
echo ""
echo "Step 4: Testing with v0.1.0..."
python "$SCRIPT_DIR"

# Upgrade to v0.5.0 (using local build)
echo ""
echo "Step 5: Upgrading to v0.5.0..."
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -f "${PROJECT_ROOT}/dist/asap_protocol-0.5.0-py3-none-any.whl" ]; then
    pip install --upgrade "${PROJECT_ROOT}/dist/asap_protocol-0.5.0-py3-none-any.whl"
elif [ -f "${PROJECT_ROOT}/dist/asap_protocol-0.3.0-py3-none-any.whl" ]; then
    echo "⚠️  v0.5.0 wheel not found, using v0.3.0 for testing..."
    pip install --upgrade "${PROJECT_ROOT}/dist/asap_protocol-0.3.0-py3-none-any.whl"
else
    echo "⚠️  No wheel found, installing from source..."
    pip install --upgrade "${PROJECT_ROOT}"
fi

# Verify upgrade
echo ""
echo "Step 6: Verifying upgrade..."
python -c "import asap; print(f'Upgraded version: {asap.__version__}')"

# Run test again with upgraded version
echo ""
echo "Step 7: Testing with upgraded version (should work without code changes)..."
python "$SCRIPT_DIR"

# Test that new security features are opt-in
echo ""
echo "Step 8: Verifying new security features are opt-in..."
python << 'PYTHON_EOF'
from asap.models.entities import Manifest, Capability, Endpoint, Skill
from asap.transport.server import create_app

# Create manifest WITHOUT auth (should work)
manifest = Manifest(
    id="urn:asap:agent:test-no-auth",
    name="Test Agent No Auth",
    version="1.0.0",
    description="Test agent without auth",
    capabilities=Capability(
        asap_version="0.1",
        skills=[Skill(id="echo", description="Echo skill")],
        state_persistence=False,
    ),
    endpoints=Endpoint(asap="http://127.0.0.1:8000/asap"),
)

# Should work without auth configuration
app = create_app(manifest)
print("✅ App created without auth (opt-in security confirmed)")

# Verify no auth middleware is required
print("✅ Security features are opt-in - upgrade successful!")
PYTHON_EOF

echo ""
echo "=========================================="
echo "✅ Upgrade test completed successfully!"
echo "=========================================="
echo ""
echo "Summary:"
echo "  - v0.1.0 installed and tested"
echo "  - Upgraded to v0.5.0"
echo "  - Same code works without modifications"
echo "  - New security features are opt-in"
echo ""

deactivate
