# SuperClaude Dashboard

Native desktop dashboard for the SuperClaude agentic framework.

**Tech Stack**: Tauri v2 + Leptos (Rust WASM)

## Quick Start

```bash
# Start daemon first
cargo run -p superclaude-daemon

# Launch dashboard
cargo tauri dev
```

## Documentation

See [Dashboard User Guide](../../Docs/dashboard.md) for full documentation.

## Development

- **Frontend**: `frontend/` (Leptos WASM, trunk build system)
- **Backend**: `src/` (Tauri IPC commands)
- **Build**: `cargo tauri build` produces .deb and AppImage

## Architecture

- **Frontend**: Client-side Leptos app compiled to WASM
- **Backend**: Tauri native layer with IPC commands
- **Communication**: Frontend ↔ Tauri IPC ↔ gRPC daemon
- **Data**: Inventory from filesystem, metrics from JSONL, live events from gRPC stream

## Pages

1. **Inventory** - Browse agents, commands, skills, modes
2. **Monitor** - Real-time execution tracking and event streaming
3. **Control** - Start/stop/pause executions with parameters
4. **History** - View past execution metrics and events

## Building

### Development Mode

```bash
cargo tauri dev
```

This launches:
- Trunk dev server on port 1420 (frontend)
- Tauri window with dev tools enabled

### Production Build

```bash
cargo tauri build
```

Output:
- `target/release/bundle/deb/superclaude-dashboard_*.deb` - Debian package
- `target/release/bundle/appimage/superclaude-dashboard_*.AppImage` - AppImage

## Dependencies

### System (Linux)

**Manjaro/Arch**:
```bash
sudo pacman -S webkit2gtk-4.1 libappindicator-gtk3 librsvg patchelf
```

**Ubuntu/Debian**:
```bash
sudo apt install libwebkit2gtk-4.1-dev libappindicator3-dev librsvg2-dev
```

### Rust

- trunk: `cargo install trunk`
- tauri-cli v2: `cargo install tauri-cli --version ^2`

## Project Structure

```
dashboard/
├── Cargo.toml           # Backend dependencies
├── tauri.conf.json      # Tauri configuration
├── build.rs             # Build script
├── src/
│   ├── main.rs          # Tauri backend entry point
│   ├── grpc_client.rs   # gRPC client for daemon
│   └── commands.rs      # Tauri IPC commands
├── frontend/
│   ├── Cargo.toml       # Frontend dependencies
│   ├── index.html       # HTML shell
│   ├── src/
│   │   ├── main.rs      # Leptos app entry
│   │   ├── pages/       # Page components
│   │   ├── components/  # Reusable components
│   │   └── types.rs     # Shared types
│   └── Trunk.toml       # Trunk configuration
└── icons/               # Application icons
```

## Troubleshooting

### Build Errors

**Missing webkit2gtk**:
```bash
sudo apt install libwebkit2gtk-4.1-dev
```

**Missing tauri-cli**:
```bash
cargo install tauri-cli --version ^2
```

### Runtime Issues

**Daemon connection failed**:
- Ensure daemon is running: `cargo run -p superclaude-daemon`
- Check port 50051 is open

**Frontend not loading**:
- Clear trunk cache: `rm -rf frontend/dist`
- Rebuild: `cd frontend && trunk build`

## Contributing

See main [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

Dashboard-specific notes:
- Frontend uses Leptos CSR mode (client-side rendering)
- Backend uses Tauri v2 IPC commands
- Follow Rust style guidelines (rustfmt, clippy)
- Test on Linux (primary target), macOS (secondary)
