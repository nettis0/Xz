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
edit("smarttubetv/src/main/res/values/colors.xml", youtube_theme)


def set_color(source, name, value):
    pattern = rf'(<color name="{re.escape(name)}">)[^<]*(</color>)'
    updated, count = re.subn(pattern, rf'\g<1>{value}\g<2>', source, count=1)
    if count != 1:
        raise SystemExit(f"YouTube TV palette: expected one color named {name}, found {count}")
    return updated

def youtube_tv_colors(source):
    palette = {
        "default_background_gradient_end": "#0F0F0F",
        "fastlane_background": "#FF0033",
        "fastlane_background_dark": "#181818",
        "search_opaque": "#FF0033",
        "card_selected_background_white": "#303030",
        "card_selected_background_white_grey": "#3A3A3A",
        "card_selected_background_grey": "#303030",
        "card_selected_text_grey": "#FFFFFF",
        "card_default_background_dark": "#181818",
        "card_default_text": "#F1F1F1",
        "shelf_background": "#181818",
        "shelf_background_dark": "#0F0F0F",
        "icon_background": "#242424",
        "scheme_grey_background": "#0F0F0F",
        "scheme_grey_background_dark": "#0F0F0F",
        "scheme_grey_shelf_background_dark": "#0F0F0F",
        "scheme_grey_card_background_dark": "#181818",
        "scheme_red_card_background_dark": "#181818",
        "orb_color": "#272727",
        "orb_bright_color": "#3D3D3D",
        "orb_icon_color": "#FFFFFF",
    }
    for name, value in palette.items():
        source = set_color(source, name, value)
    return source

def youtube_tv_common_colors(source):
    for name, value in {
        "red": "#FF0033",
        "semi_red": "#FF0033",
        "light_red": "#FF667A",
        "dark_red": "#CC0029",
        "leanback": "#FF0033",
    }.items():
        source = set_color(source, name, value)
    return source

def youtube_tv_dimensions(source):
    for name, value in {
        "card_width": "224dp",
        "card_height": "126dp",
        "grid_item_horizontal_spacing": "16dp",
        "grid_item_vertical_spacing": "18dp",
        "lb_rounded_rect_corner_radius": "14dp",
        "search_bar_right_items_margin": "14dp",
        "browse_headers_vertical_spacing": "9dp",
        "lb_browse_rows_margin_top": "118dp",
    }.items():
        pattern = rf'(<dimen name="{re.escape(name)}">)[^<]*(</dimen>)'
        source, count = re.subn(pattern, rf'\g<1>{value}\g<2>', source, count=1)
        if count != 1:
            raise SystemExit(f"YouTube TV dimensions: expected one dimen named {name}, found {count}")
    return source

def youtube_tv_nav_title(source):
    source = replace_once(
        source,
        "import com.liskovsoft.smartyoutubetv2.common.app.presenters.PlaybackPresenter;\n",
        "import com.liskovsoft.smartyoutubetv2.common.app.presenters.PlaybackPresenter;\n"
        "import com.liskovsoft.smartyoutubetv2.common.app.presenters.SearchPresenter;\n",
        "Import voice search presenter"
    )
    source = replace_once(
        source,
        "    private SearchOrbView mSearchOrbView;\n",
        "    private SearchOrbView mSearchOrbView;\n"
        "    private SearchOrbView mVoiceSearchOrb;\n",
        "Add title voice-search field"
    )
    source = replace_once(
        source,
        "        mSearchOrbView = findViewById(R.id.title_orb);\n",
        "        mSearchOrbView = findViewById(R.id.title_orb);\n"
        "        mVoiceSearchOrb = findViewById(R.id.voice_search_orb);\n"
        "        mVoiceSearchOrb.setOnOrbClickedListener(v -> SearchPresenter.instance(getContext()).startVoice());\n"
        "        TooltipCompatHandler.setTooltipText(mVoiceSearchOrb, \"Voice search\");\n",
        "Wire voice search into the title bar"
    )
    source = replace_once(
        source,
        "        mSearchVisibility = (flags & SEARCH_VIEW_VISIBLE) == SEARCH_VIEW_VISIBLE\n"
        "                ? View.VISIBLE : View.INVISIBLE;\n",
        "        mSearchVisibility = (flags & SEARCH_VIEW_VISIBLE) == SEARCH_VIEW_VISIBLE\n"
        "                ? View.VISIBLE : View.INVISIBLE;\n"
        "        if (mVoiceSearchOrb != null) {\n"
        "            mVoiceSearchOrb.setVisibility(mSearchVisibility);\n"
        "        }\n",
        "Hide voice search with the title search controls"
    )
    return source

