#!/usr/bin/env bash
# ═══════════════════════════════════════════════
#  🤖 INFINITECORE BOT — ONE-LINE INSTALLER
#  Usage: bash <(curl -fsSL https://raw.githubusercontent.com/YOUR_USER/infinitecore-bot/main/install.sh)
# ═══════════════════════════════════════════════

set -e

R='\033[0;31m'; G='\033[0;32m'; Y='\033[1;33m'; B='\033[0;34m'
C='\033[0;36m'; M='\033[0;35m'; W='\033[1;37m'; N='\033[0m'

REPO_URL="${REPO_URL:-https://github.com/YOUR_USER/infinitecore-bot.git}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/infinitecore-bot}"
BRANCH="${BRANCH:-main}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="$INSTALL_DIR/venv"

show_banner() {
    clear
    echo -e "${C}"
    cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   🤖  I N F I N I T E C O R E   B O T                         ║
║                                                               ║
║   Premium Discord Bot — One-Line Installer                    ║
║   Version: 4.0.0                                              ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${N}"
}

log()  { echo -e "${C}[INFO]${N}  $1"; }
ok()   { echo -e "${G}[  OK ]${N}  $1"; }
warn() { echo -e "${Y}[WARN]${N}  $1"; }
fail() { echo -e "${R}[FAIL]${N}  $1"; exit 1; }

step() {
    echo ""
    echo -e "${M}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
    echo -e "${W}  ▸ $1${N}"
    echo -e "${M}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
}

detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/debian_version ]; then OS="debian"
        elif [ -f /etc/redhat-release ]; then OS="redhat"
        else OS="linux"; fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then OS="macos"
    else OS="unknown"; fi
    log "Detected OS: $OS"
}

install_sysdeps() {
    step "Installing system dependencies"
    case "$OS" in
        debian)
            sudo apt-get update -qq
            sudo apt-get install -y -qq python3 python3-pip python3-venv git curl
            ;;
        redhat)
            sudo dnf install -y python3 python3-pip git curl
            ;;
        macos)
            command -v brew &>/dev/null || fail "Homebrew not installed"
            brew install python3 git curl
            ;;
        *)
            warn "Unknown OS — assuming python3/git/curl are installed"
            ;;
    esac
    ok "System dependencies ready"
}

check_python() {
    step "Checking Python"
    command -v "$PYTHON_BIN" &>/dev/null || fail "Python3 not found"
    PY_VER=$("$PYTHON_BIN" --version 2>&1 | awk '{print $2}')
    log "Python version: $PY_VER"
    "$PYTHON_BIN" -c "import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)" || \
        fail "Python 3.9+ required. Found: $PY_VER"
    ok "Python OK"
}

clone_repo() {
    step "Cloning InfiniteCore Bot"
    if [ -d "$INSTALL_DIR" ]; then
        warn "Directory exists: $INSTALL_DIR"
        read -rp "Overwrite? [y/N]: " ans
        if [[ "$ans" =~ ^[Yy]$ ]]; then
            rm -rf "$INSTALL_DIR"
        else
            cd "$INSTALL_DIR"
            git pull origin "$BRANCH" || warn "Git pull failed"
            return
        fi
    fi
    git clone --branch "$BRANCH" --depth 1 "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    ok "Repo cloned"
}

create_venv() {
    step "Creating virtual environment"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip wheel setuptools -q
    ok "Virtual env ready"
}

install_pip() {
    step "Installing Python packages"
    [ -f requirements.txt ] || fail "requirements.txt not found"
    pip install -r requirements.txt -q
    ok "Python packages installed"
}

setup_env() {
    step "Configuring .env"
    if [ -f .env ]; then
        warn ".env already exists"
        read -rp "Reconfigure? [y/N]: " ans
        [[ ! "$ans" =~ ^[Yy]$ ]] && { log "Keeping .env"; return; }
    fi
    [ -f .env.example ] || fail ".env.example missing"
    cp .env.example .env

    echo ""
    echo -e "${Y}━━━ Interactive Setup ━━━${N}"
    echo "Leave blank to skip (edit .env later)"
    echo ""

    read -rp "🤖 Discord Bot Token: " token
    [ -n "$token" ] && sed -i.bak "s|^DISCORD_TOKEN=.*|DISCORD_TOKEN=$token|" .env

    read -rp "🏠 Guild ID (0 for global): " gid
    [ -n "$gid" ] && sed -i.bak "s|^GUILD_ID=.*|GUILD_ID=$gid|" .env

    read -rp "👑 Owner Discord ID: " oid
    [ -n "$oid" ] && sed -i.bak "s|^OWNER_ID=.*|OWNER_ID=$oid|" .env

    rm -f .env.bak
    ok ".env configured"
}

init_dirs() {
    step "Creating directories"
    mkdir -p data backups logs bot/cogs bot/utils
    touch data/.gitkeep backups/.gitkeep logs/.gitkeep 2>/dev/null || true
    ok "Directories ready"
}

test_import() {
    step "Testing imports"
    source "$VENV_DIR/bin/activate"
    if python -c "import discord, aiohttp, dotenv" 2>/dev/null; then
        ok "All imports OK"
    else
        fail "Import test failed"
    fi
}

print_success() {
    echo ""
    echo -e "${G}"
    cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   ✅  I N S T A L L A T I O N   C O M P L E T E               ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${N}"
    echo -e "${W}📁 Install Dir:${N}  $INSTALL_DIR"
    echo -e "${W}🐍 Python Venv:${N}  $VENV_DIR"
    echo ""
    echo -e "${C}🚀 To start the bot:${N}"
    echo "   cd $INSTALL_DIR"
    echo "   source venv/bin/activate"
    echo "   cd bot"
    echo "   python bot.py"
    echo ""
    echo -e "${Y}📝 Edit .env:${N}"
    echo "   nano $INSTALL_DIR/.env"
    echo ""
}

main() {
    show_banner
    detect_os
    install_sysdeps
    check_python
    clone_repo
    create_venv
    install_pip
    init_dirs
    setup_env
    test_import
    print_success
}

main "$@"
