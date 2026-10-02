/**
 * Pi Windows Notification Extension
 *
 * Sends native Windows toast notifications when the LLM agent is idle
 * (waiting for user response or has completed its task).
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { join, dirname } from "node:path";
import { existsSync, readFileSync, writeFileSync } from "node:fs";

// ─── Default Configuration ───────────────────────────────────────────────

interface NotifyConfig {
  on_settle: boolean;
  on_turn_end: boolean;
  idle_delay_ms: number;
  play_sound: boolean;
  audio_output_device: string;
  sound_file?: string | null;
  volume: number;
  title: string;
  show_session_name: boolean;
  /** Always send notifications regardless of whether Pi window is focused.
   * Setting to false attempts foreground detection but it doesn't work reliably
   * inside pi's jiti sandbox — so this defaults to true for safety. */
  show_foreground: boolean;
}

const DEFAULT_CONFIG: NotifyConfig = {
  on_settle: true,
  on_turn_end: false,
  idle_delay_ms: 2000,
  play_sound: false,
  audio_output_device: "",
  sound_file: null,
  volume: 75,
  title: "Pi Agent",
  show_session_name: true,
  show_foreground: true,
};

// ─── Helpers ──────────────────────────────────────────────────────────────

function getExtDir(): string {
  const selfPath = __filename ?? import.meta.filename;
  if (selfPath) return dirname(selfPath);
  var home = process.env.HOME ?? process.env.USERPROFILE ?? "";
  return join(home, ".pi", "agent", "extensions", "windows-notify");
}

var _extDirCache: string | null = null;

function loadConfig(): NotifyConfig {
  var extDir = getExtDir();
  var cfgPath = join(extDir, "config.json");

  if (existsSync(cfgPath)) {
    try {
      var raw = JSON.parse(readFileSync(cfgPath, "utf8"));
      // Merge with defaults
      for (var key in DEFAULT_CONFIG) {
        if (!(key in raw)) {
          raw[key] = DEFAULT_CONFIG[key];
        }
      }
      return raw as NotifyConfig;
    } catch {
      /* ignore parse errors */
    }
  }

  return DEFAULT_CONFIG;
}

/** Ensure nircmd.exe is present. Returns path or null. */
function ensureNircmd(pi: ExtensionAPI): string | null {
  _extDirCache ??= getExtDir();
  var target = join(_extDirCache, "nircmd.exe");

  if (existsSync(target)) return target;

  // Check PATH via pi.exec
  try {
    var result = pi.exec("nircmd", ["help"], { timeout: 5000 });
    return "nircmd";
  } catch {
    /* not found on PATH */
  }

  return null;
}

/** List common audio device name patterns to help autocomplete. */
var AUDIO_HINTS = [
  "Speakers",
  "Headphones",
  "Realtek High Definition Audio",
  "HD Audio",
  "Display Audio",
  "NVIDIA High Definition Audio",
  "Intel Display Audio",
];

