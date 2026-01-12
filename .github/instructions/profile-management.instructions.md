# Personal Voice Profile Management

## Overview

The Personal Voice configuration has been refactored to support **multiple speaker profiles**. Users can now:
- Create multiple Personal Voice profiles
- Select which profile to use for synthesis via a dropdown
- Each profile is automatically saved with a name and creation date

## Data Structure

### JSON Configuration

The configuration file (`.conf/personal_voice_config.json`) now uses this structure:

```json
{
  "speech_key": "...",
  "speech_region": "southeastasia",
  "voice_name": "DragonLatestNeural",
  "language": "en-US",
  "selected_profile_id": "profile_2026_01_12",
  "profiles": [
    {
      "id": "profile_2026_01_12",
      "name": "Default Profile",
      "speaker_profile_id": "c62770c7-aaa2-40ea-8536-408e2540707c",
      "creation_date": "2026-01-12"
    }
  ],
  ...
}
```

### Key Changes

1. **`profiles` array**: Contains all speaker profiles with metadata
2. **`selected_profile_id`**: Tracks which profile is currently active
3. **No more top-level `speaker_profile_id`**: Moved into profile objects

## Profile Structure

Each profile in the `profiles` array contains:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier (auto-generated as `profile_YYYY_MM_DD_N`) |
| `name` | string | Human-readable name (from voice talent name or auto-generated) |
| `speaker_profile_id` | string | Azure Personal Voice speaker profile GUID |
| `creation_date` | string | ISO date when profile was created |

## Code Implementation

### PersonalVoiceConfig Class

New methods added to `PersonalVoiceConfig`:

```python
def get_selected_profile() -> SpeakerProfile | None:
    """Get the currently selected speaker profile."""

def add_profile(name: str, speaker_profile_id: str) -> SpeakerProfile:
    """Add a new speaker profile with auto-generated ID."""

def get_profile_choices() -> list[tuple[str, str]]:
    """Get list of (display_name, profile_id) for UI selection."""
```

### Backward Compatibility

The `from_dict()` method automatically migrates old configs:

```python
# Old format (single speaker_profile_id)
{
  "speaker_profile_id": "abc-123",
  ...
}

# Auto-migrated to:
{
  "profiles": [
    {
      "id": "profile_2026_01_12",
      "name": "Migrated Profile",
      "speaker_profile_id": "abc-123",
      "creation_date": "2026-01-12"
    }
  ],
  "selected_profile_id": "profile_2026_01_12",
  ...
}
```

## UI Changes

### Configuration Section (0️⃣)

**Removed**: Speaker profile ID input field (no longer needed)

Users only configure:
- Speech credentials
- Base voice name
- Language

### Create Personal Voice Section (1️⃣)

When creating a new Personal Voice:

1. Profile is automatically created with:
   - Name from `voice_talent_name` or auto-generated
   - Unique ID based on creation date
   - Auto-selected as active profile

2. Success message shows the profile name:
   ```
   ✅ Profile 'John Doe' saved to .conf/personal_voice_config.json
   ```

### Synthesize Text Section (2️⃣)

**New**: Profile selector dropdown at the top

```python
st.selectbox(
    "Speaker Profile",
    options=["Default Profile (2026-01-12)", "John Doe (2026-01-15)"],
    help="Select which Personal Voice profile to use for synthesis."
)
```

- Shows all available profiles with name and date
- Selection is persisted in session state
- Synthesis uses the selected profile's `speaker_profile_id`

## Testing

All tests have been updated to use the new profile structure:

```python
# Create test profile
profile = SpeakerProfile(
    id="profile_1",
    name="Test Profile",
    speaker_profile_id="spid",
    creation_date="2026-01-12",
)

# Use in config
cfg = PersonalVoiceConfig(
    speech_key="k",
    speech_region="eastus",
    profiles=[profile],
    selected_profile_id="profile_1",
)
```

## Migration Guide

### For Users

No action required! Existing configs are automatically migrated on first load.

### For Developers

When working with Personal Voice configs:

1. **Always use `get_selected_profile()`** to retrieve the active profile:
   ```python
   profile = config.get_selected_profile()
   speaker_profile_id = profile.speaker_profile_id
   ```

2. **Add new profiles using `add_profile()`**:
   ```python
   profile = config.add_profile(name="John Doe", speaker_profile_id="guid")
   # Profile is auto-selected
   save_personal_voice_config(config)
   ```

3. **Never access `speaker_profile_id` directly** from config (deprecated)

## Benefits

✅ Support for multiple Personal Voice profiles  
✅ Easy profile switching via dropdown  
✅ Automatic profile naming and organization  
✅ Backward compatible with old configs  
✅ No manual speaker profile ID entry needed  
✅ Profile metadata (name, date) for better UX
