# Platform Testing Safety System

This document describes the comprehensive safety system designed to protect your real playlists and collections during platform testing.

## 🛡️ Safety Overview

The safety system ensures that **no real playlists can be accidentally modified or deleted** during testing. It uses multiple layers of protection:

1. **Test Playlist Markers**: Only playlists with specific prefixes can be modified
2. **Safety Levels**: Different levels of protection for different scenarios
3. **Interactive Confirmation**: Optional user confirmation for risky operations
4. **Emergency Stop**: Ability to halt all operations immediately
5. **Automatic Cleanup**: Test playlists are automatically removed after testing

## 🏷️ Test Playlist Markers

All test playlists must start with one of these markers:

| Marker | Example | Platform Support |
|--------|---------|------------------|
| `🧪` | `🧪 My Test Playlist` | All (preferred) |
| `[TEST]` | `[TEST] Another Test` | All (fallback) |
| `SELECTA_TEST_` | `SELECTA_TEST_Legacy` | All (legacy) |

**The safety system will REFUSE to modify any playlist that doesn't start with these markers.**

## 🔒 Safety Levels

### `READ_ONLY`
- **No modifications allowed**
- Only reading/searching operations
- Perfect for investigating platform capabilities
- Use when you want to explore without any risk

### `TEST_ONLY` (Recommended)
- **Only marked test playlists can be modified**
- Real playlists are completely protected
- Default level for most testing
- Balances safety with functionality

### `INTERACTIVE`
- **Prompts for confirmation** before risky operations
- Allows operations on real playlists with user approval
- Use for manual testing with careful oversight
- Each operation requires explicit confirmation

### `DISABLED` (Dangerous!)
- **No safety checks**
- Can modify any playlist
- **Only use if absolutely necessary**
- Requires explicit user confirmation

## 🧪 Using the Safety System

### Quick Start

1. **Set up environment**:
   ```bash
   python scripts/setup_test_environment.py
   ```

2. **Run basic tests**:
   ```bash
   python scripts/test_platform_basics.py
   ```

3. **Check results**: All test playlists are automatically cleaned up

### Environment Variables

Configure safety behavior with environment variables:

```bash
# Safety level (read_only, test_only, interactive, disabled)
export SELECTA_SAFETY_LEVEL=test_only

# Require user confirmation for operations
export SELECTA_REQUIRE_CONFIRMATION=false

# Dry run mode - show what would happen without doing it
export SELECTA_DRY_RUN=true

# Maximum number of test playlists allowed
export SELECTA_MAX_TEST_PLAYLISTS=50

# Environment indicator
export SELECTA_ENVIRONMENT=testing
```

### Code Examples

#### Safe Playlist Testing
```python
from selecta.core.testing.safe_platform_tester import safe_platform_test

# Automatic cleanup and safety enforcement
with safe_platform_test() as session:
    # Create test playlist (automatically gets safety marker)
    playlist_id = session.create_safe_playlist("spotify", "My Test")

    # Add tracks safely
    tracks = session.search_for_test_tracks("spotify", "test", limit=5)
    session.add_tracks_to_playlist("spotify", playlist_id, track_ids)

    # Playlist automatically cleaned up when context exits
```

#### Manual Safety Checks
```python
from selecta.core.testing import is_test_playlist, verify_safe_operation, OperationType

# Check if playlist name is safe
if is_test_playlist("🧪 My Playlist"):
    print("Safe to modify")

# Verify operation is allowed
verify_safe_operation("🧪 Test Playlist", OperationType.MODIFY)
```

#### Emergency Stop
```python
from selecta.core.testing import emergency_stop

# Stop all operations immediately
emergency_stop()
```

## 🔧 Platform-Specific Safety

### Spotify
- ✅ **Playlist creation**: Fully supported with safety
- ✅ **Track addition/removal**: Safe for test playlists
- ❌ **Playlist deletion**: Not supported by Spotify API
- 🛡️ **Protection**: Only user-owned playlists can be modified

