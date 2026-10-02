# Pi Windows Notification Extension

Sends native **Windows toast notifications** when the Pi agent is idle (waiting for user response or has completed its task).

## Features

- Toast notification via PowerShell `ToastNotificationManager` API
- Configurable delay to avoid spam during rapid tool calls
- Optional sound alert routed to a specific audio output device (not system default)
- Custom tool `send_notify` callable by the LLM to send manual notifications
- Per-event configuration (`on_settle`, `on_turn_end`)
- **Foreground-aware** — only notifies when Pi's terminal is not active (configurable)

## Installation

The extension is auto-discovered from `~/.pi/agent/extensions/windows-notify/`. No additional setup needed — just reload pi with `/reload`.

### Audio Setup (Optional)

To route notification sounds to your laptop speakers instead of headphones:

```powershell
# Run the helper script
powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\.pi\agent\extensions\windows-notify\setup-audio.ps1"
```

This will:
1. Download and extract `nircmd.exe` if not already present (~65 KB)
2. List all available audio output devices
3. Prompt you to enter your speaker device name
4. Update `config.json` automatically

**Alternative:** Manually download [nircmd-x64.zip](https://www.nirsoft.net/utils/nircmd-x64.zip), extract `nircmd.exe`, and place it in the extension directory.

## Configuration (`config.json`)

```json
{
  "on_settle": true,              // Notify when agent finishes a task and goes idle
  "on_turn_end": false,           // Also notify at end of each turn (for long tasks)
  "idle_delay_ms": 2000,          // Delay before sending (avoids spam during rapid turns)
  "play_sound": false,            // Play a sound with the notification
  "audio_output_device": "",      // Device name for sound output (empty = system default)
  "sound_file": null,             // Path to WAV file, or null for simple beep
  "volume": 75,                   // Volume level: 0–100
  "title": "Pi Agent",            // Notification title bar text
  "show_session_name": true,      // Include session name in body
  "show_foreground": true         // Only notify when Pi window is NOT active (true = always show)
}
```

#### Option A — Interactive Wizard (Recommended)

First, install nircmd if not already present:

```
/notify-install-nircmd
```

Then run the audio setup wizard:

```
/notify-setup-audio
```

The wizard will:
1. Guide you to find your speakers/device name in Windows Sound Settings
2. Let you type the exact device name (shows common patterns as hints)
3. Update `config.json` automatically with your selection
4. Play a test toast notification through the selected device to confirm

### How to find your audio device name

Open **Windows Sound Settings** (right-click the speaker icon → *Sound settings*), then look under **Output**. The displayed name is exactly what you'll type into the wizard.

Common patterns: `Speakers (Realtek High Definition Audio)`, `Headphones`, `NVIDIA High Definition Audio`, etc.

### Option C — Manual Setup

To play sounds on your laptop speakers while headphones are the system default:

Manually edit `config.json`:
   ```json
   {
     "play_sound": true,
     "audio_output_device": "Speakers (Realtek High Definition Audio)",
     "sound_file": null,
     "volume": 75
   }
   ```

**How it works:** The extension uses [NirCmd](https://www.nirsoft.net/utils/nircmd.html) to temporarily switch the default audio endpoint for ~10 seconds before playing the sound, then restores the original default. This is done atomically so other applications are minimally affected.

## Custom Tool: `send_notify`

The LLM can call this tool to send manual notifications:

```typescript
// Example usage by the LLM
send_notify({ message: "Build complete!" })
send_notify({ title: "Deploy Status", message: "Production deployment finished" })
```

## Events Used

| Event | Purpose |
|-------|---------|
| `agent_settled` | Main notification — fires when agent is idle after completing work |
| `turn_end` | Optional progress updates at end of each turn |
| `session_start` | Notification on new session start |
| `session_shutdown` | Cleanup pending timers |