def youtube_tv_title_layout(source, rtl=False):
    if "voice_search_orb" in source:
        return source
    marker = "        <com.liskovsoft.smartyoutubetv2.tv.ui.widgets.search.LongClickSearchOrbView"
    focus_left = "@id/account_orb" if rtl else "@id/title_orb"
    focus_right = "@id/title_orb" if rtl else "@id/account_orb"
    mic = (
        "        <androidx.leanback.widget.SearchOrbView\n"
        "            android:id=\"@+id/voice_search_orb\"\n"
        "            android:layout_width=\"wrap_content\"\n"
        "            android:layout_height=\"wrap_content\"\n"
        "            android:transitionGroup=\"true\"\n"
        "            android:layout_marginStart=\"@dimen/search_bar_right_items_margin\"\n"
        f"            android:nextFocusLeft=\"{focus_left}\"\n"
        f"            android:nextFocusRight=\"{focus_right}\"\n"
        "            android:contentDescription=\"Voice search\"\n"
        "            app:searchOrbIcon=\"@drawable/youtube_voice_mic\"\n"
        "            app:searchOrbColor=\"@color/orb_color\"\n"
        "            app:searchOrbBrightColor=\"@color/orb_bright_color\"\n"
        "            app:searchOrbIconColor=\"@color/orb_icon_color\" />\n\n"
    )
    if marker not in source:
        raise SystemExit("YouTube TV title layout: account orb insertion point not found")
    source = source.replace(marker, mic + marker, 1)
    old = 'android:nextFocusRight="@id/account_orb"' if not rtl else 'android:nextFocusLeft="@id/account_orb"'
    new = 'android:nextFocusRight="@id/voice_search_orb"' if not rtl else 'android:nextFocusLeft="@id/voice_search_orb"'
    source = replace_once(source, old, new, "Connect title search orb to voice search focus")
    old_account = 'android:nextFocusLeft="@id/title_orb"' if not rtl else 'android:nextFocusRight="@id/title_orb"'
    new_account = 'android:nextFocusLeft="@id/voice_search_orb"' if not rtl else 'android:nextFocusRight="@id/voice_search_orb"'
    source = replace_once(source, old_account, new_account, "Connect account orb focus after voice search")
    return source

def youtube_tv_header_presenter(source):
    source = replace_once(
        source,
        "import android.graphics.drawable.ColorDrawable;\n",
        "import android.graphics.Color;\n"
        "import android.graphics.Typeface;\n"
        "import android.graphics.drawable.ColorDrawable;\n"
        "import android.graphics.drawable.GradientDrawable;\n",
        "Add YouTube TV navigation styling imports"
    )
    source = replace_once(
        source,
        "            label.setText(headerItem.getName());\n",
        "            label.setText(headerItem.getName());\n"
        "            label.setTextColor(Color.rgb(241, 241, 241));\n"
        "            label.setTextSize(15);\n"
        "            label.setTypeface(Typeface.create(\"sans-serif-medium\", Typeface.NORMAL));\n",
        "Apply YouTube TV navigation typography"
    )
    source = replace_once(
        source,
        "    protected void onSelectLevelChanged(RowHeaderPresenter.ViewHolder holder) {\n"
        "        holder.view.setAlpha(mUnselectedAlpha + holder.getSelectLevel() *\n"
        "                (1.0f - mUnselectedAlpha));\n"
        "    }\n",
        "    protected void onSelectLevelChanged(RowHeaderPresenter.ViewHolder holder) {\n"
        "        float density = holder.view.getResources().getDisplayMetrics().density;\n"
        "        GradientDrawable pill = new GradientDrawable();\n"
        "        pill.setColor(holder.getSelectLevel() > 0.05f ? Color.rgb(43, 43, 43) : Color.TRANSPARENT);\n"
        "        pill.setCornerRadius(18 * density);\n"
        "        holder.view.setBackground(pill);\n"
        "        holder.view.setAlpha(mUnselectedAlpha + holder.getSelectLevel() *\n"
        "                (1.0f - mUnselectedAlpha));\n"
        "    }\n",
        "Render focused sidebar item as a rounded YouTube-style pill"
    )
    return source

