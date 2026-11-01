#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path.cwd() if (Path.cwd() / "common").is_dir() else Path(__file__).resolve().parents[1]

def edit(rel, transform):
    path = ROOT / rel
    if not path.is_file():
        raise SystemExit(f"Required source file missing: {rel}")
    source = path.read_text(encoding="utf-8")
    updated = transform(source)
    if updated == source:
        print(f"Already customized: {rel}")
    else:
        path.write_text(updated, encoding="utf-8")
        print(f"Customized: {rel}")

def replace_once(source, old, new, label):
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one exact match, found {count}")
    return source.replace(old, new, 1)

def sidebar(source):
    source = re.sub(
        r"    private void initSections\(\) \{.*?\n    \}",
        """    private void initSections() {
        // Keep only the requested YouTube-style navigation sections.
        mDefaultSections.put(R.string.header_home, MediaGroup.TYPE_HOME);
        mDefaultSections.put(R.string.header_shorts, MediaGroup.TYPE_SHORTS);
        mDefaultSections.put(R.string.header_kids_home, MediaGroup.TYPE_KIDS_HOME);
        mDefaultSections.put(R.string.header_subscriptions, MediaGroup.TYPE_SUBSCRIPTIONS);
        mDefaultSections.put(R.string.header_history, MediaGroup.TYPE_HISTORY);
        mDefaultSections.put(R.string.header_settings, MediaGroup.TYPE_SETTINGS);
    }""",
        source, count=1, flags=re.S
    )
    if "mDefaultSections.put(R.string.header_trending" in source:
        raise SystemExit("Sidebar section list replacement did not apply")
    source = replace_once(
        source,
        "        mBootSectionId = Helpers.parseInt(split, 1, MediaGroup.TYPE_HOME);",
        "        mBootSectionId = MediaGroup.TYPE_HOME;",
        "Force Home as startup section"
    )
    source = replace_once(
        source,
        "            item.videoId = null;\n\n            // Fix id collision between pinned and default sections",
        """            item.videoId = null;

            // Remove legacy default sections that are no longer part of this fork's sidebar.
            if (item.sectionId != -1 && !Helpers.equalsAny(item.sectionId, new int[] {
                    MediaGroup.TYPE_HOME,
                    MediaGroup.TYPE_SHORTS,
                    MediaGroup.TYPE_KIDS_HOME,
                    MediaGroup.TYPE_SUBSCRIPTIONS,
                    MediaGroup.TYPE_HISTORY,
                    MediaGroup.TYPE_SETTINGS
            })) {
                return true;
            }

            // Fix id collision between pinned and default sections""",
        "Remove unsupported legacy sidebar sections"
    )
    return source

def general_settings(source):
    source = replace_once(source, "        appendBackgroundPlaybackCategory(settingsPresenter);\n", "", "Remove background playback settings")
    source = replace_once(source, "        appendScreenDimmingCategory(settingsPresenter);\n", "", "Remove screen dimming settings")
    source = replace_once(
        source,
        """        for (int[] pair : new int[][] {
                {R.string.app_exit_none, GeneralData.EXIT_NONE},
                {R.string.app_double_back_exit, GeneralData.EXIT_DOUBLE_BACK},
                {R.string.app_single_back_exit, GeneralData.EXIT_SINGLE_BACK}}) {""",
        """        for (int[] pair : new int[][] {
                {R.string.app_double_back_exit, GeneralData.EXIT_DOUBLE_BACK}}) {""",
        "Keep double-Back exit only"
    )
    return source

def language_settings(source):
    return replace_once(source, "        appendCountryCategory(settingsPresenter);\n", "", "Remove country selector")

def datasource(source):
    source = replace_once(source, "import com.liskovsoft.smartyoutubetv2.common.app.presenters.settings.BackupSettingsPresenter;\n", "", "Remove backup import")
    source = replace_once(
        source,
        """        settingItems.add(new SettingsItem(
                context.getString(R.string.app_backup_restore), () -> BackupSettingsPresenter.instance(context).show(), R.drawable.settings_backup));
""",
        "",
        "Remove backup/restore menu entry"
    )
    return source