/** Build a PowerShell script that shows a Windows toast notification. */
function buildToastScript(title: string, body: string): string {
  // Use plain concatenation to avoid template literal parser conflicts
  var type = "Windows.UI.Notifications";
  var safeTitle = title.replace(/'/g, "''");
  var safeBody = body.replace(/'/g, "''");

  var lines = [
    "[" + type + ".ToastNotificationManager, " + type + ", ContentType = WindowsRuntime] > $null",
    "$xml = [" + type + ".ToastNotificationManager]::GetTemplateContent([" + type + ".ToastTemplateType]::ToastText01)",
    "$xml.GetElementsByTagName('text')[0].AppendChild($xml.CreateTextNode('" + safeBody + "')) > $null",
    "[" + type + ".ToastNotificationManager]::CreateToastNotifier('" + safeTitle + "').Show([" + type + ".ToastNotification]::new($xml))"
  ];

  return lines.join("; ");
}

/** Build command to play sound on a specific audio device. */
function buildSoundCommands(nircmdPath: string, config: NotifyConfig): { cmd: string; args: string[] } | null {
  if (!config.audio_output_device || !nircmdPath) return null;

  var escapedDevice = config.audio_output_device.replace(/'/g, "''");
  var volume = Math.max(0, Math.min(100, config.volume));

  // Return nircmd commands for routing + playing
  return {
    cmd: existsSync(nircmdPath) ? nircmdPath : "nircmd.exe",
    args: [
      "setdefaultsounddevice '" + escapedDevice + "' '10'",
      "playsound '" + (config.sound_file || "") + "' " + volume.toString(),
      "setdefaultsounddevice '' '2'"
    ]
  };
}

async function sendNotification(pi: ExtensionAPI, title: string, body: string): Promise<void> {
  var config = loadConfig();

  // Check if Pi's terminal is in the foreground — skip notification if so
  if (config.show_foreground && isPiInForeground()) {
    console.log("[windows-notify] Skipping: Pi window is active.");
    return;
  }

  // Send toast notification via PowerShell
  try {
    await pi.exec("powershell.exe", ["-NoProfile", "-Command", buildToastScript(config.title !== undefined ? config.title : "", body)], {
      timeout: 5000,
    });
  } catch (err: any) {
    console.error("[windows-notify] Failed to show toast:", err.message ?? err);
  }

  // Optionally play sound on specific audio device
  if (config.play_sound && ensureNircmd(pi)) {
    try {
      var script = buildSoundCommands(ensureNircmd(pi)!, config);
      if (script) {
        await pi.exec(script.cmd, script.args, { timeout: 15000 });
      } else {
        // No routing needed — just beep via PowerShell
        await pi.exec("powershell.exe", ["-NoProfile", "-Command", "[System.Console]::Beep(800, 200)"], {
          timeout: 3000,
        });
      }
    } catch (err: any) {
      console.error("[windows-notify] Failed to play sound:", err.message ?? err);
    }
  }
}

/** Write config back to disk. */
function saveConfig(config: NotifyConfig): void {
  var extDir = getExtDir();
  var cfgPath = join(extDir, "config.json");
  writeFileSync(cfgPath, JSON.stringify(config, null, 2));
}

/** Check if any console window owns the foreground.
 * NOTE: This requires C# P/Invoke via Add-Type which doesn't work reliably
 * inside pi's jiti sandbox. Returns false by default so notifications fire.
 */
function isPiInForeground(): boolean {
  // Detection not possible without file I/O or working P/Invoke in jiti context.
  // Always return false = "not in foreground" = always show notification.
  return false;
}

/** Escape text for use in notification body (truncate very long messages). */
function formatBody(message: string): string {
  var maxLen = 200;
  return message.length > maxLen ? message.slice(0, maxLen) + "\u2026" : message;
}

// ─── Extension Factory ────────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {
  // Idle timeout tracker
  var idleTimer: ReturnType<typeof setTimeout> | null = null;

  function clearIdle(): void {
    if (idleTimer !== null) {
      clearTimeout(idleTimer);
      idleTimer = null;
    }
  }

  /** Schedule a toast after the configured idle delay. */
  function scheduleNotify(title: string, body: string): void {
    var config = loadConfig();
    clearIdle();
    idleTimer = setTimeout(function () {
      sendNotification(pi, title || config.title, formatBody(body));
    }, config.idle_delay_ms);
  }

  // ── Agent settled (main notification point) ────────────────────────
  pi.on("agent_settled", async function (_event, ctx) {
    var config = loadConfig();

    if (!config.on_settle) return;

    // Only notify when truly idle
    if (!ctx.isIdle()) return;

    var body = "Ready for your next request";

    if (config.show_session_name) {
      var sessionName = pi.getSessionName();
      if (sessionName) {
        body = "Session: " + sessionName + "\n" + body;
      }
    }

    scheduleNotify(config.title || "", formatBody(body));
  });

  // ── Turn end (optional intermediate notifications) ─────────────────
  pi.on("turn_end", async function (event, ctx) {
    var config = loadConfig();
    if (!config.on_turn_end) return;

    var body = "Turn " + event.turnIndex.toString() + " completed";

    if (config.show_session_name) {
      var sessionName = pi.getSessionName();
      if (sessionName) {
        body = "Session: " + sessionName + "\n" + body;
      }
    }

    scheduleNotify(config.title || "", formatBody(body));
  });

  // ── Session start notification ─────────────────────────────────────
  pi.on("session_start", async function (_event, ctx) {
    var config = loadConfig();
    var sessionFile = ctx.sessionManager.getSessionFile() ?? "ephemeral";
    sendNotification(pi, config.title || "Pi Agent", "Session started: " + sessionFile);
  });

  // ── Custom tool for manual notifications from the LLM ──────────────
  pi.registerTool({
    name: "send_notify",
    label: "Send Notify",
    description: "Send a Windows notification. Useful to alert when an external task completes.",
    parameters: Type.Object({
      title: Type.Optional(Type.String({ default: "", description: "Notification title (empty = use config)" })),
      message: Type.String({ description: "The notification body text" }),
    }),
    async execute(_toolCallId, params) {
      var config = loadConfig();
      var title = params.title || config.title || "";
      sendNotification(pi, title, formatBody(params.message));

      return {
        content: [
          { type: "text", text: 'Notification sent: "' + title + '" - ' + params.message },
        ],
        details: {},
      };
    },
  });

  // ── Install nircmd.exe ─────────────────────────────────────────────
  pi.registerCommand("notify-install-nircmd", {
    description: "Download and install nircmd.exe for audio device routing",
    handler: async function (_args, ctx) {
      if (!ctx.hasUI) {
        ctx.ui.notify("Installation requires TUI mode.", "warning");
        return;
      }

      var extDir = getExtDir();
      var targetExe = join(extDir, "nircmd.exe");
      var targetZip = join(extDir, "nircmd-x64.zip");

      // Check if already installed
      if (existsSync(targetExe)) {
        ctx.ui.notify("nircmd.exe is already installed at:\n" + targetExe, "info");
        return;
      }

      ctx.ui.setStatus("notify-install", "Downloading nircmd...");
      try {
        await pi.exec(
          "powershell.exe",
          [
            "-NoProfile",
            "-Command",
            "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; " +
              "Invoke-WebRequest -Uri 'https://www.nirsoft.net/utils/nircmd-x64.zip' -OutFile '" +
              targetZip.replace(/'/g, "''") + "';"
          ],
          { timeout: 30000 }
        );

        ctx.ui.setStatus("notify-install", "Extracting...");
        await pi.exec(
          "powershell.exe",
          [
            "-NoProfile",
            "-Command",
            "Add-Type -AssemblyName System.IO.Compression.FileSystem; " +
              "[System.IO.Compression.ZipFile]::ExtractToDirectory('" +
              targetZip.replace(/'/g, "''") + "', '" + extDir.replace(/'/g, "''") + "');"
          ],
          { timeout: 10000 }
        );

        // Clean up zip file
        try {
          if (existsSync(targetZip)) require("node:fs").unlinkSync(targetZip);
        } catch { /* ignore cleanup errors */ }
      } finally {
        ctx.ui.setStatus("notify-install", undefined);
      }

      if (!existsSync(targetExe)) {
        ctx.ui.notify(
          'Download failed. Please manually download from https://www.nirsoft.net/utils/nircmd-x64.zip\n' +
            'Extract nircmd.exe to:\n' + extDir,
          "error"
        );
        return;
      }

      ctx.ui.notify('nircmd.exe installed successfully at: ' + targetExe, "info");
    },
  });

  // ── Audio device selection wizard ──────────────────────────────────
  pi.registerCommand("notify-setup-audio", {
    description: "Interactive wizard to select audio output device for notifications",
    handler: async function (_args, ctx) {
      if (!ctx.hasUI) {
        ctx.ui.notify("Audio wizard requires TUI mode.", "warning");
        return;
      }

      var extDir = getExtDir();
      var targetExe = join(extDir, "nircmd.exe");
      var hasNircmd = existsSync(targetExe);

      // Step 1: Ensure nircmd is installed
      if (!hasNircmd) {
        ctx.ui.notify(
          'Step 1 of 2: Install nircmd first (needed for audio routing).\n' +
            '/notify-install-nircmd',
          "info"
        );
        return;
      }

      // Step 2: Guide user to find their device name in Windows Settings
      ctx.ui.setStatus("notify-setup-audio", "Guide active...");
      try {
        var guideText = [
          "Find your speakers/device name:",
          "",
          "1. Right-click speaker icon → Sound settings",
          "2. Under 'Output', note the device name",
          "3. Type that exact name below",
          "",
          "Common patterns:",
        ].concat(AUDIO_HINTS.map(function (h) { return "    - " + h; })).join("\n");

        ctx.ui.notify(guideText, "info");

        // Step 3: Let user type their device name with hints as suggestions
        var choice = await ctx.ui.input(
          "Enter audio output device name (or press Enter to cancel):",
          ""
        );
      } finally {
        ctx.ui.setStatus("notify-setup-audio", undefined);
      }

      if (!choice || !choice.trim()) {
        ctx.ui.notify("Setup cancelled.", "info");
        return;
      }

      // Update config
      var config = loadConfig();
      config.audio_output_device = choice.trim();
      config.play_sound = true;
      saveConfig(config);

      ctx.ui.setStatus("notify-setup-audio", "Testing sound...");
      try {
        sendNotification(pi, "Pi Agent - Sound Test", "Audio routing to: " + choice.trim());
        await new Promise(function (r) { setTimeout(r, 2000); });
      } finally {
        ctx.ui.setStatus("notify-setup-audio", undefined);
      }

      ctx.ui.notify(
        'Sound device set to: "' + choice.trim() + '". Notifications will play through this output.',
        "info"
      );
    },
  });

  // ── Cleanup on shutdown ────────────────────────────────────────────
  pi.on("session_shutdown", function () {
    clearIdle();
  });
}
