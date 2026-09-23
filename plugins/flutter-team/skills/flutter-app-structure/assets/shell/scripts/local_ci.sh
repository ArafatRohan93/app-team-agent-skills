#!/usr/bin/env bash
# Local CI — run before every push. Mirrors what the CI pipeline checks.
#
#   scripts/local_ci.sh                    # full run, development flavor
#   scripts/local_ci.sh --skip-build       # checks + tests only (fast)
#   scripts/local_ci.sh --flavor staging   # build a different flavor
#   MIN_COVERAGE=90 scripts/local_ci.sh    # raise the coverage gate
set -euo pipefail

FLAVOR="development"
SKIP_BUILD=false
MIN_COVERAGE="${MIN_COVERAGE:-80}"

# Files excluded from the coverage gate: generated code, entry points and
# thin platform adapters that can only be exercised on a device.
COVERAGE_EXCLUDES=(
  "lib/main_"
  "lib/bootstrap.dart"
  "lib/app/app.dart"
  "lib/l10n/gen/"
  ".g.dart"
  ".freezed.dart"
  "lib/shared/storage/secure_key_value_storage.dart"
)

while [[ $# -gt 0 ]]; do
  case "$1" in
    --flavor) FLAVOR="$2"; shift 2 ;;
    --skip-build) SKIP_BUILD=true; shift ;;
    -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
step() { echo -e "\n${YELLOW}==>${NC} $1"; }
ok() { echo -e "${GREEN}✓${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; exit 1; }

cd "$(dirname "$0")/.."

if [[ -f .fvmrc || -d .fvm ]] && command -v fvm >/dev/null 2>&1; then
  FLUTTER=(fvm flutter); DART=(fvm dart)
else
  FLUTTER=(flutter); DART=(dart)
fi

step "Getting dependencies"
"${FLUTTER[@]}" pub get >/dev/null || fail "pub get failed"
ok "Dependencies installed"

step "Generating localizations"
"${FLUTTER[@]}" gen-l10n || fail "gen-l10n failed"
ok "Localizations generated"

step "Checking formatting"
"${DART[@]}" format --output=none --set-exit-if-changed lib test \
  || fail "Run: ${DART[*]} format lib test"
ok "Formatting is clean"

step "Analyzing"
"${FLUTTER[@]}" analyze --fatal-infos --fatal-warnings || fail "Analysis failed"
ok "No analysis issues"

step "Running tests with coverage"
"${FLUTTER[@]}" test --coverage || fail "Tests failed"
ok "All tests passed"

step "Checking coverage (minimum ${MIN_COVERAGE}%)"
[[ -f coverage/lcov.info ]] || fail "coverage/lcov.info not found"
COVERAGE=$(awk -v excludes="$(IFS='|'; echo "${COVERAGE_EXCLUDES[*]}")" '
  BEGIN { n = split(excludes, ex, "|") }
  /^SF:/ { skip = 0; for (i = 1; i <= n; i++) if (index($0, ex[i])) skip = 1 }
  /^LF:/ && !skip { found += substr($0, 4) }
  /^LH:/ && !skip { hit += substr($0, 4) }
  END { if (found == 0) print "0.0"; else printf "%.1f", hit * 100 / found }
' coverage/lcov.info)
echo "Coverage: ${COVERAGE}%"
awk -v c="$COVERAGE" -v m="$MIN_COVERAGE" 'BEGIN { exit !(c >= m) }' \
  || fail "Coverage ${COVERAGE}% is below ${MIN_COVERAGE}%"
ok "Coverage gate passed"

if [[ "$SKIP_BUILD" == false ]]; then
  step "Building Android ($FLAVOR, debug)"
  "${FLUTTER[@]}" build apk --debug --flavor "$FLAVOR" -t "lib/main_$FLAVOR.dart" \
    || fail "Android build failed"
  ok "APK: build/app/outputs/flutter-apk/app-$FLAVOR-debug.apk"

  if [[ "$(uname)" == "Darwin" ]]; then
    step "Building iOS ($FLAVOR, debug, simulator)"
    "${FLUTTER[@]}" build ios --debug --simulator --flavor "$FLAVOR" -t "lib/main_$FLAVOR.dart" \
      || fail "iOS build failed"
    ok "iOS simulator build succeeded"
  else
    echo "Skipping iOS build (requires macOS)"
  fi
fi

echo -e "\n${GREEN}✓ All local CI checks passed${NC}"
