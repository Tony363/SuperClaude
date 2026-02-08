//! Integration tests for safety module

use std::path::Path;
use superclaude_runtime::safety::{PatternCategory, SafetyValidator, ValidationError};

#[test]
fn test_dangerous_commands_blocked() {
    let validator = SafetyValidator::new();

    // File destruction
    let result = validator.validate_command("rm -rf /");
    assert!(result.is_err());
    if let Err(ValidationError::DangerousCommand { severity, .. }) = result {
        assert_eq!(severity, 5);
    }

    let result = validator.validate_command("rm -rf /*");
    assert!(result.is_err());

    let result = validator.validate_command("dd if=/dev/zero of=/dev/sda");
    assert!(result.is_err());

    // Git destruction
    let result = validator.validate_command("git reset --hard");
    assert!(result.is_err());

    let result = validator.validate_command("git clean -fdx");
    assert!(result.is_err());

    let result = validator.validate_command("git push --force origin main");
    assert!(result.is_err());

    // Database operations
    let result = validator.validate_command("DROP DATABASE production");
    assert!(result.is_err());

    let result = validator.validate_command("DELETE FROM users");
    assert!(result.is_err());
}

#[test]
fn test_safe_commands_allowed() {
    let validator = SafetyValidator::new();

    // Common safe commands
    assert!(validator.validate_command("ls -la").is_ok());
    assert!(validator.validate_command("git status").is_ok());
    assert!(validator.validate_command("git diff").is_ok());
    assert!(validator.validate_command("npm install").is_ok());
    assert!(validator.validate_command("cargo build").is_ok());
    assert!(validator.validate_command("pytest tests/").is_ok());
    assert!(validator.validate_command("cat README.md").is_ok());
}

#[test]
fn test_path_traversal_blocked() {
    let validator = SafetyValidator::new();

    // Traversal attacks
    assert!(validator.validate_path(Path::new("../etc/passwd")).is_err());
    assert!(validator.validate_path(Path::new("../../secrets")).is_err());
    assert!(validator.validate_path(Path::new("foo/../../../bar")).is_err());
}

#[test]
fn test_system_paths_blocked() {
    let validator = SafetyValidator::new();

    // Unix system paths
    assert!(validator.validate_path(Path::new("/etc/passwd")).is_err());
    assert!(validator.validate_path(Path::new("/bin/bash")).is_err());
    assert!(validator.validate_path(Path::new("/dev/sda1")).is_err());
    assert!(validator.validate_path(Path::new("/proc/cpuinfo")).is_err());

    // Windows system paths (lowercase test)
    assert!(validator.validate_path(Path::new("c:/windows/system32")).is_err());
    assert!(validator.validate_path(Path::new("c:\\windows\\system32")).is_err());
}

#[test]
fn test_sensitive_files_blocked() {
    let validator = SafetyValidator::new();

    // Environment and credential files
    assert!(validator.validate_path(Path::new(".env")).is_err());
    assert!(validator.validate_path(Path::new("credentials.json")).is_err());
    assert!(validator.validate_path(Path::new("/home/user/.ssh/id_rsa")).is_err());
    assert!(validator.validate_path(Path::new("/home/user/.aws/credentials")).is_err());
}

#[test]
fn test_safe_paths_allowed() {
    let validator = SafetyValidator::new();

    // User directories and files
    assert!(validator.validate_path(Path::new("/home/user/code/project")).is_ok());
    assert!(validator.validate_path(Path::new("./src/main.rs")).is_ok());
    assert!(validator.validate_path(Path::new("README.md")).is_ok());
    assert!(validator.validate_path(Path::new("config.yaml")).is_ok());
}

#[test]
fn test_filename_sanitization() {
    let validator = SafetyValidator::new();

    assert_eq!(validator.sanitize_filename("normal.txt"), "normal.txt");
    assert_eq!(
        validator.sanitize_filename("file:with<bad>chars.txt"),
        "file_with_bad_chars.txt"
    );
    assert_eq!(
        validator.sanitize_filename("../../../etc/passwd"),
        ".._.._.._etc_passwd"
    );
    assert_eq!(validator.sanitize_filename(""), "unnamed");
    assert_eq!(validator.sanitize_filename("   ...   "), "unnamed");
    assert_eq!(
        validator.sanitize_filename("file/with\\slashes.txt"),
        "file_with_slashes.txt"
    );
}

#[test]
fn test_null_byte_detection() {
    let validator = SafetyValidator::new();

    let result = validator.validate_path(Path::new("file\0.txt"));
    assert!(matches!(result, Err(ValidationError::NullByteInPath { .. })));
}

#[test]
fn test_path_length_limits() {
    let validator = SafetyValidator::new();

    // Path within limit
    let short_path = "a".repeat(100);
    assert!(validator.validate_path(Path::new(&short_path)).is_ok());

    // Path exceeding limit
    let long_path = "a".repeat(5000);
    let result = validator.validate_path(Path::new(&long_path));
    assert!(matches!(result, Err(ValidationError::PathTooLong { .. })));
}

#[test]
fn test_severity_levels() {
    let validator = SafetyValidator::new();

    // Severity 5 (most severe) - system destruction
    let result = validator.validate_command("rm -rf /");
    if let Err(ValidationError::DangerousCommand { severity, .. }) = result {
        assert_eq!(severity, 5);
    } else {
        panic!("Expected DangerousCommand error");
    }

    // Severity 4 - git destruction
    let result = validator.validate_command("git reset --hard");
    if let Err(ValidationError::DangerousCommand { severity, .. }) = result {
        assert_eq!(severity, 4);
    } else {
        panic!("Expected DangerousCommand error");
    }

    // Severity 3 - permissive access
    let result = validator.validate_command("chmod 777 /tmp");
    if let Err(ValidationError::DangerousCommand { severity, .. }) = result {
        assert_eq!(severity, 3);
    } else {
        panic!("Expected DangerousCommand error");
    }
}

#[test]
fn test_case_insensitive_matching() {
    let validator = SafetyValidator::new();

    // SQL commands in various cases
    assert!(validator.validate_command("DROP DATABASE test").is_err());
    assert!(validator.validate_command("drop database test").is_err());
    assert!(validator.validate_command("DrOp DaTaBaSe test").is_err());

    // Git commands in various cases
    assert!(validator.validate_command("GIT RESET --HARD").is_err());
    assert!(validator.validate_command("Git Reset --Hard").is_err());
}
