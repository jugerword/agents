#!/bin/bash
# 用 curl 拉取 Polymarket gamma 全量市场并合并为单个 JSON 数组。
# curl 走 mihomo HTTP 代理稳定（Python httpx env-proxy 在 macOS 上与 mihomo
# 冲突导致 SSL EOF / 挂起），故用 curl 完成网络拉取，Python 只做本地处理。
# 用法: ./fetch_markets_with_curl.sh <输出目录> [每页大小]
set -uo pipefail

OUT_DIR="${1:-./local_db}"
LIMIT="${2:-100}"
EXTRA_PARAMS="${3:-}"
mkdir -p "$OUT_DIR"
OUT_FILE="$OUT_DIR/all-current-markets.json"
TMPDIR=$(mktemp -d)
CURSOR=""
PAGE=0

while true; do
  PAGE=$((PAGE + 1))
  URL="https://gamma-api.polymarket.com/markets/keyset?limit=${LIMIT}&active=true&closed=false&archived=false"
  if [ -n "$EXTRA_PARAMS" ]; then
    URL="${URL}&${EXTRA_PARAMS}"
  fi
  if [ -n "$CURSOR" ]; then
    URL="${URL}&after_cursor=${CURSOR}"
  fi
  PAGE_FILE="$TMPDIR/page_$PAGE.json"
  if ! curl -s --max-time 30 -x http://127.0.0.1:7890 "$URL" -o "$PAGE_FILE"; then
    echo "page $PAGE: curl failed, retrying..." >&2
    sleep 2
    continue
  fi
  if ! python3 -c "import json; json.load(open('$PAGE_FILE'))" 2>/dev/null; then
    echo "page $PAGE: invalid json, retrying..." >&2
    sleep 2
    continue
  fi
  META=$(python3 -c "
import json
d = json.load(open('$PAGE_FILE'))
print(len(d.get('markets', [])))
print(d.get('next_cursor', ''))
")
  COUNT=$(echo "$META" | head -1)
  NEW_CURSOR=$(echo "$META" | tail -1)
  if [ "$COUNT" = "0" ]; then
    echo "page $PAGE: empty, done" >&2
    rm -f "$PAGE_FILE"
    break
  fi
  echo "page $PAGE: +$COUNT markets" >&2
  CURSOR="$NEW_CURSOR"
  if [ -z "$CURSOR" ]; then
    echo "cursor END, done" >&2
    break
  fi
  sleep 0.3
done

# 合并所有页为单个 JSON 数组
python3 - "$TMPDIR" "$OUT_FILE" <<'PYEOF'
import json, sys, glob

tmpdir, out_file = sys.argv[1], sys.argv[2]
all_markets = []
for page_file in sorted(glob.glob(f"{tmpdir}/page_*.json")):
    d = json.load(open(page_file))
    all_markets.extend(d.get("markets", []))
with open(out_file, "w") as f:
    json.dump(all_markets, f)
print(f"MERGED {len(all_markets)} markets -> {out_file}")
PYEOF
rm -rf "$TMPDIR"
