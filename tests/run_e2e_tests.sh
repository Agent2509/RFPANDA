#!/usr/bin/env bash
# ==============================================================================
# ApexTender v2.0 — End-to-End (E2E) Test Runner Script
# ==============================================================================
# Runs the 5-tier E2E opaque-box test framework:
#   Tier 1: Feature Coverage (46 tests)
#   Tier 2: Boundary & Corner Cases (35 tests)
#   Tier 3: Cross-Feature Combinations (7 tests)
#   Tier 4: Real-World Application Scenarios (4 tests)
#   Tier 5: Adversarial Stress & Security Hardening (17 tests)
# ==============================================================================

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}==============================================================================${NC}"
echo -e "${BLUE}        APEXTENDER v2.0 — E2E TEST SUITE RUNNER (4-TIER METHODOLOGY)        ${NC}"
echo -e "${BLUE}==============================================================================${NC}"
echo -e "Working Directory: ${PROJECT_ROOT}"
echo -e "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo ""

cd "${PROJECT_ROOT}"

# Set Python path
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH}"

# Check for Python & pytest
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ERROR] python3 not found on PATH.${NC}"
    exit 1
fi

TIER_TARGET="${1:-all}"
EXTRA_ARGS="${@:2}"

case "${TIER_TARGET}" in
    tier1|1)
        echo -e "${YELLOW}Running Tier 1: Feature Coverage Tests...${NC}"
        python3 -m pytest tests/e2e/test_tier1_feature_coverage.py -v ${EXTRA_ARGS}
        ;;
    tier2|2)
        echo -e "${YELLOW}Running Tier 2: Boundary & Corner Cases Tests...${NC}"
        python3 -m pytest tests/e2e/test_tier2_boundary_cases.py -v ${EXTRA_ARGS}
        ;;
    tier3|3)
        echo -e "${YELLOW}Running Tier 3: Cross-Feature Integration Tests...${NC}"
        python3 -m pytest tests/e2e/test_tier3_cross_feature.py -v ${EXTRA_ARGS}
        ;;
    tier4|4)
        echo -e "${YELLOW}Running Tier 4: Real-World Application Scenarios Tests...${NC}"
        python3 -m pytest tests/e2e/test_tier4_real_world_scenarios.py -v ${EXTRA_ARGS}
        ;;
    tier5|5)
        echo -e "${YELLOW}Running Tier 5: Adversarial Stress & Security Tests...${NC}"
        python3 -m pytest tests/e2e/test_tier5_adversarial_stress.py -v ${EXTRA_ARGS}
        ;;
    all|*)
        echo -e "${YELLOW}Executing All E2E Tiers (Tiers 1-5)...${NC}"
        python3 -m pytest tests/e2e -v --tb=short ${EXTRA_ARGS}
        ;;
esac

EXIT_CODE=$?

echo ""
if [ ${EXIT_CODE} -eq 0 ]; then
    echo -e "${GREEN}==============================================================================${NC}"
    echo -e "${GREEN}        [PASS] ALL APEXTENDER v2.0 E2E TESTS PASSED SUCCESSFULLY!             ${NC}"
    echo -e "${GREEN}==============================================================================${NC}"
else
    echo -e "${RED}==============================================================================${NC}"
    echo -e "${RED}        [FAIL] E2E TEST RUN COMPLETED WITH FAILURES (Exit Code: ${EXIT_CODE}) ${NC}"
    echo -e "${RED}==============================================================================${NC}"
fi

exit ${EXIT_CODE}