def youtube_tv_header_layout(source):
    source = source.replace(
        '    android:layout_height="match_parent"\n    android:orientation="horizontal">',
        '    android:layout_height="match_parent"\n'
        '    android:minHeight="52dp"\n'
        '    android:gravity="center_vertical"\n'
        '    android:paddingStart="12dp"\n'
        '    android:paddingEnd="12dp"\n'
        '    android:orientation="horizontal">',
        1
    )
    source = replace_once(
        source,
        '        android:layout_width="32dp"\n        android:layout_height="32dp"',
        '        android:layout_width="28dp"\n        android:layout_height="28dp"',
        "Resize sidebar icons for the YouTube TV rail"
    )
    source = replace_once(
        source,
        '        android:layout_marginTop="3dp"\n        android:layout_marginStart="10dp"',
        '        android:layout_marginStart="12dp"\n        android:textSize="15sp"\n        android:fontFamily="sans-serif-medium"\n        android:includeFontPadding="false"',
        "Restyle sidebar labels"
    )
    source = source.replace('android:maxWidth="150sp"', 'android:maxWidth="180sp"', 1)
    return source

def youtube_tv_video_card_layout(source):
    source = source.replace('android:fontFamily="sans-serif-condensed"', 'android:fontFamily="sans-serif-medium"', 1)
    source = source.replace('android:fontFamily="sans-serif-condensed"', 'android:fontFamily="sans-serif"', 1)
    return source

def create_text_file(rel, content):
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != content:
            raise SystemExit(f"New UI resource already exists with different contents: {rel}")
        print(f"Already customized: {rel}")
        return
    path.write_text(content, encoding="utf-8")
    print(f"Created: {rel}")

edit("smarttubetv/src/main/java/com/liskovsoft/smartyoutubetv2/tv/ui/widgets/browse/NavigateTitleView.java", youtube_tv_nav_title)
edit("smarttubetv/src/main/res/layout/lb_title_view.xml", lambda s: youtube_tv_title_layout(s, False))
edit("smarttubetv/src/main/res/layout-ldrtl/lb_title_view.xml", lambda s: youtube_tv_title_layout(s, True))
edit("smarttubetv/src/main/java/com/liskovsoft/smartyoutubetv2/tv/presenter/IconHeaderItemPresenter.java", youtube_tv_header_presenter)
edit("smarttubetv/src/main/res/layout/icon_header_item.xml", youtube_tv_header_layout)
edit("smarttubetv/src/main/res/layout/lb_video_card_view.xml", youtube_tv_video_card_layout)
edit("smarttubetv/src/main/res/values/colors.xml", youtube_tv_colors)
edit("common/src/main/res/values/colors.xml", youtube_tv_common_colors)
edit("smarttubetv/src/main/res/values/dimens.xml", youtube_tv_dimensions)
create_text_file(
    "smarttubetv/src/main/res/drawable/youtube_voice_mic.xml",
    """<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp"
    android:height="24dp"
    android:viewportWidth="24"
    android:viewportHeight="24">
    <path
        android:fillColor="#FFFFFFFF"
        android:pathData="M12,14c1.66,0 2.99,-1.34 2.99,-3L15,5c0,-1.66 -1.34,-3 -3,-3S9,3.34 9,5v6c0,1.66 1.34,3 3,3zM17.3,11c0,3 -2.54,5.1 -5.3,5.1S6.7,14 6.7,11H5c0,3.42 2.72,6.23 6,6.72V21h2v-3.28c3.28,-0.49 6,-3.3 6,-6.72h-1.7z" />
</vector>
"""
)
print("YouTube TV full browse-interface pass completed.")


