//! Safety rules and validation for SuperClaude operations.
//!
//! This module provides security validation for:
//! - Command execution (blocking dangerous patterns)
//! - File path validation (directory traversal, system directories)
//! - URL validation
//! - Filename sanitization
//!
//! Architecture:
//! - Pattern-based matching using regex for dangerous operations
//! - Platform-specific validation (Windows vs Unix)
//! - Integration with PreToolUse hooks for real-time blocking
//!
//! Based on Python implementations:
//! - SuperClaude/Orchestrator/hooks.py (DANGEROUS_PATTERNS)
//! - setup/utils/security.py (SecurityValidator)
//! - .claude/hooks/pre-tool-use/*.sh (bash validators)

use anyhow::{Context, Result};
use regex::Regex;
use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use std::path::{Path, PathBuf};
use tracing::{debug, warn};

/// Maximum allowed path length (cross-platform)
const MAX_PATH_LENGTH: usize = 4096;

/// Maximum allowed filename length
const MAX_FILENAME_LENGTH: usize = 255;

/// Type of dangerous pattern
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum PatternCategory {
    /// Directory traversal attacks (../, ///)
    Traversal,
    /// Destructive file operations (rm -rf, dd, mkfs)
    FileDestruction,
    /// Destructive git operations (reset --hard, clean -fdx)
    GitDestruction,
    /// Overly permissive operations (chmod 777)
    PermissiveAccess,
    /// Database operations (DROP, DELETE, TRUNCATE)
    DatabaseDestruction,
    /// System directory writes
    SystemPath,
    /// Sensitive file patterns (.env, credentials, secrets)
    SensitiveFile,
}

/// A dangerous pattern rule with regex and metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DangerousPattern {
    /// Pattern category for classification
    pub category: PatternCategory,
    /// Regex pattern to match
    pub pattern: String,
    /// Human-readable description
    pub description: String,
    /// Severity level (1-5, 5 being most severe)
    pub severity: u8,
    /// Compiled regex (not serialized)
    #[serde(skip)]
    regex: Option<Regex>,
}

impl DangerousPattern {
    /// Create a new dangerous pattern
    pub fn new(
        category: PatternCategory,
        pattern: impl Into<String>,
        description: impl Into<String>,
        severity: u8,
    ) -> Result<Self> {
        let pattern_str = pattern.into();
        let regex = Regex::new(&pattern_str)
            .with_context(|| format!("Invalid regex pattern: {}", pattern_str))?;

        Ok(Self {
            category,
            pattern: pattern_str,
            description: description.into(),
            severity,
            regex: Some(regex),
        })
    }

    /// Check if pattern matches the input
    pub fn matches(&self, input: &str) -> bool {
        self.regex
            .as_ref()
            .map(|r| r.is_match(input))
            .unwrap_or(false)
    }

    /// Compile regex if not already compiled
    pub fn ensure_compiled(&mut self) -> Result<()> {
        if self.regex.is_none() {
            self.regex = Some(
                Regex::new(&self.pattern)
                    .with_context(|| format!("Failed to compile regex: {}", self.pattern))?,
            );
        }
        Ok(())
    }
}

/// Safety validator for commands and paths
#[derive(Debug, Clone)]
pub struct SafetyValidator {
    /// Dangerous command patterns
    command_patterns: Vec<DangerousPattern>,
    /// Path traversal patterns
    traversal_patterns: Vec<DangerousPattern>,
    /// Unix system directory patterns
    unix_system_patterns: Vec<DangerousPattern>,
    /// Windows system directory patterns
    windows_system_patterns: Vec<DangerousPattern>,
    /// Sensitive filename patterns
    sensitive_file_patterns: Vec<DangerousPattern>,
    /// Allowed file extensions
    allowed_extensions: HashSet<String>,
}

impl Default for SafetyValidator {
    fn default() -> Self {
        Self::new()
    }
}

impl SafetyValidator {
    /// Create a new safety validator with default patterns
    pub fn new() -> Self {
        let mut validator = Self {
            command_patterns: Vec::new(),
            traversal_patterns: Vec::new(),
            unix_system_patterns: Vec::new(),
            windows_system_patterns: Vec::new(),
            sensitive_file_patterns: Vec::new(),
            allowed_extensions: Self::default_allowed_extensions(),
        };

        // Initialize patterns (ignore errors for default initialization)
        let _ = validator.initialize_patterns();

        validator
    }