def player_settings(source):
    source = replace_once(
        source,
        "                {R.string.screen_dimming, PlayerTweaksData.PLAYER_BUTTON_SCREEN_DIMMING},\n",
        "",
        "Remove screen dimming player button"
    )
    source = replace_once(
        source,
        "                {R.string.run_in_background, PlayerTweaksData.PLAYER_BUTTON_PIP},\n",
        "",
        "Remove background/PiP player button"
    )
    return source

def video_glue(source):
    for line, label in [
        ("import com.liskovsoft.smartyoutubetv2.tv.ui.playback.actions.ScreenDimmingAction;\n", "Remove dimming action import"),
        ("import com.liskovsoft.smartyoutubetv2.tv.ui.playback.actions.PipAction;\n", "Remove PiP action import"),
        ("        putAction(new PipAction(context));\n", "Remove PiP action"),
        ("        putAction(new ScreenDimmingAction(context));\n", "Remove dimming action"),
    ]:
        source = replace_once(source, line, "", label)
    source = replace_once(
        source,
        """        if (mPlayerTweaksData.isPlayerButtonEnabled(PlayerTweaksData.PLAYER_BUTTON_PIP)) {
            adapter.add(mActions.get(R.id.action_pip));
        }
""",
        "",
        "Remove PiP control"
    )
    source = replace_once(
        source,
        """        if (mPlayerTweaksData.isPlayerButtonEnabled(PlayerTweaksData.PLAYER_BUTTON_SCREEN_DIMMING)) {
            adapter.add(mActions.get(R.id.action_screen_dimming));
        }
""",
        "",
        "Remove screen dimming control"
    )
    return source

def playback_activity(source):
    pattern = r"    @Override\n    public void onUserLeaveHint\(\) \{.*?\n    \}"
    replacement = """    @Override
    public void onUserLeaveHint() {
        // Background playback and picture-in-picture are intentionally disabled in this fork.
        super.onUserLeaveHint();
    }"""
    updated, count = re.subn(pattern, replacement, source, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"Disable background playback: expected one method, found {count}")
    return updated

def general_data(source):
    return replace_once(
        source,
        "        mAppExitShortcut = Helpers.parseInt(split, 3, EXIT_DOUBLE_BACK);",
        "        mAppExitShortcut = EXIT_DOUBLE_BACK;",
        "Force double-Back app exit"
    )

def browse_fragment(source):
    source = replace_once(
        source,
        "import android.view.ViewGroup;\n",
        "import android.view.ViewGroup;\nimport android.view.Gravity;\nimport android.graphics.Color;\nimport android.graphics.PorterDuff;\nimport android.graphics.drawable.GradientDrawable;\nimport android.widget.FrameLayout;\nimport android.widget.ImageButton;\n",
        "Add voice search view imports"
    )
    old = """        mProgressBarManager.setRootView((ViewGroup) root);

        return root;"""
    new = """        mProgressBarManager.setRootView((ViewGroup) root);

        // Separate voice-search shortcut; the standard search orb remains text search.
        if (root instanceof FrameLayout) {
            ImageButton voiceSearch = new ImageButton(requireContext());
            voiceSearch.setImageResource(android.R.drawable.ic_btn_speak_now);
            voiceSearch.setContentDescription("Voice search");
            voiceSearch.setFocusable(true);
            voiceSearch.setClickable(true);
            float density = getResources().getDisplayMetrics().density;
            int buttonSize = (int) (48 * density + 0.5f);
            int inset = (int) (11 * density + 0.5f);
            GradientDrawable micBackground = new GradientDrawable();
            micBackground.setShape(GradientDrawable.OVAL);
            micBackground.setColor(Color.rgb(38, 38, 38));
            micBackground.setStroke(Math.max(1, (int) density), Color.rgb(90, 90, 90));
            voiceSearch.setBackground(micBackground);
            voiceSearch.setPadding(inset, inset, inset, inset);
            voiceSearch.setColorFilter(Color.WHITE, PorterDuff.Mode.SRC_IN);
            voiceSearch.setElevation(6 * density);
            voiceSearch.setOnClickListener(v ->
                    SearchPresenter.instance(requireContext()).startVoice());

            // Keep the focusable mic away from the sidebar list so DPAD navigation
            // can reach every section, including Settings.
            FrameLayout.LayoutParams params = new FrameLayout.LayoutParams(
                    buttonSize, buttonSize, Gravity.TOP | Gravity.END);
            params.rightMargin = (int) (88 * density + 0.5f);
            params.topMargin = (int) (8 * density + 0.5f);
            ((FrameLayout) root).addView(voiceSearch, params);
        }

        return root;"""
    return replace_once(source, old, new, "Add separate sidebar voice-search button")