### Rekordbox
- ✅ **Playlist creation**: Fully supported with safety
- ✅ **Track addition/removal**: Safe for test playlists
- ⚠️ **Playlist deletion**: Implementation needed
- 🛡️ **Protection**: Database backup recommended before testing

### YouTube
- ✅ **Playlist creation**: Supported with safety
- ✅ **Track addition/removal**: Safe for test playlists
- ⚠️ **Playlist deletion**: Implementation needed
- 🛡️ **Protection**: Only user-owned playlists can be modified

### Discogs
- ✅ **Collection management**: Safe for test collections
- ❌ **Playlist creation**: Uses collection/wantlist instead
- 🛡️ **Protection**: Only designated test collections

## ⚠️ What the Safety System Prevents

### Absolutely Prevented
- ❌ Modifying playlists without test markers
- ❌ Deleting non-test playlists
- ❌ Operations when emergency stop is active
- ❌ Running in production environment

### Warned/Confirmed
- ⚠️ Operations on non-test playlists (interactive mode)
- ⚠️ Disabling safety system
- ⚠️ Large numbers of test playlists

### Logged/Audited
- 📝 All playlist operations
- 📝 Safety level changes
- 📝 Emergency stop activations
- 📝 Failed safety checks

## 🚨 Emergency Procedures

### If Something Goes Wrong

1. **Immediate action**: Press `Ctrl+C` to stop the script
2. **Emergency stop**: Run `emergency_stop()` in any Python session
3. **Check logs**: Review the operation log for what happened
4. **Manual cleanup**: Remove any test playlists manually if needed

### Recovery Steps

1. **Check created playlists**: Look for playlists starting with test markers
2. **Manual cleanup**: Delete test playlists from platform UIs
3. **Verify real playlists**: Confirm your real playlists are unchanged
4. **Review logs**: Check what operations were performed

### If Real Playlists Were Modified

This should be **impossible** with the safety system, but if it happens:

1. **Document the issue**: Note exactly what happened
2. **Check platform history**: Most platforms have operation history
3. **Restore from backup**: Use platform's undo features if available
4. **Report the bug**: This indicates a serious safety system failure

## 📝 Testing Best Practices

### Before Testing
1. ✅ Run `setup_test_environment.py` first
2. ✅ Verify authentication status
3. ✅ Choose appropriate safety level
4. ✅ Consider using dry-run mode first

### During Testing
1. ✅ Monitor logs for any warnings
2. ✅ Keep test playlists small and simple
3. ✅ Use descriptive test playlist names
4. ✅ Don't override safety checks unless necessary

### After Testing
1. ✅ Verify test playlists were cleaned up
2. ✅ Check your real playlists are unchanged
3. ✅ Review operation logs
4. ✅ Document any issues found

## 🔍 Troubleshooting

### "Permission denied" errors
- Check that playlist names have test markers
- Verify safety level allows the operation
- Confirm you're not in read-only mode

### "Not authenticated" errors
- Run platform authentication: `selecta auth <platform>`
- Check credentials are valid
- Verify platform settings

### Test playlists not cleaned up
- Check for errors during cleanup
- Manually delete remaining test playlists
- Review cleanup logs for issues

### Safety system disabled warnings
- **Never ignore these warnings**
- Only disable safety for debugging
- Always re-enable after troubleshooting

## 🎯 Testing Scenarios

The safety system enables testing these workflows safely:

1. **Basic Operations**: Create/modify test playlists
2. **Import Workflows**: Import platform playlists to local
3. **Export Workflows**: Export local playlists to platforms
4. **Sync Testing**: Test bidirectional synchronization
5. **Edge Cases**: Test error handling and recovery
6. **Performance**: Test with large numbers of tracks

All while ensuring your real music collection remains completely untouched.

---

**Remember: The safety system is designed to make testing impossible to mess up. If you encounter any way to bypass these protections, please report it immediately as a critical bug.**