    /// Initialize all dangerous patterns
    fn initialize_patterns(&mut self) -> Result<()> {
        // File destruction patterns
        self.add_command_pattern(
            PatternCategory::FileDestruction,
            r"rm\s+-rf?\s+/\s*$",
            "Recursive deletion of root directory",
            5,
        )?;
        self.add_command_pattern(
            PatternCategory::FileDestruction,
            r"rm\s+-rf?\s+/\*",
            "Recursive deletion of root contents",
            5,
        )?;
        self.add_command_pattern(
            PatternCategory::FileDestruction,
            r"rm\s+-rf?\s+~",
            "Recursive deletion of home directory",
            5,
        )?;
        self.add_command_pattern(
            PatternCategory::FileDestruction,
            r"rm\s+-rf?\s+\$HOME",
            "Recursive deletion of $HOME",
            5,
        )?;
        self.add_command_pattern(
            PatternCategory::FileDestruction,
            r"dd\s+if=/dev/zero",
            "Disk wiping with dd",
            5,
        )?;
        self.add_command_pattern(
            PatternCategory::FileDestruction,
            r"mkfs\.",
            "Filesystem formatting",
            5,
        )?;
        self.add_command_pattern(
            PatternCategory::FileDestruction,
            r">\s*/dev/sd[a-z]",
            "Writing to raw disk device",
            5,
        )?;
        self.add_command_pattern(
            PatternCategory::FileDestruction,
            r":?\(\)\{:\|:&\};:",
            "Fork bomb pattern",
            5,
        )?;

        // Git destruction patterns
        self.add_command_pattern(
            PatternCategory::GitDestruction,
            r"git\s+reset\s+--hard",
            "Hard reset (discards local changes)",
            4,
        )?;
        self.add_command_pattern(
            PatternCategory::GitDestruction,
            r"git\s+checkout\s+--\s+",
            "Git checkout with path (reverts files)",
            4,
        )?;
        self.add_command_pattern(
            PatternCategory::GitDestruction,
            r"git\s+clean\s+-[fd]",
            "Git clean (deletes untracked files)",
            4,
        )?;
        self.add_command_pattern(
            PatternCategory::GitDestruction,
            r"git\s+push\s+.*--force.*\s+(main|master)",
            "Force push to main/master",
            4,
        )?;
        self.add_command_pattern(
            PatternCategory::GitDestruction,
            r"git\s+push\s+-f\s+.*\s+(main|master)",
            "Force push to main/master (short flag)",
            4,
        )?;

        // Permissive access patterns
        self.add_command_pattern(
            PatternCategory::PermissiveAccess,
            r"chmod\s+777\s+",
            "Overly permissive file permissions",
            3,
        )?;
        self.add_command_pattern(
            PatternCategory::PermissiveAccess,
            r"chmod\s+-R\s+777",
            "Recursive chmod 777",
            3,
        )?;
        self.add_command_pattern(
            PatternCategory::PermissiveAccess,
            r"chown\s+.*\s+/etc",
            "Ownership change on /etc",
            4,
        )?;
        self.add_command_pattern(
            PatternCategory::PermissiveAccess,
            r"chown\s+.*\s+/usr",
            "Ownership change on /usr",
            4,
        )?;
        self.add_command_pattern(
            PatternCategory::PermissiveAccess,
            r"chown\s+.*\s+/bin",
            "Ownership change on /bin",
            4,
        )?;

        // Database destruction patterns
        self.add_command_pattern(
            PatternCategory::DatabaseDestruction,
            r"DROP\s+TABLE",
            "SQL DROP TABLE",
            4,
        )?;
        self.add_command_pattern(
            PatternCategory::DatabaseDestruction,
            r"DROP\s+DATABASE",
            "SQL DROP DATABASE",
            5,
        )?;
        self.add_command_pattern(
            PatternCategory::DatabaseDestruction,
            r"DELETE\s+FROM",
            "SQL DELETE FROM",
            3,
        )?;
        self.add_command_pattern(
            PatternCategory::DatabaseDestruction,
            r"TRUNCATE\s+TABLE",
            "SQL TRUNCATE TABLE",
            4,
        )?;

        // Path traversal patterns
        self.add_traversal_pattern(r"\.\./", "Directory traversal using ../", 4)?;
        self.add_traversal_pattern(r"\.\.\.", "Directory traversal using ...", 4)?;
        self.add_traversal_pattern(r"//+", "Multiple consecutive slashes", 3)?;

        // Unix system directory patterns (anchored at start)
        self.add_unix_system_pattern(r"^/etc/", "/etc (system configuration)", 4)?;
        self.add_unix_system_pattern(r"^/bin/", "/bin (essential binaries)", 4)?;
        self.add_unix_system_pattern(r"^/sbin/", "/sbin (system binaries)", 4)?;
        self.add_unix_system_pattern(r"^/usr/bin/", "/usr/bin (user binaries)", 4)?;
        self.add_unix_system_pattern(r"^/usr/sbin/", "/usr/sbin (system binaries)", 4)?;
        self.add_unix_system_pattern(r"^/var/", "/var (variable data)", 3)?;
        self.add_unix_system_pattern(r"^/tmp/", "/tmp (system temporary)", 3)?;
        self.add_unix_system_pattern(r"^/dev/", "/dev (device files)", 5)?;
        self.add_unix_system_pattern(r"^/proc/", "/proc (process info)", 4)?;
        self.add_unix_system_pattern(r"^/sys/", "/sys (system info)", 4)?;

        // Windows system directory patterns
        self.add_windows_system_pattern(
            r"^[cC]:[/\\][wW]indows[/\\]",
            "C:\\Windows (system directory)",
            4,
        )?;
        self.add_windows_system_pattern(
            r"^[cC]:[/\\][pP]rogram [fF]iles[/\\]",
            "C:\\Program Files",
            3,
        )?;

        // Sensitive filename patterns
        self.add_sensitive_file_pattern(r"\.env$", "Environment file", 4)?;
        self.add_sensitive_file_pattern(r"\.secret", "Secret file", 4)?;
        self.add_sensitive_file_pattern(r"credentials", "Credentials file", 5)?;
        self.add_sensitive_file_pattern(r"passwd$", "Password file", 5)?;
        self.add_sensitive_file_pattern(r"shadow$", "Shadow password file", 5)?;
        self.add_sensitive_file_pattern(r"\.ssh/", "SSH directory", 5)?;
        self.add_sensitive_file_pattern(r"\.aws/", "AWS credentials directory", 5)?;
        self.add_sensitive_file_pattern(r"\.gnupg/", "GPG directory", 5)?;

        Ok(())
    }