def install_hub():
    template = Path(__file__).resolve().parent / "HubActivity.java"
    target = ROOT / "smarttubetv/src/main/java/com/liskovsoft/smartyoutubetv2/tv/ui/main/HubActivity.java"
    if not template.is_file():
        raise SystemExit("Required launcher template missing: tools/HubActivity.java")
    target.parent.mkdir(parents=True, exist_ok=True)
    source = template.read_text(encoding="utf-8")
    if target.is_file() and target.read_text(encoding="utf-8") == source:
        print("Already customized: HubActivity.java")
    else:
        target.write_text(source, encoding="utf-8")
        print("Installed TV app hub: HubActivity.java")


def disable_background_backup_and_warmup(source):
    patterns = [
        r"(?m)^import com\.liskovsoft\.smartyoutubetv2\.common\.misc\.GDriveBackupWorker;\r?\n",
        r"(?m)^import com\.liskovsoft\.smartyoutubetv2\.common\.misc\.LocalDriveBackupWorker;\r?\n",
        r"(?m)^import com\.liskovsoft\.youtubeapi\.service\.YouTubeServiceManager;\r?\n",
        r"(?m)^\s*GDriveBackupWorker\.schedule\(getContext\(\)\);\r?\n",
        r"(?m)^\s*LocalDriveBackupWorker\.schedule\(getContext\(\)\);\r?\n",
        r"(?m)^\s*YouTubeServiceManager\.instance\(\)\.refreshCacheIfNeeded\(\); // warm up player engine\r?\n",
    ]
    for pattern in patterns:
        source = re.sub(pattern, "", source)
    return source

def hub_manifest(source):
    launcher_filter = """            <intent-filter>
                <action android:name="android.intent.action.MAIN" />

                <category android:name="android.intent.category.DEFAULT"/>
                <category android:name="android.intent.category.LAUNCHER" />
                <category android:name="android.intent.category.LEANBACK_LAUNCHER" />
            </intent-filter>
"""
    source = replace_once(source, launcher_filter, "", "Move launcher entry from SplashActivity")
    source = replace_once(source, 'android:allowBackup="true"', 'android:allowBackup="false"', "Disable Android backup for this fork")
    source = replace_once(
        source,
        "    </queries>",
        """        <package android:name="ru.rutube.app" />
        <package android:name="ru.rutube.tv" />
        <package android:name="ru.kinopoisk" />
    </queries>""",
        "Allow TV hub to detect supported streaming apps"
    )
    activity = """        <activity
            android:name="com.liskovsoft.smartyoutubetv2.tv.ui.main.HubActivity"
            android:exported="true"
            android:launchMode="singleTask"
            android:configChanges="screenSize|smallestScreenSize|screenLayout|orientation|layoutDirection"
            android:screenOrientation="unspecified">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.DEFAULT" />
                <category android:name="android.intent.category.LAUNCHER" />
                <category android:name="android.intent.category.LEANBACK_LAUNCHER" />
            </intent-filter>
        </activity>

"""
    return replace_once(
        source,
        "        <activity\n            android:name=" + '"com.liskovsoft.smartyoutubetv2.tv.ui.main.SplashActivity"',
        activity + "        <activity\n            android:name=" + '"com.liskovsoft.smartyoutubetv2.tv.ui.main.SplashActivity"',
        "Add TV streaming app hub as launcher"
    )

