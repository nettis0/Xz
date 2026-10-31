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

def youtube_theme(source):
    # YouTube TV-inspired neutral dark surfaces and red accent.
    replacements = {
        '<color name="fastlane_background">#0096a6</color>':
            '<color name="fastlane_background">#FF0033</color>',
        '<color name="fastlane_background_dark">#004B53</color>':
            '<color name="fastlane_background_dark">#181818</color>',
        '<color name="search_opaque">#0096a6</color>':
            '<color name="search_opaque">#FF0033</color>',
        '<color name="card_selected_background_white">#FFFFFF</color>':
            '<color name="card_selected_background_white">#303030</color>',
        '<color name="card_selected_text_grey">#343434</color>':
            '<color name="card_selected_text_grey">#FFFFFF</color>',
        '<color name="card_default_background_dark">#004B53</color>':
            '<color name="card_default_background_dark">#181818</color>',
        '<color name="card_default_text">#FFFFFF</color>':
            '<color name="card_default_text">#F1F1F1</color>',
        '<color name="shelf_background_dark">#131313</color>':
            '<color name="shelf_background_dark">#0F0F0F</color>',
        '<color name="scheme_grey_background">#181818</color>':
            '<color name="scheme_grey_background">#0F0F0F</color>',
        '<color name="scheme_grey_background_dark">#181818</color>':
            '<color name="scheme_grey_background_dark">#0F0F0F</color>',
        '<color name="scheme_grey_shelf_background_dark">#000000</color>':
            '<color name="scheme_grey_shelf_background_dark">#0F0F0F</color>',
        '<color name="scheme_grey_card_background_dark">#121212</color>':
            '<color name="scheme_grey_card_background_dark">#181818</color>',
    }
    for old, new in replacements.items():
        if old in source:
            source = source.replace(old, new, 1)
        elif new not in source:
            raise SystemExit("YouTube theme color not found: " + old)
    return source

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

            FrameLayout.LayoutParams params = new FrameLayout.LayoutParams(
                    buttonSize, buttonSize, Gravity.TOP | Gravity.START);
            params.leftMargin = (int) (12 * density + 0.5f);
            params.topMargin = (int) (56 * density + 0.5f);
            ((FrameLayout) root).addView(voiceSearch, params);
        }

        return root;"""
    return replace_once(source, old, new, "Add separate sidebar voice-search button")

edit("common/src/main/java/com/liskovsoft/smartyoutubetv2/common/app/presenters/service/SidebarService.java", sidebar)
edit("common/src/main/java/com/liskovsoft/smartyoutubetv2/common/app/presenters/settings/GeneralSettingsPresenter.java", general_settings)
edit("common/src/main/java/com/liskovsoft/smartyoutubetv2/common/app/presenters/settings/LanguageSettingsPresenter.java", language_settings)
edit("common/src/main/java/com/liskovsoft/smartyoutubetv2/common/misc/AppDataSourceManager.java", datasource)
edit("common/src/main/java/com/liskovsoft/smartyoutubetv2/common/app/presenters/settings/PlayerSettingsPresenter.java", player_settings)
edit("smarttubetv/src/main/java/com/liskovsoft/smartyoutubetv2/tv/ui/playback/other/VideoPlayerGlue.java", video_glue)
edit("smarttubetv/src/main/java/com/liskovsoft/smartyoutubetv2/tv/ui/playback/PlaybackActivity.java", playback_activity)
edit("common/src/main/java/com/liskovsoft/smartyoutubetv2/common/prefs/GeneralData.java", general_data)
edit("smarttubetv/src/main/java/com/liskovsoft/smartyoutubetv2/tv/ui/browse/BrowseFragment.java", browse_fragment)
edit("smarttubetv/src/main/res/values/colors.xml", youtube_theme)

print("UI customization phase 1 completed.")
