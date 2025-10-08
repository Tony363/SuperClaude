# SuperClaude Troubleshooting Guide

## Common Issues and Solutions

### Installation Errors

#### Error: "Failed components: core"
**Symptom**: Installation fails with core component error
```
[✗] Installation completed with errors in 32.7 seconds
[✗] Failed components: core
[✗] Installation failed. Check logs for details.
```

**Cause**: Corrupted metadata file (`~/.claude/.superclaude-metadata.json`)

**Solutions**:

##### Quick Fix (Recommended)
```bash
# Use the new clean command
SuperClaude clean --metadata
SuperClaude install --force
```

##### Alternative Fix
```bash
# Use the fix script
cd /home/tony/Desktop/SuperClaude_Framework
./scripts/fix_installation.sh --backup
```

##### Manual Fix
```bash
# Remove corrupted metadata
rm -f ~/.claude/.superclaude-metadata.json
rm -f ~/.claude/settings.json

# Reinstall
SuperClaude install --force --yes
```

---

#### Error: "SuperClaude: error: argument operation: invalid choice: 'clean'"
**Symptom**: Trying to run `SuperClaude clean` fails
**Cause**: Using old documentation - clean command was just added
**Solution**: Update to latest version or use manual cleanup

---

### Command Not Found

#### Error: "SuperClaude: command not found"
**Solutions**:

1. **Check installation**:
   ```bash
   which SuperClaude
   # Should show: /home/tony/.local/bin/SuperClaude
   ```

2. **Reinstall if missing**:
   ```bash
   cd /home/tony/Desktop/SuperClaude_Framework
   pip install -e .
   ```

3. **Check PATH**:
   ```bash
   echo $PATH | grep -q "$HOME/.local/bin" || echo "PATH missing ~/.local/bin"
   ```

---

### Corrupted State Recovery

#### Clean Everything and Start Fresh
```bash
# Complete cleanup
SuperClaude clean --all --force

# Fresh install
SuperClaude install --force

# Verify
SuperClaude --version
```

#### Selective Cleanup
```bash
# Clean only metadata (preserves user files)
SuperClaude clean --metadata

# Clean cache and logs
SuperClaude clean --cache --logs

# Clean with validation
SuperClaude clean --all --validate
```

---

### Permission Issues

#### Error: "Permission denied"
**Solutions**:

1. **Fix permissions**:
   ```bash
   chmod -R u+rw ~/.claude
   ```

2. **Check ownership**:
   ```bash
   ls -la ~/.claude
   # Should be owned by your user
   ```

---

### Update Issues

#### Error during update
**Solution**: Clean and reinstall
```bash
SuperClaude clean --metadata --cache
SuperClaude update --force
```

---

## Using the Clean Command

The `SuperClaude clean` command helps recover from various issues:

### Available Options
```bash
# See all options
SuperClaude clean --help

# Clean everything (safe defaults)
SuperClaude clean

# Clean specific components
SuperClaude clean --metadata      # Corrupted settings
SuperClaude clean --cache         # Clear cache
SuperClaude clean --logs          # Remove logs
SuperClaude clean --worktrees     # Clean git worktrees

# Preview without making changes
SuperClaude clean --dry-run

# Keep recent logs (last 7 days)
SuperClaude clean --logs --keep-recent

# Validate after cleaning
SuperClaude clean --validate
```

### When to Use Clean

| Situation | Command |
|-----------|---------|
| Installation fails | `SuperClaude clean --metadata` |
| Disk space issues | `SuperClaude clean --cache --logs` |
| Corrupted settings | `SuperClaude clean --metadata --force` |
| Before fresh install | `SuperClaude clean --all` |
| Development cleanup | `SuperClaude clean --worktrees` |

---

## Fix Script

For complex issues, use the automated fix script:

```bash
cd /home/tony/Desktop/SuperClaude_Framework
./scripts/fix_installation.sh --backup --verbose
```

### Script Features
- Automatic backup before cleaning
- JSON validation checks
- Step-by-step recovery process
- Verbose mode for debugging
- Safe defaults (asks before destructive operations)

---

## Getting Help

### Check Logs
```bash
# View recent logs
tail -n 100 ~/.claude/logs/superclaude.log

# Search for errors
grep ERROR ~/.claude/logs/*.log
```

### Version Information
```bash
SuperClaude --version
```

### Available Commands
```bash
SuperClaude --help
```

---

## Prevention Tips

1. **Regular Cleanup**: Run `SuperClaude clean --cache --logs` monthly
2. **Before Updates**: Always run `SuperClaude clean --metadata` before major updates
3. **Use Force Carefully**: The `--force` flag bypasses safety checks
4. **Keep Backups**: Use `SuperClaude backup --create` before major changes

---

## Emergency Recovery

If all else fails:

```bash
# Complete removal and reinstall
cd /home/tony/Desktop/SuperClaude_Framework

# Backup your custom files
cp -r ~/.claude ~/claude.backup

# Remove everything
rm -rf ~/.claude
pip uninstall superclaude -y

# Fresh install
pip install -e .
SuperClaude install --force

# Restore custom files
cp -r ~/claude.backup/commands ~/.claude/
cp -r ~/claude.backup/agents ~/.claude/
```

---

*Updated: 2024 | SuperClaude v6.0.0*