def vless_dialog_navigation(source):
    # The nested settings dialog must be closed before Android's AlertDialog editor is shown.
    # Re-open the Network page after dismissing the editor so the user stays in the same place.
    old = """        settingsPresenter.appendSingleButton(UiOptionItem.from(title, optionItem -> {
            appendNetworkErrorFixing(settingsPresenter);

            appendProxyManager(settingsPresenter);

            appendVlessProfile(settingsPresenter);

            appendConscrypt(settingsPresenter);

            appendDNSCategory(settingsPresenter);

            settingsPresenter.showDialog(title);
        }));"""
    new = """        settingsPresenter.appendSingleButton(UiOptionItem.from(title, option ->
                showNetworkSettings(settingsPresenter)));
    }

    private void showNetworkSettings(AppDialogPresenter settingsPresenter) {
        String title = getContext().getString(R.string.network_settings);
        appendNetworkErrorFixing(settingsPresenter);
        appendProxyManager(settingsPresenter);
        appendVlessProfile(settingsPresenter);
        appendConscrypt(settingsPresenter);
        appendDNSCategory(settingsPresenter);
        settingsPresenter.showDialog(title);"""
    source = replace_once(source, old, new, "Keep Network settings navigation in one place")

    source = replace_once(
        source,
        "        if (store.hasProfile()) {\n            XrayVlessManager manager = XrayVlessManager.instance(getContext());",
        """        if (store.hasProfile()) {
            settingsPresenter.appendSingleButton(UiOptionItem.from("Copy saved VLESS link", option -> {
                android.content.ClipboardManager clipboard = (android.content.ClipboardManager) getContext().getSystemService(Context.CLIPBOARD_SERVICE);
                if (clipboard != null) {
                    clipboard.setPrimaryClip(android.content.ClipData.newPlainText("VLESS profile", store.getShareUri()));
                    MessageHelpers.showMessage(getContext(), "VLESS link copied to clipboard");
                }
            }));
            XrayVlessManager manager = XrayVlessManager.instance(getContext());""",
        "Add a local VLESS profile export action"
    )

    old = """        settingsPresenter.appendSingleButton(UiOptionItem.from(title, description, option -> {
            SimpleEditDialog.show(getContext(), "Import VLESS profile", "vless://…", store.getShareUri(), value -> {
                try {
                    VlessConfigBuilder.Profile profile = VlessConfigBuilder.parse(value);
                    // Generate once here so malformed transport-specific options are rejected before saving.
                    VlessConfigBuilder.buildXrayConfig(value);
                    store.saveShareUri(value);
                    MessageHelpers.showMessage(getContext(), "VLESS profile saved: " + profile.host + ":" + profile.port + ". Open Network settings again to start it.");
                    return true;
                } catch (Exception e) {
                    MessageHelpers.showMessage(getContext(), "Invalid VLESS profile: " + (e.getMessage() == null ? "check the link" : e.getMessage()));
                    return false;
                }
            });
        }));"""
    new = """        settingsPresenter.appendSingleButton(UiOptionItem.from(title, description, option -> {
            // AlertDialog does not reliably receive TV focus while AppDialogView is on top.
            settingsPresenter.closeDialog();
            new Handler(Looper.getMainLooper()).postDelayed(() ->
                    SimpleEditDialog.show(getContext(), "Import VLESS profile", "vless://…", store.getShareUri(), value -> {
                        try {
                            VlessConfigBuilder.Profile profile = VlessConfigBuilder.parse(value);
                            VlessConfigBuilder.buildXrayConfig(value);
                            store.saveShareUri(value);
                            MessageHelpers.showMessage(getContext(), "VLESS profile saved: " + profile.host + ":" + profile.port);
                            return true;
                        } catch (Exception e) {
                            MessageHelpers.showMessage(getContext(), "Invalid VLESS profile: " + (e.getMessage() == null ? "check the link" : e.getMessage()));
                            return false;
                        }
                    }, () -> new Handler(Looper.getMainLooper()).postDelayed(
                            () -> reopenNetworkSettings(settingsPresenter), 180)), 180);
        }));"""
    source = replace_once(source, old, new, "Restore TV focus for VLESS key entry")

    old = """    private void startVless(XrayVlessManager manager, AppDialogPresenter settingsPresenter) {
        settingsPresenter.closeDialog();
        new Thread(() -> {
            try {
                manager.start();
                new Handler(Looper.getMainLooper()).post(() -> MessageHelpers.showMessage(getContext(),
                        "VLESS started. Only SmartTube requests that honor the app proxy are routed; this is not a device-wide VPN."));
            } catch (Exception e) {
                new Handler(Looper.getMainLooper()).post(() -> MessageHelpers.showMessage(getContext(),
                        "VLESS could not start. Check that libXray is installed and the profile is valid."));
            }
        }, "smarttube-vless-start").start();
    }"""
    new = """    private void startVless(XrayVlessManager manager, AppDialogPresenter settingsPresenter) {
        settingsPresenter.closeDialog();
        new Thread(() -> {
            boolean started = false;
            try {
                manager.start();
                started = true;
            } catch (Exception ignored) {
                // Do not expose profile credentials or native config in UI messages.
            }
            final boolean success = started;
            new Handler(Looper.getMainLooper()).postDelayed(() -> {
                MessageHelpers.showMessage(getContext(), success
                        ? "VLESS started for supported SmartTube requests"
                        : "VLESS could not start. Check the saved profile and libXray core.");
                reopenNetworkSettings(settingsPresenter);
            }, 180);
        }, "smarttube-vless-start").start();
    }"""
    source = replace_once(source, old, new, "Keep Network settings open after VLESS start")

    old = """    private void stopVless(XrayVlessManager manager, AppDialogPresenter settingsPresenter) {
        settingsPresenter.closeDialog();
        new Thread(() -> {
            try {
                manager.stop();
                new Handler(Looper.getMainLooper()).post(() -> MessageHelpers.showMessage(getContext(), "VLESS stopped"));
            } catch (Exception e) {
                new Handler(Looper.getMainLooper()).post(() -> MessageHelpers.showMessage(getContext(),
                        "VLESS stop reported an error. Restart SmartTube if proxy settings remain stuck."));
            }
        }, "smarttube-vless-stop").start();
    }"""
    new = """    private void stopVless(XrayVlessManager manager, AppDialogPresenter settingsPresenter) {
        settingsPresenter.closeDialog();
        new Thread(() -> {
            boolean stopped = false;
            try {
                manager.stop();
                stopped = true;
            } catch (Exception ignored) {
                // Keep native errors and profile data out of logs and UI.
            }
            final boolean success = stopped;
            new Handler(Looper.getMainLooper()).postDelayed(() -> {
                MessageHelpers.showMessage(getContext(), success
                        ? "VLESS stopped"
                        : "VLESS stop failed. Restart SmartTube if the proxy remains active.");
                showNetworkSettings(settingsPresenter);
            }, 180);
        }, "smarttube-vless-stop").start();
    }"""
    return replace_once(source, old, new, "Keep Network settings open after VLESS stop")

