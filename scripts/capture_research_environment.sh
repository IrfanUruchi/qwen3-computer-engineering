#!/usr/bin/env bash
set -euo pipefail

out="${1:-research/hardware/environment-$(date +%Y%m%d-%H%M%S).txt}"

mkdir -p "$(dirname "$out")"

{
    echo "========================================================================"
    echo "Qwen3 CE Research Environment"
    echo "========================================================================"
    echo
    echo "Timestamp:"
    date --iso-8601=seconds
    echo
    echo "Git commit:"
    git rev-parse HEAD
    echo
    echo "Git status:"
    git status --short
    echo
    echo "Kernel:"
    uname -a
    echo
    echo "OS:"
    cat /etc/os-release 2>/dev/null || true
    echo
    echo "Python:"
    python3 --version
    echo
    echo "CPU:"
    lscpu 2>/dev/null || true
    echo
    echo "Memory:"
    free -h 2>/dev/null || true
    echo
    echo "NVIDIA:"
    nvidia-smi 2>/dev/null || true
    echo
    echo "Python packages:"
    python3 -m pip freeze 2>/dev/null || true
} > "$out"

echo "Environment captured: $out"
