#!/usr/bin/env bash
# Post-apply render checks (read-only): the sample faces, with cache-buster.
set -uo pipefail
BUST="?cbq=m2$(date -u +%H%M%S)"
check() {
  local url="$1"
  local html status
  html=$(curl -sk -H 'Cache-Control: no-cache' "https://de-linker.com${url}${BUST}")
  status=$(curl -sk -o /dev/null -w '%{http_code}' -H 'Cache-Control: no-cache' "https://de-linker.com${url}${BUST}")
  local hits=""
  for t in "Linker Advisor" "Linker Planner" "Linker Site Detail" "Linker Berater" "Linker Planer" "Linker Standortdetails" '/linker-advisor/' '/linker-planner/' '/de/linker-planer/'; do
    n=$(printf '%s' "$html" | grep -o -- "$t" | wc -l | tr -d ' ')
    [ "$n" != "0" ] && hits="$hits $t:$n"
  done
  printf '%-42s %s  old-tokens:%s\n' "$url" "$status" "${hits:- 0}"
}
for u in / /de/ /de/fuer-installateur/ /de/loesung/ /de/service-support/ /de/datenschutz/ /de/faq-download/ /privacy-policy/ /de/genie/ /de/loesungskonfigurator/ /genie/ /solution-configurator/; do
  check "$u"
done
