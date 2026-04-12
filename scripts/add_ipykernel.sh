#!/bin/bash
set -euo pipefail

# =========================================================
# User configuration
# =========================================================
VENV_NAME="dataset_agent"
BASE_DIR="/data/jovillalobos/agentic_workflows/${VENV_NAME}"
VENV_DIR="${BASE_DIR}/.venv"
KERNEL_NAME="venv_${VENV_NAME}"
KERNEL_DIR="$HOME/.local/share/jupyter/kernels/${KERNEL_NAME}"

# =========================================================
# Sanity checks
# =========================================================
echo "========================================"
echo "Creating Jupyter kernel for uv environment"
echo "VENV_DIR: ${VENV_DIR}"
echo "KERNEL_DIR: ${KERNEL_DIR}"
echo "========================================"

if [ ! -d "${VENV_DIR}" ]; then
    echo "ERROR: .venv not found at ${VENV_DIR}"
    exit 1
fi

if [ ! -x "${VENV_DIR}/bin/python" ]; then
    echo "ERROR: Python executable not found in ${VENV_DIR}/bin/python"
    exit 1
fi

# =========================================================
# Ensure ipykernel is installed
# =========================================================
#echo "Ensuring ipykernel is installed..."
#"${VENV_DIR}/bin/python" -m pip install --quiet ipykernel

# =========================================================
# Create kernel launcher script (with logging)
# =========================================================
KERNEL_SCRIPT="${VENV_DIR}/kernel.sh"

echo "Creating kernel launcher at ${KERNEL_SCRIPT}"

cat <<EOF > "${KERNEL_SCRIPT}"
#!/bin/bash
set -euo pipefail

# Log kernel startup for debugging
exec >"\$HOME/jupyter_kernel_${VENV_NAME}.log" 2>&1

VENV_PATH="${VENV_DIR}"

echo "========================================"
echo "Kernel starting..."
echo "Using venv: \$VENV_PATH"
echo "Python: \$VENV_PATH/bin/python"
echo "========================================"

# Execute kernel
exec "\$VENV_PATH/bin/python" -m ipykernel "\$@"
EOF

chmod +x "${KERNEL_SCRIPT}"

# =========================================================
# Create Jupyter kernel spec
# =========================================================
echo "Creating Jupyter kernel spec..."

mkdir -p "${KERNEL_DIR}"

cat <<EOF > "${KERNEL_DIR}/kernel.json"
{
 "argv": [
  "${KERNEL_SCRIPT}",
  "-f",
  "{connection_file}"
 ],
 "display_name": "uv_${VENV_NAME}",
 "language": "python",
 "metadata": {
   "debugger": true
 }
}
EOF

# =========================================================
# Final validation
# =========================================================
echo "Validating kernel..."

"${VENV_DIR}/bin/python" -m ipykernel --version

echo "========================================"
echo "SUCCESS: Kernel created"
echo "Name: uv_${VENV_NAME}"
echo "Path: ${KERNEL_DIR}"
echo "========================================"
echo "You can now select it in Jupyter."