    /// Add a command pattern
    fn add_command_pattern(
        &mut self,
        category: PatternCategory,
        pattern: &str,
        description: &str,
        severity: u8,
    ) -> Result<()> {
        self.command_patterns
            .push(DangerousPattern::new(category, pattern, description, severity)?);
        Ok(())
    }

    /// Add a traversal pattern
    fn add_traversal_pattern(&mut self, pattern: &str, description: &str, severity: u8) -> Result<()> {
        self.traversal_patterns.push(DangerousPattern::new(
            PatternCategory::Traversal,
            pattern,
            description,
            severity,
        )?);
        Ok(())
    }

    /// Add a Unix system pattern
    fn add_unix_system_pattern(&mut self, pattern: &str, description: &str, severity: u8) -> Result<()> {
        self.unix_system_patterns.push(DangerousPattern::new(
            PatternCategory::SystemPath,
            pattern,
            description,
            severity,
        )?);
        Ok(())
    }

    /// Add a Windows system pattern
    fn add_windows_system_pattern(
        &mut self,
        pattern: &str,
        description: &str,
        severity: u8,
    ) -> Result<()> {
        self.windows_system_patterns.push(DangerousPattern::new(
            PatternCategory::SystemPath,
            pattern,
            description,
            severity,
        )?);
        Ok(())
    }

    /// Add a sensitive file pattern
    fn add_sensitive_file_pattern(
        &mut self,
        pattern: &str,
        description: &str,
        severity: u8,
    ) -> Result<()> {
        self.sensitive_file_patterns.push(DangerousPattern::new(
            PatternCategory::SensitiveFile,
            pattern,
            description,
            severity,
        )?);
        Ok(())
    }

    /// Default allowed file extensions
    fn default_allowed_extensions() -> HashSet<String> {
        [
            ".md", ".json", ".py", ".js", ".ts", ".jsx", ".tsx", ".txt", ".yml", ".yaml",
            ".toml", ".cfg", ".conf", ".sh", ".ps1", ".html", ".css", ".svg", ".png", ".jpg",
            ".gif", ".rs", ".go", ".java", ".c", ".cpp", ".h", ".hpp",
        ]
        .iter()
        .map(|s| s.to_string())
        .collect()
    }

