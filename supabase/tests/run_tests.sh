#!/usr/bin/env bash
set -euo pipefail

echo "================================================================="
echo "Running ApexTender v2.0 Database & pgvector Verification Suite"
echo "================================================================="

python3 "$(dirname "$0")/run_tests.py"

echo "================================================================="
echo "Verification Suite Complete!"
echo "================================================================="
