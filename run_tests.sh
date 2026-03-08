#!/bin/bash

# Test Runner Script for mul-agent
# Usage: ./run_tests.sh [options]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
RUN_BACKEND=true
RUN_FRONTEND=false
RUN_COVERAGE=true
SPECIFIC_TEST=""

# Help function
show_help() {
    echo "Usage: ./run_tests.sh [options]"
    echo ""
    echo "Options:"
    echo "  -h, --help          Show this help message"
    echo "  -b, --backend       Run backend tests (default)"
    echo "  -f, --frontend      Run frontend tests"
    echo "  -a, --all           Run both backend and frontend tests"
    echo "  -c, --coverage      Generate coverage report"
    echo "  -t, --test PATH     Run specific test file or function"
    echo "  -v, --verbose       Verbose output"
    echo ""
    echo "Examples:"
    echo "  ./run_tests.sh                    # Run backend tests"
    echo "  ./run_tests.sh -a                 # Run all tests"
    echo "  ./run_tests.sh -t test_brain.py   # Run specific test"
    echo "  ./run_tests.sh --coverage         # With coverage"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -b|--backend)
            RUN_BACKEND=true
            RUN_FRONTEND=false
            shift
            ;;
        -f|--frontend)
            RUN_BACKEND=false
            RUN_FRONTEND=true
            shift
            ;;
        -a|--all)
            RUN_BACKEND=true
            RUN_FRONTEND=true
            shift
            ;;
        -c|--coverage)
            RUN_COVERAGE=true
            shift
            ;;
        -t|--test)
            SPECIFIC_TEST="$2"
            shift 2
            ;;
        -v|--verbose)
            set -x
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

echo "========================================"
echo "       MUL-Agent Test Runner          "
echo "========================================"
echo ""

# Backend tests
if [ "$RUN_BACKEND" = true ]; then
    echo -e "${YELLOW}Running Backend Tests...${NC}"
    echo ""

    cd "$(dirname "$0")"

    if [ -n "$SPECIFIC_TEST" ]; then
        echo "Running specific test: $SPECIFIC_TEST"
        pytest tests/$SPECIFIC_TEST -v
    else
        if [ "$RUN_COVERAGE" = true ]; then
            echo "With coverage enabled"
            pytest tests/ -v --cov=mul_agent --cov-report=html --cov-report=term
        else
            pytest tests/ -v
        fi
    fi

    echo ""
    echo -e "${GREEN}Backend Tests Complete!${NC}"
    echo ""
fi

# Frontend tests
if [ "$RUN_FRONTEND" = true ]; then
    echo -e "${YELLOW}Running Frontend Tests...${NC}"
    echo ""

    cd frontend

    if [ -n "$SPECIFIC_TEST" ]; then
        npm run test -- $SPECIFIC_TEST
    else
        if [ "$RUN_COVERAGE" = true ]; then
            npm run test:coverage
        else
            npm run test
        fi
    fi

    cd ..

    echo ""
    echo -e "${GREEN}Frontend Tests Complete!${NC}"
    echo ""
fi

echo "========================================"
echo "         All Tests Complete!           "
echo "========================================"