edit("common/src/main/java/com/liskovsoft/smartyoutubetv2/common/app/presenters/service/SidebarService.java", sidebar)
edit("common/src/main/java/com/liskovsoft/smartyoutubetv2/common/app/presenters/settings/GeneralSettingsPresenter.java", vless_dialog_navigation)
edit("common/src/main/java/com/liskovsoft/smartyoutubetv2/common/app/presenters/settings/GeneralSettingsPresenter.java", general_settings)
edit("common/src/main/java/com/liskovsoft/smartyoutubetv2/common/app/presenters/settings/LanguageSettingsPresenter.java", language_settings)
edit("common/src/main/java/com/liskovsoft/smartyoutubetv2/common/misc/AppDataSourceManager.java", datasource)
edit("common/src/main/java/com/liskovsoft/smartyoutubetv2/common/app/presenters/settings/PlayerSettingsPresenter.java", player_settings)
edit("smarttubetv/src/main/java/com/liskovsoft/smartyoutubetv2/tv/ui/playback/other/VideoPlayerGlue.java", video_glue)
edit("smarttubetv/src/main/java/com/liskovsoft/smartyoutubetv2/tv/ui/playback/PlaybackActivity.java", playback_activity)
edit("common/src/main/java/com/liskovsoft/smartyoutubetv2/common/prefs/GeneralData.java", general_data)
edit("smarttubetv/src/main/java/com/liskovsoft/smartyoutubetv2/tv/ui/browse/BrowseFragment.java", browse_fragment)
install_hub()
edit("smarttubetv/src/main/AndroidManifest.xml", hub_manifest)
edit("common/src/main/java/com/liskovsoft/smartyoutubetv2/common/app/presenters/SplashPresenter.java", disable_background_backup_and_warmup)

print("UI customization phase 1 completed.")
