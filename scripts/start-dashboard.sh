#!/usr/bin/env bash
# start-dashboard.sh — Launch SuperClaude Daemon + Dashboard
#
# Usage:
#   ./scripts/start-dashboard.sh          # normal start
#   ./scripts/start-dashboard.sh --build   # force rebuild before starting
#   ./scripts/start-dashboard.sh --kill    # kill any running daemon/dashboard

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/.superclaude_logs"
DAEMON_LOG="$LOG_DIR/daemon.log"
DASHBOARD_LOG="$LOG_DIR/dashboard.log"
DAEMON_PID_FILE="$LOG_DIR/daemon.pid"

DAEMON_TCP_PORT=50051
DASHBOARD_PORT=1420
UNIX_SOCKET="/tmp/superclaude.sock"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()   { echo -e "${RED}[ERR]${NC}   $*"; }

# ─── Cleanup on exit ──────────────────────────────────────────────
cleanup() {
    local exit_code=$?
    echo ""
    info "Shutting down..."

    # Kill daemon if we started it
    if [[ -f "$DAEMON_PID_FILE" ]]; then
        local pid
        pid=$(cat "$DAEMON_PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            info "Stopping daemon (pid $pid)"
            kill "$pid" 2>/dev/null || true
            # Wait briefly for graceful shutdown
            for _ in {1..10}; do
                kill -0 "$pid" 2>/dev/null || break
                sleep 0.2
            done
            # Force kill if still alive
            kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null || true
        fi
        rm -f "$DAEMON_PID_FILE"
    fi

    # Kill trunk/dashboard processes we may have spawned
    if [[ -n "${TAURI_PID:-}" ]] && kill -0 "$TAURI_PID" 2>/dev/null; then
        info "Stopping dashboard (pid $TAURI_PID)"
        kill "$TAURI_PID" 2>/dev/null || true
    fi

    # Clean stale socket
    [[ -S "$UNIX_SOCKET" ]] && rm -f "$UNIX_SOCKET"

    if [[ $exit_code -eq 0 ]]; then
        ok "Clean shutdown."
    else
        warn "Exited with code $exit_code"
    fi
}
trap cleanup EXIT

# ─── Kill mode ────────────────────────────────────────────────────
kill_existing() {
    local killed=0

    # Kill daemon
    if [[ -f "$DAEMON_PID_FILE" ]]; then
        local pid
        pid=$(cat "$DAEMON_PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            info "Killing daemon (pid $pid)"
            kill "$pid" 2>/dev/null
            killed=1
        fi
        rm -f "$DAEMON_PID_FILE"
    fi

    # Kill anything on daemon port
    local pids
    pids=$(ss -tlnp 2>/dev/null | grep ":${DAEMON_TCP_PORT}" | grep -oP 'pid=\K[0-9]+' || true)
    for pid in $pids; do
        info "Killing process on port $DAEMON_TCP_PORT (pid $pid)"
        kill "$pid" 2>/dev/null || true
        killed=1
    done

    # Kill anything on dashboard port
    pids=$(ss -tlnp 2>/dev/null | grep ":${DASHBOARD_PORT}" | grep -oP 'pid=\K[0-9]+' || true)
    for pid in $pids; do
        info "Killing process on port $DASHBOARD_PORT (pid $pid)"
        kill "$pid" 2>/dev/null || true
        killed=1
    done

    # Clean socket
    [[ -S "$UNIX_SOCKET" ]] && rm -f "$UNIX_SOCKET" && info "Removed stale socket"

    if [[ $killed -eq 0 ]]; then
        info "Nothing to kill."
    else
        ok "Cleaned up."
    fi
}

# ─── Preflight checks ────────────────────────────────────────────
preflight() {
    local missing=0

    info "Running preflight checks..."

    # Rust toolchain
    if ! command -v cargo &>/dev/null; then
        err "cargo not found. Install Rust: https://rustup.rs"
        missing=1
    fi

    # Trunk (WASM bundler)
    if ! command -v trunk &>/dev/null; then
        err "trunk not found. Install: cargo install trunk"
        missing=1
    fi

    # Tauri CLI
    if ! command -v cargo-tauri &>/dev/null; then
        err "cargo-tauri not found. Install: cargo install tauri-cli --version ^2"
        missing=1
    fi

    # Claude CLI (needed by daemon to spawn executions)
    if ! command -v claude &>/dev/null; then
        warn "claude CLI not found in PATH. Daemon can start but executions will fail."
        warn "Install: npm install -g @anthropic-ai/claude-code"
    fi

    # WebKit (Linux/Tauri dependency)
    if command -v pacman &>/dev/null; then
        local pkg
        for pkg in webkit2gtk-4.1 librsvg; do
            if ! pacman -Q "$pkg" &>/dev/null; then
                err "Missing system package: $pkg"
                err "  sudo pacman -S $pkg"
                missing=1
            fi
        done
    fi

    # Check ports aren't occupied by something unrelated
    local port_pid
    port_pid=$(ss -tlnp 2>/dev/null | grep ":${DAEMON_TCP_PORT}" | grep -oP 'pid=\K[0-9]+' | head -1 || true)
    if [[ -n "$port_pid" ]]; then
        local port_cmd
        port_cmd=$(ps -p "$port_pid" -o comm= 2>/dev/null || echo "unknown")
        if [[ "$port_cmd" == *superclaude* ]]; then
            warn "Daemon already running on port $DAEMON_TCP_PORT (pid $port_pid)"
            warn "Use --kill to stop it first, or it will be reused."
            DAEMON_ALREADY_RUNNING=1
        else
            err "Port $DAEMON_TCP_PORT occupied by '$port_cmd' (pid $port_pid)"
            err "  Kill it or use --kill flag"
            missing=1
        fi
    fi

    port_pid=$(ss -tlnp 2>/dev/null | grep ":${DASHBOARD_PORT}" | grep -oP 'pid=\K[0-9]+' | head -1 || true)
    if [[ -n "$port_pid" ]]; then
        local port_cmd
        port_cmd=$(ps -p "$port_pid" -o comm= 2>/dev/null || echo "unknown")
        if [[ "$port_cmd" == *trunk* ]] || [[ "$port_cmd" == *superclaude* ]]; then
            warn "Port $DASHBOARD_PORT occupied by '$port_cmd' (pid $port_pid) — killing it"
            kill "$port_pid" 2>/dev/null || true
            sleep 1
        else
            err "Port $DASHBOARD_PORT occupied by '$port_cmd' (pid $port_pid)"
            err "  Kill it manually or use --kill flag"
            missing=1
        fi
    fi

    if [[ $missing -ne 0 ]]; then
        err "Preflight failed. Fix the issues above and retry."
        exit 1
    fi

    ok "Preflight passed."
}

# ─── Build ────────────────────────────────────────────────────────
build() {
    info "Building daemon..."
    if ! cargo build -p superclaude-daemon 2>&1 | tee "$LOG_DIR/build-daemon.log"; then
        err "Daemon build failed. See $LOG_DIR/build-daemon.log"
        exit 1
    fi
    ok "Daemon built."

    # Dashboard builds via `cargo tauri dev` (which runs trunk internally),
    # so we only pre-build the daemon here.
}

# ─── Start daemon ─────────────────────────────────────────────────
start_daemon() {
    if [[ "${DAEMON_ALREADY_RUNNING:-0}" -eq 1 ]]; then
        ok "Reusing existing daemon on port $DAEMON_TCP_PORT"
        return
    fi

    info "Starting daemon..."
    RUST_LOG="${RUST_LOG:-superclaude_daemon=info,tower_http=debug}" \
        cargo run -p superclaude-daemon \
        >> "$DAEMON_LOG" 2>&1 &
    local daemon_pid=$!
    echo "$daemon_pid" > "$DAEMON_PID_FILE"

    # Wait for daemon to be ready (poll TCP port)
    info "Waiting for daemon on port $DAEMON_TCP_PORT..."
    local retries=0
    local max_retries=60
    while ! ss -tln 2>/dev/null | grep -q ":${DAEMON_TCP_PORT}"; do
        if ! kill -0 "$daemon_pid" 2>/dev/null; then
            err "Daemon died during startup. Last 20 lines:"
            tail -20 "$DAEMON_LOG" | while IFS= read -r line; do echo "  $line"; done
            exit 1
        fi
        retries=$((retries + 1))
        if [[ $retries -ge $max_retries ]]; then
            err "Daemon did not start. Last 20 lines of log:"
            tail -20 "$DAEMON_LOG" | while IFS= read -r line; do echo "  $line"; done
            exit 1
        fi
        sleep 1
    done
    ok "Daemon running (pid $daemon_pid, TCP :$DAEMON_TCP_PORT, Unix $UNIX_SOCKET)"
}

# ─── Start dashboard ─────────────────────────────────────────────
start_dashboard() {
    info "Starting dashboard (Tauri + Trunk)..."
    info "  Logs: $DASHBOARD_LOG"
    info "  This compiles WASM frontend + native backend — first run is slower."

    cd "$PROJECT_ROOT/crates/dashboard"
    cargo tauri dev >> "$DASHBOARD_LOG" 2>&1 &
    TAURI_PID=$!

    # Wait for trunk to serve the frontend
    info "Waiting for frontend on port $DASHBOARD_PORT..."
    local retries=0
    local max_retries=120
    while ! ss -tln 2>/dev/null | grep -q ":${DASHBOARD_PORT}"; do
        if ! kill -0 "$TAURI_PID" 2>/dev/null; then
            err "Dashboard died during startup. Last 30 lines:"
            tail -30 "$DASHBOARD_LOG" | while IFS= read -r line; do echo "  $line"; done
            exit 1
        fi
        retries=$((retries + 1))
        if [[ $retries -ge $max_retries ]]; then
            err "Dashboard did not start. Last 30 lines:"
            tail -30 "$DASHBOARD_LOG" | while IFS= read -r line; do echo "  $line"; done
            exit 1
        fi
        sleep 1
    done
    ok "Dashboard running (pid $TAURI_PID)"
    cd "$PROJECT_ROOT"
}

# ─── Status display ──────────────────────────────────────────────
show_status() {
    echo ""
    echo -e "${BOLD}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║          SuperClaude Dashboard Ready             ║${NC}"
    echo -e "${BOLD}╠══════════════════════════════════════════════════╣${NC}"
    echo -e "${BOLD}║${NC}  Daemon:    ${GREEN}tcp://127.0.0.1:${DAEMON_TCP_PORT}${NC}             ${BOLD}║${NC}"
    echo -e "${BOLD}║${NC}             ${GREEN}unix://${UNIX_SOCKET}${NC}   ${BOLD}║${NC}"
    echo -e "${BOLD}║${NC}  Frontend:  ${GREEN}http://localhost:${DASHBOARD_PORT}${NC}              ${BOLD}║${NC}"
    echo -e "${BOLD}║${NC}                                                  ${BOLD}║${NC}"
    echo -e "${BOLD}║${NC}  Logs:                                           ${BOLD}║${NC}"
    echo -e "${BOLD}║${NC}    Daemon:    ${CYAN}$DAEMON_LOG${NC}"
    echo -e "${BOLD}║${NC}    Dashboard: ${CYAN}$DASHBOARD_LOG${NC}"
    echo -e "${BOLD}║${NC}                                                  ${BOLD}║${NC}"
    echo -e "${BOLD}║${NC}  ${YELLOW}Press Ctrl+C to stop everything${NC}                ${BOLD}║${NC}"
    echo -e "${BOLD}╚══════════════════════════════════════════════════╝${NC}"
    echo ""
}

# ─── Tail logs ────────────────────────────────────────────────────
tail_logs() {
    # Interleave both log files, prefixed
    tail -f "$DAEMON_LOG" 2>/dev/null | while IFS= read -r line; do
        echo -e "${CYAN}[daemon]${NC}    $line"
    done &
    local tail_daemon_pid=$!

    tail -f "$DASHBOARD_LOG" 2>/dev/null | while IFS= read -r line; do
        echo -e "${YELLOW}[dashboard]${NC} $line"
    done &
    local tail_dash_pid=$!

    # Wait for Ctrl+C — the EXIT trap handles cleanup
    wait "$TAURI_PID" 2>/dev/null || true

    kill "$tail_daemon_pid" "$tail_dash_pid" 2>/dev/null || true
}

# ─── Main ─────────────────────────────────────────────────────────
main() {
    DAEMON_ALREADY_RUNNING=0

    echo -e "${BOLD}SuperClaude Dashboard Launcher${NC}"
    echo ""

    # Parse args
    local do_build=0
    for arg in "$@"; do
        case "$arg" in
            --kill)
                kill_existing
                exit 0
                ;;
            --build)
                do_build=1
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --build    Force rebuild before starting"
                echo "  --kill     Kill any running daemon/dashboard and exit"
                echo "  --help     Show this help"
                exit 0
                ;;
            *)
                err "Unknown option: $arg"
                exit 1
                ;;
        esac
    done

    # Setup log dir
    mkdir -p "$LOG_DIR"
    : > "$DAEMON_LOG"
    : > "$DASHBOARD_LOG"

    preflight

    if [[ $do_build -eq 1 ]]; then
        build
    fi

    start_daemon
    start_dashboard
    show_status
    tail_logs
}

main "$@"