    /// Validate a bash command for dangerous patterns
    pub fn validate_command(&self, command: &str) -> Result<(), ValidationError> {
        let command_lower = command.to_lowercase();

        for pattern in &self.command_patterns {
            if pattern.matches(&command_lower) {
                warn!(
                    "Blocked dangerous command: {} (pattern: {})",
                    command, pattern.description
                );
                return Err(ValidationError::DangerousCommand {
                    command: command.to_string(),
                    pattern: pattern.description.clone(),
                    severity: pattern.severity,
                });
            }
        }

        debug!("Command validation passed: {}", command);
        Ok(())
    }

    /// Validate a file path for security issues
    pub fn validate_path(&self, path: &Path) -> Result<(), ValidationError> {
        let path_str = path.to_string_lossy();

        // Check path length
        if path_str.len() > MAX_PATH_LENGTH {
            return Err(ValidationError::PathTooLong {
                path: path.to_path_buf(),
                length: path_str.len(),
                max_length: MAX_PATH_LENGTH,
            });
        }

        // Check filename length
        if let Some(filename) = path.file_name() {
            let filename_str = filename.to_string_lossy();
            if filename_str.len() > MAX_FILENAME_LENGTH {
                return Err(ValidationError::FilenameTooLong {
                    filename: filename_str.to_string(),
                    length: filename_str.len(),
                    max_length: MAX_FILENAME_LENGTH,
                });
            }
        }

        // Check for null bytes
        if path_str.contains('\0') {
            return Err(ValidationError::NullByteInPath {
                path: path.to_path_buf(),
            });
        }

        // Check traversal patterns
        let path_lower = path_str.to_lowercase();
        for pattern in &self.traversal_patterns {
            if pattern.matches(&path_lower) {
                return Err(ValidationError::PathTraversal {
                    path: path.to_path_buf(),
                    pattern: pattern.description.clone(),
                });
            }
        }

        // Check Unix system paths
        for pattern in &self.unix_system_patterns {
            if pattern.matches(&path_lower) {
                return Err(ValidationError::SystemPath {
                    path: path.to_path_buf(),
                    pattern: pattern.description.clone(),
                });
            }
        }

        // Check Windows system paths
        for pattern in &self.windows_system_patterns {
            if pattern.matches(&path_lower) {
                return Err(ValidationError::SystemPath {
                    path: path.to_path_buf(),
                    pattern: pattern.description.clone(),
                });
            }
        }

        // Check sensitive file patterns
        for pattern in &self.sensitive_file_patterns {
            if pattern.matches(&path_lower) {
                return Err(ValidationError::SensitiveFile {
                    path: path.to_path_buf(),
                    pattern: pattern.description.clone(),
                });
            }
        }

        Ok(())
    }

    /// Validate file extension
    pub fn validate_extension(&self, path: &Path) -> Result<(), ValidationError> {
        if let Some(ext) = path.extension() {
            let ext_str = format!(".{}", ext.to_string_lossy().to_lowercase());
            if !self.allowed_extensions.contains(&ext_str) {
                return Err(ValidationError::DisallowedExtension {
                    path: path.to_path_buf(),
                    extension: ext_str,
                });
            }
        }
        Ok(())
    }

    /// Sanitize a filename by removing dangerous characters
    pub fn sanitize_filename(&self, filename: &str) -> String {
        // Remove null bytes
        let mut sanitized = filename.replace('\0', "");

        // Replace dangerous characters with underscores
        let dangerous_chars = regex::Regex::new(r#"[<>:"/\\|?*\x00-\x1f]"#).unwrap();
        sanitized = dangerous_chars.replace_all(&sanitized, "_").to_string();

        // Remove leading/trailing dots and spaces
        sanitized = sanitized.trim_matches(|c| c == '.' || c == ' ').to_string();

        // Ensure not empty
        if sanitized.is_empty() {
            sanitized = "unnamed".to_string();
        }

        // Truncate if too long
        if sanitized.len() > MAX_FILENAME_LENGTH {
            sanitized.truncate(MAX_FILENAME_LENGTH);
        }

        // Check for Windows reserved names
        #[cfg(target_os = "windows")]
        {
            let reserved_names = [
                "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6",
                "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7",
                "LPT8", "LPT9",
            ];

            let name_upper = sanitized.to_uppercase();
            for reserved in &reserved_names {
                if name_upper.starts_with(reserved) {
                    sanitized = format!("safe_{}", sanitized);
                    break;
                }
            }
        }

        sanitized
    }
}

/// Validation error types
#[derive(Debug, thiserror::Error)]
pub enum ValidationError {
    #[error("Dangerous command blocked: {command}\nReason: {pattern}\nSeverity: {severity}/5")]
    DangerousCommand {
        command: String,
        pattern: String,
        severity: u8,
    },

