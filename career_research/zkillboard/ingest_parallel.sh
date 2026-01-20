#!/bin/bash
#
# Parallel killmail ingestion script
#
# Forks a process for each month to download and ingest killmails in parallel.
#
# Usage:
#   ./ingest_parallel.sh 2025                    # All of 2025
#   ./ingest_parallel.sh 2025 01 03              # Jan-Mar 2025
#   ./ingest_parallel.sh 2024 10 12 2025         # Oct 2024 - Dec 2025 (cross-year)
#   ./ingest_parallel.sh 2025 --dry-run          # Show what would be ingested
#
# Data will be cached in /tmp/killmails/ and reused on subsequent runs.

set -e

# Directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Parse arguments
DRY_RUN=false
START_YEAR=2025
START_MONTH=1
END_YEAR=2025
END_MONTH=12

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        [0-9][0-9][0-9][0-9])
            if [[ -z "$START_YEAR_SET" ]]; then
                START_YEAR=$1
                END_YEAR=$1
                START_YEAR_SET=true
            else
                END_YEAR=$1
            fi
            shift
            ;;
        [0-9][0-9])
            if [[ -z "$START_MONTH_SET" ]]; then
                START_MONTH=$1
                END_MONTH=$1
                START_MONTH_SET=true
            else
                END_MONTH=$1
            fi
            shift
            ;;
        *)
            echo "Unknown argument: $1"
            echo "Usage: $0 [start_year] [start_month] [end_year] [end_month] [--dry-run]"
            exit 1
            ;;
    esac
done

# Validate inputs
if [[ ! "$START_YEAR" =~ ^[0-9]{4}$ ]] || \
   [[ ! "$START_MONTH" =~ ^[0-9]{1,2}$ ]] || \
   [[ ! "$END_YEAR" =~ ^[0-9]{4}$ ]] || \
   [[ ! "$END_MONTH" =~ ^[0-9]{1,2}$ ]]; then
    echo "Usage: $0 [start_year] [start_month] [end_year] [end_month]"
    echo "Example: $0 2025 01 03    # Jan-Mar 2025"
    exit 1
fi

# Convert to integers for comparison
start_y=$((10#$START_YEAR))
start_m=$((10#$START_MONTH))
end_y=$((10#$END_YEAR))
end_m=$((10#$END_MONTH))

# Log file for this run
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/ingest_${TIMESTAMP}.log"

echo "=================================================="
echo "Parallel Killmail Ingestion"
echo "=================================================="
echo "Range: ${START_YEAR}-${START_MONTH} to ${END_YEAR}-${END_MONTH}"
echo "Log: $LOG_FILE"
echo "=================================================="

# Function to ingest a single month
ingest_month() {
    local year=$1
    local month=$2
    local month_pad=$(printf "%02d" $month)
    local dry_run_flag=""

    if [[ "$DRY_RUN" == true ]]; then
        dry_run_flag="--dry-run"
    fi

    echo "[$year-$month_pad] Starting..." | tee -a "$LOG_FILE"

    # Run the Python ingest script
    if python3 "$SCRIPT_DIR/ingest_month.py" "$year" "$month" $dry_run_flag 2>&1 | tee -a "$LOG_FILE"; then
        echo "[$year-$month_pad] ✓ Complete" | tee -a "$LOG_FILE"
    else
        echo "[$year-$month_pad] ✗ Failed with exit code $?" | tee -a "$LOG_FILE"
        return 1
    fi
}

# Fork a process for each month
pids=()

current_year=$start_y
current_month=$start_m

while true; do
    # Check if we've passed the end
    if [[ $current_year -gt $end_y ]] || \
       [[ $current_year -eq $end_y && $current_month -gt $end_m ]]; then
        break
    fi

    # Fork this month
    ingest_month $current_year $current_month &
    pids+=($!)

    # Move to next month
    ((current_month++))
    if [[ $current_month -gt 12 ]]; then
        current_month=1
        ((current_year++))
    fi
done

echo "=================================================="
echo "Forked ${#pids[@]} month process(es)"
echo "Check $LOG_FILE for progress"
echo "=================================================="

# Wait for all background processes
failed=0
for pid in "${pids[@]}"; do
    if ! wait $pid; then
        ((failed++))
    fi
done

echo "=================================================="
if [[ $failed -eq 0 ]]; then
    echo "✓ All months completed successfully"
else
    echo "✗ $failed month(s) failed"
    exit 1
fi
echo "=================================================="

# Show final stats
echo ""
echo "Final Statistics:"
cd "$SCRIPT_DIR"
python3 -c "
from ingest import KillmailImporter
importer = KillmailImporter()
importer.print_stats()
" 2>/dev/null || echo "Run importer.print_stats() in Python for detailed stats"
