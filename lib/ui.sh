#!/usr/bin/env bash
# InfiniteCore — UI helpers

# shellcheck source=colors.sh
[ -f "$(dirname "${BASH_SOURCE[0]}")/colors.sh" ] && source "$(dirname "${BASH_SOURCE[0]}")/colors.sh"

ui_banner() {
    local title="$1" version="$2"
    clear
    echo -e "${C}"
    cat << EOF
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   🚀 ${title}
║   Version: ${version}
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${N}"
}

ui_step() {
    echo ""
    echo -e "${M}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
    echo -e "${W}  ▸ $1${N}"
    echo -e "${M}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
}

ui_log()  { echo -e "${C}[INFO]${N}  $1"; }
ui_ok()   { echo -e "${G}[  OK ]${N}  $1"; }
ui_warn() { echo -e "${Y}[WARN]${N}  $1"; }
ui_fail() { echo -e "${R}[FAIL]${N}  $1"; exit 1; }

ui_progress() {
    local current="$1" total="$2" label="${3:-}"
    local pct=$((current * 100 / total))
    local filled=$((current * 40 / total))
    local bar=""
    for ((i=0; i<filled; i++)); do bar+="█"; done
    for ((i=filled; i<40; i++)); do bar+="░"; done
    printf "\r${C}[${bar}]${N} ${pct}%% ${label}"
    [ "$current" -eq "$total" ] && echo ""
}

ui_spinner() {
    local pid=$1
    local msg="${2:-Working}"
    local spin=('⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏')
    local i=0
    while kill -0 "$pid" 2>/dev/null; do
        printf "\r${C}%s${N} %s..." "${spin[$i]}" "$msg"
        i=$(((i+1) % 10))
        sleep 0.1
    done
    printf "\r"
}

ui_box() {
    local title="$1"
    local -a lines=("${@:2}")
    local max=0
    for l in "${lines[@]}"; do
        [ ${#l} -gt $max ] && max=${#l}
    done
    local w=$((max + 4))
    echo -e "${G}╔$(printf '═%.0s' $(seq 1 $w))╗${N}"
    echo -e "${G}║  ${W}${title}$(printf ' %.0s' $(seq 1 $((w - ${#title} - 2))))${G}║${N}"
    echo -e "${G}╠$(printf '═%.0s' $(seq 1 $w))╣${N}"
    for l in "${lines[@]}"; do
        echo -e "${G}║  ${N}${l}$(printf ' %.0s' $(seq 1 $((w - ${#l} - 2))))${G}║${N}"
    done
    echo -e "${G}╚$(printf '═%.0s' $(seq 1 $w))╝${N}"
}

ui_confirm() {
    local msg="${1:-Continue?}"
    read -rp "$(echo -e "${Y}?${N} ${msg} [y/N]: ")" ans
    [[ "$ans" =~ ^[Yy]$ ]]
}
