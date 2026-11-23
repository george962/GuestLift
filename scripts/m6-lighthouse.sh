#!/usr/bin/env bash
# Run after deploying public pages to staging, with Chrome + lighthouse available.
# Usage: M6_PUBLIC_URL=https://staging.example.org bash scripts/m6-lighthouse.sh
set -euo pipefail
: "${M6_PUBLIC_URL:?Set M6_PUBLIC_URL to an approved staging URL}"
command -v lighthouse >/dev/null 2>&1 || { echo 'Install Lighthouse CLI before running this external gate.' >&2; exit 2; }
for page in / /product /pricing /help; do
  path="${page#/}"; [ -n "$path" ] || path=home
  lighthouse "${M6_PUBLIC_URL%/}${page}" --quiet --chrome-flags='--headless --no-sandbox' \
    --form-factor=mobile --only-categories=accessibility,performance,best-practices,seo \
    --output=json --output-path="/tmp/tablesignal-m6-${path}.json"
  python3 - "/tmp/tablesignal-m6-${path}.json" <<'LIGHTHOUSE_RESULT'
import json, sys
report=json.load(open(sys.argv[1]))
scores={name:round(row['score']*100) for name,row in report['categories'].items()}
print('Mobile Lighthouse:',sys.argv[1],scores)
if any(score < 90 for score in scores.values()):
    raise SystemExit('Mobile Lighthouse score below 90; M6 external gate remains open')
LIGHTHOUSE_RESULT
done
