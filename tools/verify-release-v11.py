#!/usr/bin/env python3
"""Fail the build if any required Shorts v11 patch is missing."""
from pathlib import Path
import sys

ROOT = Path.cwd() if (Path.cwd() / "common").is_dir() else Path(__file__).resolve().parents[1]


def read(rel):
    path = ROOT / rel
    if not path.is_file():
        raise SystemExit(f"RELEASE CHECK FAILED: missing {rel}")
    return path.read_text(encoding="utf-8")


def require(source, snippets, label):
    missing = [snippet for snippet in snippets if snippet not in source]
    if missing:
        raise SystemExit(f"RELEASE CHECK FAILED: {label}; missing: {missing}")
    print(f"PASS: {label}")


def forbid(source, snippets, label):
    present = [snippet for snippet in snippets if snippet in source]
    if present:
        raise SystemExit(f"RELEASE CHECK FAILED: {label}; still present: {present}")
    print(f"PASS: {label}")


grid = read("smarttubetv/src/main/java/com/liskovsoft/smartyoutubetv2/tv/ui/modern/browse/ModernGridView.java")
require(
    grid,
    [
        "mShortsSection",
        "video.isShorts = true;",
        "PlaybackPresenter.instance(getContext()).openVideo(video);",
    ],
    "Shorts cards open the selected video directly"
)

suggestions = read("common/src/main/java/com/liskovsoft/smartyoutubetv2/common/app/models/playback/controllers/SuggestionsController.java")
require(
    suggestions,
    [
        "if (current.belongsToShortsGroup())",
        "result = getNextFromGroup(current);",
        "private Video getNextFromGroup(Video current)",
        "item.sectionId = MediaGroup.TYPE_SHORTS;",
    ],
    "Next/previous navigation stays inside the Shorts feed"
)

overlay = read("smarttubetv/src/main/java/com/liskovsoft/smartyoutubetv2/tv/ui/modern/playback/ModernShortsOverlay.java")
require(
    overlay,
    [
        "addVoiceSearchButton();",
        "R.drawable.modern_ic_mic",
        "R.drawable.modern_mic_circle",
        "SearchPresenter.instance(getContext()).startVoice()",
        "public boolean onTouchEvent(MotionEvent event)",
        "mListener.onShortsNext();",
        "mListener.onShortsPrevious();",
        "mListener.onShortsTogglePlayback();",
    ],
    "Shorts microphone, swipe gestures and tap-to-pause are wired"
)

playback = read("smarttubetv/src/main/java/com/liskovsoft/smartyoutubetv2/tv/ui/modern/playback/ModernPlaybackFragment.java")
require(
    playback,
    [
        "public boolean dispatchShortsKey(KeyEvent event)",
        "mGlue.next();",
        "mGlue.previous();",
        "prefetchNextShort();",
    ],
    "Modern Shorts player handles remote navigation and prefetch"
)

general = read("common/src/main/java/com/liskovsoft/smartyoutubetv2/common/app/presenters/settings/GeneralSettingsPresenter.java")
forbid(
    general,
    [
        "appendBackgroundPlaybackCategory(settingsPresenter);",
        "appendScreenDimmingCategory(settingsPresenter);",
    ],
    "Unneeded general settings are removed"
)
require(general, ["appendNetworkCategory(settingsPresenter);"], "Network and VLESS settings remain available")

language = read("common/src/main/java/com/liskovsoft/smartyoutubetv2/common/app/presenters/settings/LanguageSettingsPresenter.java")
forbid(language, ["appendCountryCategory(settingsPresenter);"], "Country selector is removed while language setting remains")
require(language, ["appendLanguageCategory(settingsPresenter);"], "Language setting remains available")

data_source = read("common/src/main/java/com/liskovsoft/smartyoutubetv2/common/misc/AppDataSourceManager.java")
forbid(
    data_source,
    ["BackupSettingsPresenter.instance(context).show()", "R.string.app_backup_restore"],
    "Backup/restore menu entry is removed"
)

player_settings = read("common/src/main/java/com/liskovsoft/smartyoutubetv2/common/app/presenters/settings/PlayerSettingsPresenter.java")
forbid(
    player_settings,
    [
        "{R.string.screen_dimming, PlayerTweaksData.PLAYER_BUTTON_SCREEN_DIMMING}",
        "{R.string.run_in_background, PlayerTweaksData.PLAYER_BUTTON_PIP}",
    ],
    "Unneeded screen-dimming and PiP player-button settings are removed"
)

browse = read("common/src/main/java/com/liskovsoft/smartyoutubetv2/common/app/presenters/BrowsePresenter.java")
require(browse, ["MediaGroup.TYPE_SETTINGS"], "The Settings section is preserved")

print("RELEASE CHECK PASSED: all v11 Shorts, voice-search, settings and preservation checks passed.")
