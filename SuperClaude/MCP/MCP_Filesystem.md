# Filesystem MCP Server

**Purpose**: File system operations with secure read/write capabilities and directory management

## Triggers
- File operations: read, write, create, delete, move, copy
- Directory management: list, create, remove directories
- Path operations: resolve, join, normalize paths
- File metadata: size, permissions, timestamps
- Batch file operations and pattern matching

## Choose When
- **Over native file tools**: When you need controlled, secure file access
- **For batch operations**: Multiple file operations in sequence
- **For safe operations**: Built-in permission checks and sandboxing
- **For complex patterns**: Glob patterns and recursive operations
- **For metadata**: Detailed file information and statistics

## Works Best With
- **Fetch**: Fetch content → Filesystem saves locally
- **Sequential**: Sequential plans → Filesystem executes file operations
- **Serena**: Complementary code analysis with file operations

## Examples
```
"read all .js files in src/" → Filesystem (pattern-based reading)
"create project structure" → Filesystem (directory creation)
"move old files to archive" → Filesystem (batch file operations)
"get file metadata" → Filesystem (stat operations)
"analyze code structure" → Serena (semantic analysis, not raw files)
```

## Key Features
- Secure sandboxed operations
- Pattern matching with glob support
- Recursive directory operations
- Atomic file operations
- Permission and access control
- File watching and monitoring capabilities
- Efficient batch operations