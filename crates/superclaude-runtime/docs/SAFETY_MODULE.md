# Safety Module Documentation

## Overview

The `safety` module provides comprehensive security validation for SuperClaude operations, protecting against:

- **Destructive commands** (rm -rf, dd, mkfs)
- **Path traversal attacks** (../, ///)
- **System directory access** (/etc, /bin, C:\Windows)
- **Sensitive file access** (.env, credentials, .ssh)
- **Database operations** (DROP, DELETE, TRUNCATE)

## Architecture

The module is ported from Python implementations:
- `SuperClaude/Orchestrator/hooks.py` - Command patterns
- `setup/utils/security.py` - Path validation
- `.claude/hooks/pre-tool-use/*.sh` - Shell validators

### Core Components

```rust
pub struct SafetyValidator {
    command_patterns: Vec<DangerousPattern>,
    traversal_patterns: Vec<DangerousPattern>,
    unix_system_patterns: Vec<DangerousPattern>,
    windows_system_patterns: Vec<DangerousPattern>,
    sensitive_file_patterns: Vec<DangerousPattern>,
    allowed_extensions: HashSet<String>,
}
```

## Pattern Categories

### PatternCategory Enum

```rust
pub enum PatternCategory {
    Traversal,           // Directory traversal (../, ///)
    FileDestruction,     // rm -rf, dd, mkfs
    GitDestruction,      // git reset --hard, clean -fdx
    PermissiveAccess,    // chmod 777, chown
    DatabaseDestruction, // DROP, DELETE, TRUNCATE
    SystemPath,          // /etc, /bin, C:\Windows
    SensitiveFile,       // .env, credentials, .ssh
}
```

### Severity Levels

- **5** - System destruction (rm -rf /, DROP DATABASE)
- **4** - Data loss (git reset --hard, /dev access)
- **3** - Security weakening (chmod 777, DELETE FROM)
- **2** - Warning level (not currently used)
- **1** - Info level (not currently used)

## Usage Examples

### Command Validation

```rust
use superclaude_runtime::safety::SafetyValidator;

let validator = SafetyValidator::new();

// Block dangerous commands
assert!(validator.validate_command("rm -rf /").is_err());
assert!(validator.validate_command("git reset --hard").is_err());

// Allow safe commands
assert!(validator.validate_command("ls -la").is_ok());
assert!(validator.validate_command("git status").is_ok());
```

### Path Validation

```rust
use std::path::Path;

let validator = SafetyValidator::new();

// Block system paths
assert!(validator.validate_path(Path::new("/etc/passwd")).is_err());

// Block traversal
assert!(validator.validate_path(Path::new("../../../secrets")).is_err());

// Allow user paths
assert!(validator.validate_path(Path::new("/home/user/code")).is_ok());
```

### Filename Sanitization

```rust
let validator = SafetyValidator::new();

let safe = validator.sanitize_filename("file:with<bad>chars.txt");
assert_eq!(safe, "file_with_bad_chars.txt");

let safe = validator.sanitize_filename("../../../etc/passwd");
assert_eq!(safe, ".._.._.._etc_passwd");
```

## Dangerous Patterns

### File Destruction

| Pattern | Description | Severity |
|---------|-------------|----------|
| `rm -rf /` | Root deletion | 5 |
| `rm -rf /*` | Root contents deletion | 5 |
| `rm -rf ~` | Home deletion | 5 |
| `dd if=/dev/zero` | Disk wiping | 5 |
| `mkfs.` | Filesystem formatting | 5 |
| `> /dev/sd[a-z]` | Raw disk write | 5 |

### Git Destruction

| Pattern | Description | Severity |
|---------|-------------|----------|
| `git reset --hard` | Discard local changes | 4 |
| `git checkout -- <path>` | Revert files | 4 |
| `git clean -fdx` | Delete untracked files | 4 |
| `git push --force origin main` | Force push to main | 4 |

### Permissive Access

| Pattern | Description | Severity |
|---------|-------------|----------|
| `chmod 777` | Overly permissive permissions | 3 |
| `chown .* /etc` | System ownership change | 4 |

### Database Operations

| Pattern | Description | Severity |
|---------|-------------|----------|
| `DROP DATABASE` | Database deletion | 5 |
| `DROP TABLE` | Table deletion | 4 |
| `TRUNCATE TABLE` | Table truncation | 4 |
| `DELETE FROM` | Row deletion | 3 |

## Path Validation

### Unix System Directories

```
/etc/     - System configuration (severity 4)
/bin/     - Essential binaries (severity 4)
/sbin/    - System binaries (severity 4)
/usr/bin/ - User binaries (severity 4)
/var/     - Variable data (severity 3)
/tmp/     - System temporary (severity 3)
/dev/     - Device files (severity 5)
/proc/    - Process info (severity 4)
/sys/     - System info (severity 4)
```

### Windows System Directories

```
C:\Windows\       - System directory (severity 4)
C:\Program Files\ - Program installation (severity 3)
```

### Sensitive Files

```
.env              - Environment variables (severity 4)
.secret           - Secret files (severity 4)
credentials.*     - Credential files (severity 5)
passwd            - Password file (severity 5)
shadow            - Shadow passwords (severity 5)
.ssh/             - SSH keys (severity 5)
.aws/             - AWS credentials (severity 5)
.gnupg/           - GPG keys (severity 5)
```

## Integration with Hooks

The safety module integrates with the hooks system for real-time validation:

```rust
// PreToolUse hook for Bash commands
async fn validate_bash_command(input: HookInput) -> HookOutput {
    let validator = SafetyValidator::new();

    if let Some(command) = input.tool_input.get("command") {
        if let Err(e) = validator.validate_command(command) {
            return HookOutput {
                decision: "deny",
                reason: format!("{}", e),
            };
        }
    }

    HookOutput::allow()
}

// PreToolUse hook for Write/Edit operations
async fn validate_file_path(input: HookInput) -> HookOutput {
    let validator = SafetyValidator::new();

    if let Some(path) = input.tool_input.get("file_path") {
        if let Err(e) = validator.validate_path(Path::new(path)) {
            return HookOutput {
                decision: "deny",
                reason: format!("{}", e),
            };
        }
    }

    HookOutput::allow()
}
```

## Error Types

```rust
pub enum ValidationError {
    DangerousCommand {
        command: String,
        pattern: String,
        severity: u8,
    },
    PathTooLong {
        path: PathBuf,
        length: usize,
        max_length: usize,
    },
    FilenameTooLong {
        filename: String,
        length: usize,
        max_length: usize,
    },
    NullByteInPath { path: PathBuf },
    PathTraversal { path: PathBuf, pattern: String },
    SystemPath { path: PathBuf, pattern: String },
    SensitiveFile { path: PathBuf, pattern: String },
    DisallowedExtension { path: PathBuf, extension: String },
}
```

## Testing

Run the comprehensive test suite:

```bash
cargo test -p superclaude-runtime --test test_safety
```

Tests cover:
- Dangerous command detection
- Safe command allowance
- Path traversal blocking
- System path blocking
- Sensitive file blocking
- Filename sanitization
- Null byte detection
- Path length limits
- Severity levels
- Case-insensitive matching

## Configuration

### Allowed File Extensions

Default allowed extensions:

```
.md, .json, .py, .js, .ts, .jsx, .tsx, .txt,
.yml, .yaml, .toml, .cfg, .conf, .sh, .ps1,
.html, .css, .svg, .png, .jpg, .gif, .rs,
.go, .java, .c, .cpp, .h, .hpp
```

### Path Limits

- **MAX_PATH_LENGTH**: 4096 characters
- **MAX_FILENAME_LENGTH**: 255 characters

## Performance Considerations

- Patterns are compiled once during `SafetyValidator::new()`
- Regex matching is case-insensitive (`to_lowercase()`)
- Validation is synchronous (no async overhead)
- All patterns use anchored regex where appropriate (e.g., `^/etc/`)

## Platform-Specific Behavior

### Windows

- Windows reserved names checked (CON, PRN, AUX, NUL, COM1-9, LPT1-9)
- Path separators normalized (both `/` and `\` supported)
- System directories use case-insensitive matching

### Unix/Linux

- System directories checked with absolute paths
- Home directory expansion not performed (use absolute paths)

## Migration from Python

Key differences from Python implementation:

1. **Compiled patterns**: Regex is compiled once, not on each call
2. **Type safety**: Rust's type system prevents invalid patterns
3. **Error handling**: Uses `Result<(), ValidationError>` instead of tuples
4. **Performance**: Faster regex matching with compiled patterns
5. **Testing**: Comprehensive unit tests included in module

## Security Best Practices

1. **Always validate** before executing commands or file operations
2. **Log denials** for security audit trail (use `tracing::warn!`)
3. **Don't bypass** validation in production code
4. **Update patterns** when new threats are identified
5. **Test changes** with comprehensive test suite

## Future Enhancements

Potential improvements:

- [ ] Load patterns from configuration file
- [ ] Customizable severity thresholds
- [ ] Pattern hot-reloading without restart
- [ ] Integration with external threat databases
- [ ] Machine learning for pattern detection
- [ ] Audit log persistence
