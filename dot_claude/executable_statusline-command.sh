#!/usr/bin/env bash
# Claude Code statusLine script
# Shows: dir name | git branch (if repo) | model (+ effort) | context usage % | session usage %

input=$(cat)

py() {
  python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    print('')
    sys.exit(0)
def get(d, path):
    for k in path:
        if not isinstance(d, dict) or k not in d or d[k] is None:
            return None
        d = d[k]
    return d
paths = [p.split('.') for p in sys.argv[1].split('|')]
for p in paths:
    v = get(d, p)
    if v is not None:
        print(v)
        break
" "$1" <<< "$input"
}

cwd=$(py "workspace.current_dir|cwd")
model=$(py "model.display_name")
effort=$(py "effort.level")
ctx_used=$(py "context_window.used_percentage")
session_used=$(py "rate_limits.five_hour.used_percentage")

reset="\033[0m"

# segments: plain text pieces. seg_colors: matching ANSI color for each
# (empty string = pick next color from the rotating palette).
segments=()
seg_colors=()

# Percentage colored by usage threshold: <20% green, <50% yellow, <85% orange, else red
bar() {
  local pct="$1" label="$2"
  local pct_int=$(printf '%.0f' "$pct")
  local color
  if [ "$pct_int" -lt 20 ]; then
    color="\033[1;32m"        # green
  elif [ "$pct_int" -lt 50 ]; then
    color="\033[1;33m"        # yellow
  elif [ "$pct_int" -lt 85 ]; then
    color="\033[1;38;5;208m"  # orange
  else
    color="\033[1;31m"        # red
  fi
  segments+=("${label}${pct_int}%")
  seg_colors+=("$color")
}

# Current directory name + git branch (if inside a repo)
if [ -n "$cwd" ]; then
  dir_name=$(basename "$cwd")
  [ -n "$dir_name" ] && { segments+=("$dir_name"); seg_colors+=(""); }
  if git -C "$cwd" --no-optional-locks rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    branch=$(git -C "$cwd" --no-optional-locks branch --show-current 2>/dev/null)
    [ -n "$branch" ] && { segments+=("$branch"); seg_colors+=(""); }
  fi
fi

# Model + effort/reasoning level
if [ -n "$model" ]; then
  if [ -n "$effort" ]; then
    segments+=("$model ($effort)")
  else
    segments+=("$model")
  fi
  seg_colors+=("")
fi

# Context window usage as a progress bar
[ -n "$ctx_used" ] && bar "$ctx_used" "Ctx "

# Session usage (5-hour rate limit window) as a progress bar
[ -n "$session_used" ] && bar "$session_used" "Session "

# Render: rotating bright colors for plain segments, threshold color for bars
palette=("\033[1;36m" "\033[1;33m" "\033[1;35m" "\033[1;32m" "\033[1;34m")
sep="\033[90m |\033[0m "

out=""
pi=0
for idx in "${!segments[@]}"; do
  seg="${segments[$idx]}"
  color="${seg_colors[$idx]}"
  if [ -z "$color" ]; then
    color="${palette[$((pi % ${#palette[@]}))]}"
    pi=$((pi + 1))
  fi
  if [ -n "$out" ]; then
    out="${out}${sep}"
  fi
  out="${out}${color}${seg}${reset}"
done

printf "%b" "$out"