    #[error("Path too long: {path:?} ({length} > {max_length})")]
    PathTooLong {
        path: PathBuf,
        length: usize,
        max_length: usize,
    },

    #[error("Filename too long: {filename} ({length} > {max_length})")]
    FilenameTooLong {
        filename: String,
        length: usize,
        max_length: usize,
    },

    #[error("Null byte detected in path: {path:?}")]
    NullByteInPath { path: PathBuf },

    #[error("Path traversal detected: {path:?}\nPattern: {pattern}")]
    PathTraversal { path: PathBuf, pattern: String },

    #[error("System path access blocked: {path:?}\nPattern: {pattern}")]
    SystemPath { path: PathBuf, pattern: String },

    #[error("Sensitive file access blocked: {path:?}\nPattern: {pattern}")]
    SensitiveFile { path: PathBuf, pattern: String },

    #[error("Disallowed file extension: {path:?}\nExtension: {extension}")]
    DisallowedExtension { path: PathBuf, extension: String },
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_dangerous_command_detection() {
        let validator = SafetyValidator::new();

        // Should block
        assert!(validator.validate_command("rm -rf /").is_err());
        assert!(validator.validate_command("rm -rf /*").is_err());
        assert!(validator.validate_command("rm -rf ~").is_err());
        assert!(validator.validate_command("git reset --hard").is_err());
        assert!(validator.validate_command("git clean -fdx").is_err());
        assert!(validator.validate_command("chmod 777 /etc").is_err());
        assert!(validator.validate_command("DROP DATABASE users").is_err());

        // Should allow
        assert!(validator.validate_command("ls -la").is_ok());
        assert!(validator.validate_command("git status").is_ok());
        assert!(validator.validate_command("npm install").is_ok());
    }

    #[test]
    fn test_path_traversal_detection() {
        let validator = SafetyValidator::new();

        // Should block traversal
        assert!(validator.validate_path(Path::new("../etc/passwd")).is_err());
        assert!(validator.validate_path(Path::new("foo/../../secrets")).is_err());

        // Should allow normal paths
        assert!(validator.validate_path(Path::new("/home/user/code")).is_ok());
        assert!(validator.validate_path(Path::new("./src/main.rs")).is_ok());
    }

    #[test]
    fn test_system_path_detection() {
        let validator = SafetyValidator::new();

        // Should block system paths
        assert!(validator.validate_path(Path::new("/etc/passwd")).is_err());
        assert!(validator.validate_path(Path::new("/bin/bash")).is_err());
        assert!(validator.validate_path(Path::new("/dev/sda1")).is_err());

        // Should allow user paths
        assert!(validator.validate_path(Path::new("/home/user/.env")).is_ok());
    }

    #[test]
    fn test_sensitive_file_detection() {
        let validator = SafetyValidator::new();

        // Should block sensitive files
        assert!(validator.validate_path(Path::new(".env")).is_err());
        assert!(validator.validate_path(Path::new("credentials.json")).is_err());
        assert!(validator.validate_path(Path::new("/home/user/.ssh/id_rsa")).is_err());

        // Should allow normal files
        assert!(validator.validate_path(Path::new("config.yaml")).is_ok());
        assert!(validator.validate_path(Path::new("README.md")).is_ok());
    }

    #[test]
    fn test_filename_sanitization() {
        let validator = SafetyValidator::new();

        assert_eq!(validator.sanitize_filename("normal.txt"), "normal.txt");
        assert_eq!(validator.sanitize_filename("file:with<bad>chars"), "file_with_bad_chars");
        assert_eq!(validator.sanitize_filename("../../../etc/passwd"), ".._.._.._etc_passwd");
        assert_eq!(validator.sanitize_filename(""), "unnamed");
        assert_eq!(validator.sanitize_filename("   ...   "), "unnamed");
    }

    #[test]
    fn test_pattern_categories() {
        let validator = SafetyValidator::new();

        // File destruction
        let result = validator.validate_command("rm -rf /");
        assert!(matches!(
            result,
            Err(ValidationError::DangerousCommand { severity: 5, .. })
        ));

        // Git destruction
        let result = validator.validate_command("git reset --hard");
        assert!(matches!(
            result,
            Err(ValidationError::DangerousCommand { severity: 4, .. })
        ));

        // Permissive access
        let result = validator.validate_command("chmod 777 /etc");
        assert!(matches!(
            result,
            Err(ValidationError::DangerousCommand { severity: 3, .. })
        ));
    }
}
