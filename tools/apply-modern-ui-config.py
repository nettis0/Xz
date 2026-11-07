в4#!/usr/bin/env python3
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
    replacement = """    private void initPinnedSections() {
        mSections.clear();

        Collection<Video> pinnedItems = getSidebarService().getPinnedItems();

        for (Video item : pinnedItems) {
            if (item == null) {
                continue;
            }

            if (item.sectionId == -1) { // Keep user-pinned channels and playlists
                BrowseSection section = createPinnedSection(item);
                mSections.add(section);
            } else if (Helpers.equalsAny(item.sectionId, new int[] {
                    MediaGroup.TYPE_HOME,
                    MediaGroup.TYPE_SHORTS,
                    MediaGroup.TYPE_KIDS_HOME,
                    MediaGroup.TYPE_SUBSCRIPTIONS,
                    MediaGroup.TYPE_HISTORY,
                    MediaGroup.TYPE_SETTINGS
            })) {
                BrowseSection section = mSectionsMapping.get(item.sectionId);
                if (section != null) {
                    mSections.add(section);
                }
            }
        }
    }"""
    pattern = re.compile(r"    private void initPinnedSections\(\) \{.*?\n    \}", re.S)
    source, count = pattern.subn(replacement, source, count=1)
    if count != 1:
        if replacement not in source:
            raise SystemExit(f"Could not replace initPinnedSections(): found {count} matches")

    settings_old = """        if (getSidebarService().isSettingsSectionEnabled()) {
            mSectionsMapping.put(MediaGroup.TYPE_SETTINGS, new BrowseSection(MediaGroup.TYPE_SETTINGS, getContext().getString(R.string.header_settings), BrowseSection.TYPE_SETTINGS_GRID, R.drawable.icon_settings));
        }"""
    settings_new = """        // Settings must remain available in the modern interface.
        mSectionsMapping.put(MediaGroup.TYPE_SETTINGS, new BrowseSection(MediaGroup.TYPE_SETTINGS, getContext().getString(R.string.header_settings), BrowseSection.TYPE_SETTINGS_GRID, R.drawable.icon_settings));"""
    if settings_old in source:
        source = source.replace(settings_old, settings_new, 1)
    elif settings_new not in source:
        raise SystemExit("Could not ensure the Settings section is always registered.")

    boot_old = """        int bootSectionId = getSidebarService().getBootSectionId();

        // Empty Home on first run fix. Switch to something non-empty.
        if (!getSignInService().isSigned() && VideoStateService.instance(getContext()).isEmpty()) {
            bootSectionId = MediaGroup.TYPE_MUSIC;
        }"""
    boot_new = """        // Always open Home, as requested for this TV build.
        int bootSectionId = MediaGroup.TYPE_HOME;"""
    if boot_old in source:
        source = source.replace(boot_old, boot_new, 1)
    elif boot_new not in source:
        raise SystemExit("Could not force Home as the startup section.")

    return source


def enable_modern_player(source):
    source = replace_once(
        source,
        "ModernActivityResolver resolver = new ModernActivityResolver(MainUIData.instance(this).isModernUiEnabled());",
        "ModernActivityResolver resolver = new ModernActivityResolver(true);",
        "Enable the modern TV interface for all supported screens"
    )
    source = replace_once(
        source,
        "import com.liskovsoft.smartyoutubetv2.tv.ui.playback.PlaybackActivity;\n",
        "import com.liskovsoft.smartyoutubetv2.tv.ui.modern.playback.ModernPlaybackActivity;\n",
        "Import the modern playback activity"
    )
    return replace_once(
        source,
        "viewManager.register(PlaybackView.class, resolver.resolve(PlaybackView.class, PlaybackActivity.class), root);",
        "viewManager.register(PlaybackView.class, ModernPlaybackActivity.class, root);",
        "Explicitly route every video to the modern YouTube TV player"
    )


def lock_modern_interface_setting(source):
    # The fork now uses the modern interface for browse AND playback. Hide the
    # obsolete per-profile switch so it cannot imply that only the home screen
    # changes while the player remains classic.
    return replace_once(
        source,
        "        appendModernInterface(settingsPresenter);\n",
        "        // Modern TV interface is enabled consistently across the whole app.\n",
        "Remove obsolete modern-interface toggle"
    )


def shorts_overlay(source):
    replacement = """    private boolean movePanelFocus(int keyCode) {
        View focused = findFocus();

        if (focused == null) {
            return false;
        }

        int actionIndex = mActions.indexOfChild(focused);
        boolean inActions = actionIndex >= 0;

        switch (keyCode) {
            case KeyEvent.KEYCODE_DPAD_DOWN:
                if (focused == mTitle) {
                    return mChannel.requestFocus();
                }
                if (focused == mChannel) {
                    return mSubscribe.requestFocus();
                }
                if (focused == mSubscribe) {
                    return mActions.getChildCount() > 0 && mActions.getChildAt(0).requestFocus();
                }
                if (inActions) {
                    if (actionIndex + 1 < mActions.getChildCount()) {
                        return mActions.getChildAt(actionIndex + 1).requestFocus();
                    }
                    return true;
                }
                return false;

            case KeyEvent.KEYCODE_DPAD_UP:
                if (inActions) {
                    if (actionIndex > 0) {
                        return mActions.getChildAt(actionIndex - 1).requestFocus();
                    }
                    return mSubscribe.requestFocus();
                }
                if (focused == mSubscribe) {
                    return mChannel.requestFocus();
                }
                if (focused == mChannel) {
                    return mTitle.requestFocus();
                }
                return focused == mTitle;

            case KeyEvent.KEYCODE_DPAD_RIGHT:
                return true;
        }

        return false;
    }"""
    pattern = re.compile(r"    private boolean movePanelFocus\(int keyCode\) \{.*?\n    \}", re.S)
    source, count = pattern.subn(replacement, source, count=1)
    if count != 1:
        if replacement not in source:
            raise SystemExit(f"Shorts panel focus navigation: expected one method, found {count}")

    source = replace_once(
        source,
        "        params.rightMargin = getResources().getDimensionPixelSize(R.dimen.modern_player_group_gap) * 2;",
        "        params.bottomMargin = getResources().getDimensionPixelSize(R.dimen.modern_player_group_gap);"
        "\n        params.gravity = android.view.Gravity.CENTER_HORIZONTAL;",
        "Stack Shorts action buttons vertically"
    )
    return source

def shorts_layout(source):
    source = replace_once(
        source,
        '    android:visibility="gone">',
        '    android:visibility="gone"\n    android:layoutDirection="ltr">',
        "Keep Shorts video and side panel in a stable left-to-right TV layout"
    )
    source = replace_once(
        source,
        'android:layout_marginStart="@dimen/modern_shorts_panel_left"',
        'android:layout_marginLeft="@dimen/modern_shorts_panel_left"',
        "Place Shorts action panel to the right of the video"
    )
    source = replace_once(
        source,
        '            android:orientation="horizontal"\n            android:paddingStart="@dimen/modern_badge_padding_h"',
        '            android:orientation="vertical"\n            android:gravity="center_horizontal"\n            android:paddingStart="@dimen/modern_badge_padding_h"',
        "Show Shorts actions as a vertical side rail"
    )
    return source


def shorts_grid_interactions(source):
    # The dedicated Shorts grid is authoritative even when an API item omits
    # its isShorts flag. Preserve that state through focus and click handling.
    playback_import = "import com.liskovsoft.smartyoutubetv2.common.app.presenters.PlaybackPresenter;\n"
    if playback_import.strip() not in source:
        source = replace_once(
            source,
            "import com.liskovsoft.smartyoutubetv2.common.app.presenters.interfaces.VideoGroupPresenter;\n",
            "import com.liskovsoft.smartyoutubetv2.common.app.presenters.interfaces.VideoGroupPresenter;\n" + playback_import,
            "Import direct Shorts playback navigation"
        )

    if "private boolean mShortsSection;" not in source:
        source = replace_once(
            source,
            "    private boolean mChannelGrid;\n",
            "    private boolean mChannelGrid;\n    private boolean mShortsSection;\n",
            "Track whether this grid is the dedicated Shorts section"
        )

    if "mShortsSection = shorts;" not in source:
        source = replace_once(
            source,
            "    public void setShorts(boolean shorts) {\n        if (!shorts) {",
            "    public void setShorts(boolean shorts) {\n        mShortsSection = shorts;\n        if (!shorts) {",
            "Remember Shorts section mode"
        )

    if "if (mShortsSection && group.getVideos() != null)" not in source:
        source = replace_once(
            source,
            "    public void update(VideoGroup group) {\n        int action = group.getAction();",
            """    public void update(VideoGroup group) {
        if (mShortsSection && group.getVideos() != null) {
            for (Video video : group.getVideos()) {
                if (video != null) {
                    video.isShorts = true;
                }
            }
        }

        int action = group.getAction();""",
            "Mark every item loaded from the Shorts feed as a Short"
        )

    old_click = "                viewHolder.itemView.setOnClickListener(v -> mPresenter.onVideoItemClicked((Video) viewHolder.getItem()));"
    new_click = """                viewHolder.itemView.setOnClickListener(v -> {
                    Video video = (Video) viewHolder.getItem();
                    if (video != null && mShortsSection) {
                        video.isShorts = true;
                        // Shorts cards must always start playback, never be routed
                        // through channel/playlist heuristics.
                        PlaybackPresenter.instance(getContext()).openVideo(video);
                    } else {
                        mPresenter.onVideoItemClicked(video);
                    }
                });"""
    if old_click in source:
        source = replace_once(source, old_click, new_click, "Open Shorts cards directly in the Shorts player")
    elif new_click not in source:
        raise SystemExit("Shorts click handler not found")

    old_selected = "        mPresenter.onVideoItemSelected((Video) mAdapter.get(position));"
    new_selected = """        Video selected = (Video) mAdapter.get(position);
        if (selected != null && mShortsSection) {
            selected.isShorts = true;
        }
        mPresenter.onVideoItemSelected(selected);"""
    if old_selected in source:
        source = replace_once(source, old_selected, new_selected, "Keep the selected Shorts item marked for correct playback navigation")
    elif new_selected not in source:
        raise SystemExit("Shorts selected-item handler not found")

    return source

def shorts_overlay_interactions(source):
    if "mTitle.setOnClickListener" not in source:
        source = replace_once(
            source,
            "        mTime = findViewById(R.id.modern_shorts_time);\n",
            """        mTime = findViewById(R.id.modern_shorts_time);

        // The title opens the full video description.
        mTitle.setFocusable(true);
        mTitle.setFocusableInTouchMode(true);
        mTitle.setOnClickListener(v -> {
            if (mListener != null) {
                mListener.onShortsAction(R.id.action_info);
            }
        });
""",
            "Make Shorts title open the full description"
        )

    if "addAction(R.id.action_info, R.string.action_video_info);" not in source:
        source = replace_once(
            source,
            "        addAction(R.id.action_thumbs_down, R.string.action_dislike);\n",
            "        addAction(R.id.action_thumbs_down, R.string.action_dislike);\n"
            "        addAction(R.id.action_info, R.string.action_video_info);\n",
            "Add a dedicated Shorts description action"
        )

    old_right = """            case KeyEvent.KEYCODE_DPAD_RIGHT:
                mTitle.setFocusable(false);
                mChannel.requestFocus();
                return true;"""
    new_right = """            case KeyEvent.KEYCODE_DPAD_RIGHT:
                return mTitle.requestFocus();"""
    if old_right in source:
        source = replace_once(source, old_right, new_right, "Enter the Shorts details panel at its title")
    elif new_right not in source:
        raise SystemExit("Shorts video-to-panel focus link not found")

    return source

def shorts_dimensions(source):
    return replace_once(
        source,
        '<dimen name="modern_shorts_panel_top">279dp</dimen>',
        '<dimen name="modern_shorts_panel_top">70dp</dimen>',
        "Move the Shorts side rail up so the full vertical action stack fits"
    )


def shorts_layout_interactions(source):
    old = '            android:textStyle="bold" />'
    new = '            android:textStyle="bold"\n            android:focusable="true"\n            android:focusableInTouchMode="true"\n            android:clickable="true" />'
    if old in source:
        source = replace_once(source, old, new, "Make the Shorts title focusable and clickable")
    elif new not in source:
        raise SystemExit("Shorts title layout insertion point not found")
    return source

def playback_optimization(source):
    source = replace_once(
        source,
        "    private String mPosterVideoId;\n",
        "    private String mPosterVideoId;\n    private String mPrefetchedNextShortId;\n",
        "Track the next Shorts item already prefetched"
    )

    source = replace_once(
        source,
        """        if (index != -1 && index + 1 < videos.size()) {
            FormatInfoPrefetcher.instance().prefetch(videos.get(index + 1).videoId);
        }""",
        """        if (index != -1 && index + 1 < videos.size()) {
            String nextVideoId = videos.get(index + 1).videoId;
            if (nextVideoId != null && !nextVideoId.equals(mPrefetchedNextShortId)) {
                mPrefetchedNextShortId = nextVideoId;
                FormatInfoPrefetcher.instance().prefetch(nextVideoId);
            }
        }""",
        "Avoid duplicate next-Shorts format prefetch requests"
    )

    source = replace_once(
        source,
        "        Glide.with(mPoster).load(video.getCardImageUrl()).into(mPoster);",
        """        int posterWidth = getResources().getDimensionPixelSize(R.dimen.modern_shorts_video_width);
        int posterHeight = getResources().getDisplayMetrics().heightPixels;
        Glide.with(mPoster)
                .load(video.getCardImageUrl())
                .override(posterWidth, posterHeight)
                .dontAnimate()
                .into(mPoster);""",
        "Decode the Shorts poster at the actual display size and skip an unnecessary transition"
    )

    source = replace_once(
        source,
        "                params.gravity = Gravity.START | Gravity.TOP;",
        "                params.gravity = Gravity.LEFT | Gravity.TOP;",
        "Keep the Shorts video on the left in every locale"
    )

    source = replace_once(
        source,
        """        super.onViewCreated(view, savedInstanceState);
        view.getViewTreeObserver().addOnGlobalLayoutListener(mStyleProgress);""",
        """        super.onViewCreated(view, savedInstanceState);
        updateShortsMode(); // Also handle videos restored before the playback view was created.
        view.getViewTreeObserver().addOnGlobalLayoutListener(mStyleProgress);""",
        "Restore Shorts overlay when playback view is created"
    )
    return source



def card_image_optimization(source):
    source = replace_once(
        source,
        "import android.view.LayoutInflater;\n",
        "import android.view.LayoutInflater;\nimport android.view.View;\n",
        "Inspect the thumbnail container for its target size"
    )
    source = replace_once(
        source,
        ".diskCacheStrategy(VERSION.SDK_INT > 21 ? DiskCacheStrategy.ALL : DiskCacheStrategy.NONE)",
        ".diskCacheStrategy(VERSION.SDK_INT > 21 ? DiskCacheStrategy.RESOURCE : DiskCacheStrategy.NONE)",
        "Cache decoded card thumbnails without duplicating original and transformed files"
    )
    source = replace_once(
        source,
        """        if (card.getKind() == ModernVideoCard.KIND_PLAYLIST) {
            request = request.listener(new StackColorListener(card));
        }""",
        """        // Decode at the visible tile size instead of retaining an oversized source bitmap.
        View thumbContainer = (View) card.getThumbView().getParent();
        if (thumbContainer != null) {
            ViewGroup.LayoutParams thumbSize = thumbContainer.getLayoutParams();
            if (thumbSize != null && thumbSize.width > 0 && thumbSize.height > 0) {
                request = request.override(thumbSize.width, thumbSize.height);
            }
        }

        if (card.getKind() == ModernVideoCard.KIND_PLAYLIST) {
            request = request.listener(new StackColorListener(card));
        }""",
        "Downsample every home, shelf and player-suggestion thumbnail to its rendered size"
    )
    return source

def modern_shorts_glue(source):
    leanback_import = "import androidx.leanback.widget.PlaybackControlsRow;\n"
    if leanback_import.strip() not in source:
        source = replace_once(
            source,
            "import androidx.leanback.widget.PlaybackRowPresenter;\n",
            leanback_import + "import androidx.leanback.widget.PlaybackRowPresenter;\n",
            "Import the player action container type"
        )

    import_marker = "import com.liskovsoft.smartyoutubetv2.tv.ui.playback.other.VideoPlayerGlue;\n"
    imports = (
        "import com.liskovsoft.smartyoutubetv2.tv.ui.playback.actions.ChatAction;\n"
        "import com.liskovsoft.smartyoutubetv2.tv.ui.playback.actions.SubscribeAction;\n"
        "import com.liskovsoft.smartyoutubetv2.tv.ui.playback.actions.ThumbsDownAction;\n"
        "import com.liskovsoft.smartyoutubetv2.tv.ui.playback.actions.ThumbsUpAction;\n"
        "import com.liskovsoft.smartyoutubetv2.tv.ui.playback.actions.VideoInfoAction;\n"
    )
    if "import com.liskovsoft.smartyoutubetv2.tv.ui.playback.actions.ThumbsUpAction;" not in source:
        source = replace_once(source, import_marker, imports + import_marker, "Import the built-in Shorts actions")

    old = """    public boolean performAction(int actionId) {
        Action action = findAction(actionId);

        if (action == null) {
            return false;
        }

        onActionClicked(action);
        return true;
    }"""
    new = """    public boolean performAction(int actionId) {
        Action action = findAction(actionId);

        // Shorts always expose social and details actions, even when the user
        // has hidden the corresponding buttons from the normal player row.
        if (action == null) {
            action = createShortsAction(actionId);
        }

        if (action == null) {
            return false;
        }

        if (action instanceof PlaybackControlsRow.MultiAction) {
            ((PlaybackControlsRow.MultiAction) action).setIndex(getButtonState(actionId));
        }

        onActionClicked(action);
        return true;
    }

    private Action createShortsAction(int actionId) {
        switch (actionId) {
            case R.id.action_thumbs_up:
                return new ThumbsUpAction(getContext());
            case R.id.action_thumbs_down:
                return new ThumbsDownAction(getContext());
            case R.id.action_chat:
                return new ChatAction(getContext());
            case R.id.action_info:
                return new VideoInfoAction(getContext());
            case R.id.action_subscribe:
                return new SubscribeAction(getContext());
        }

        return null;
    }"""
    if old in source:
        source = replace_once(source, old, new, "Make Shorts actions work independently of normal player-button visibility")
    elif "private Action createShortsAction(int actionId)" not in source:
        raise SystemExit("Modern player action insertion point not found")

    old_active = """    public boolean isActionActive(int actionId) {
        Action action = findAction(actionId);
        return action != null && ModernControlButtonPresenterSelector.isActive(action);
    }"""
    new_active = """    public boolean isActionActive(int actionId) {
        Action action = findAction(actionId);
        if (action == null) {
            action = createShortsAction(actionId);
            if (action instanceof PlaybackControlsRow.MultiAction) {
                ((PlaybackControlsRow.MultiAction) action).setIndex(getButtonState(actionId));
            }
        }
        return action != null && ModernControlButtonPresenterSelector.isActive(action);
    }"""
    if old_active in source:
        source = replace_once(source, old_active, new_active, "Read Shorts action state even when the normal player button is hidden")
    elif "action = createShortsAction(actionId);" not in source[source.find("public boolean isActionActive"):source.find("private Action createShortsAction")]:
        raise SystemExit("Modern player action-state insertion point not found")

    return source


def shorts_channel_navigation(source):
    import_line = "import com.liskovsoft.smartyoutubetv2.common.app.presenters.dialogs.menu.VideoMenuPresenter;\n"
    if "import com.liskovsoft.smartyoutubetv2.common.app.presenters.ChannelPresenter;" not in source:
        source = replace_once(
            source,
            import_line,
            "import com.liskovsoft.smartyoutubetv2.common.app.presenters.ChannelPresenter;\n" + import_line,
            "Import the channel presenter for the Shorts author link"
        )

    old = """            public void onShortsAction(int actionId) {
                if (mGlue != null) {
                    mGlue.performAction(actionId);
                }
            }"""
    new = """            public void onShortsAction(int actionId) {
                if (actionId == R.id.action_channel) {
                    if (mVideo != null && ChannelPresenter.canOpenChannel(mVideo)) {
                        ChannelPresenter.instance(getContext()).openChannel(mVideo);
                    }
                    return;
                }

                if (mGlue != null) {
                    mGlue.performAction(actionId);
                }
            }"""
    if old in source:
        source = replace_once(source, old, new, "Open the Shorts author channel directly")
    elif "ChannelPresenter.instance(getContext()).openChannel(mVideo);" not in source:
        raise SystemExit("Shorts author click handler not found")

    return source


edit(
    "common/src/main/java/com/liskovsoft/smartyoutubetv2/common/app/presenters/BrowsePresenter.java",
    sidebar
)
edit(
    "smarttubetv/src/main/java/com/liskovsoft/smartyoutubetv2/tv/ui/main/MainApplication.java",
    enable_modern_player
)
edit(
    "common/src/main/java/com/liskovsoft/smartyoutubetv2/common/app/presenters/settings/MainUISettingsPresenter.java",
    lock_modern_interface_setting
)
edit(
    "smarttubetv/src/main/java/com/liskovsoft/smartyoutubetv2/tv/ui/modern/playback/ModernShortsOverlay.java",
    shorts_overlay
)
edit(
    "smarttubetv/src/main/java/com/liskovsoft/smartyoutubetv2/tv/ui/modern/playback/ModernShortsOverlay.java",
    shorts_overlay_interactions
)
edit(
    "smarttubetv/src/main/res/layout/modern_shorts_overlay.xml",
    shorts_layout_interactions
)
edit(
    "smarttubetv/src/main/java/com/liskovsoft/smartyoutubetv2/tv/ui/modern/browse/ModernGridView.java",
    shorts_grid_interactions
)
edit(
    "smarttubetv/src/main/res/layout/modern_shorts_overlay.xml",
    shorts_layout
)
edit(
    "smarttubetv/src/main/res/values/modern_dimens.xml",
    shorts_dimensions
)
edit(
    "smarttubetv/src/main/java/com/liskovsoft/smartyoutubetv2/tv/ui/modern/playback/ModernPlaybackFragment.java",
    playback_optimization
)
edit(
    "smarttubetv/src/main/java/com/liskovsoft/smartyoutubetv2/tv/ui/modern/playback/ModernPlaybackFragment.java",
    shorts_channel_navigation
)
edit(
    "smarttubetv/src/main/java/com/liskovsoft/smartyoutubetv2/tv/ui/modern/playback/ModernVideoPlayerGlue.java",
    modern_shorts_glue
)
edit(
    "smarttubetv/src/main/java/com/liskovsoft/smartyoutubetv2/tv/ui/modern/widgets/ModernCardPresenter.java",
    card_image_optimization
)

print("Modern YouTube TV pass applied: modern player routing, vertical Shorts side rail and D-pad navigation, plus app-wide thumbnail and playback optimizations.")
def rail_compact(source):
    source = replace_once(
        source,
        '<dimen name="modern_rail_item_height">39dp</dimen>',
        '<dimen name="modern_rail_item_height">33dp</dimen>',
        "Make navigation rail items more compact"
    )
    return replace_once(
        source,
        '<dimen name="modern_rail_divider_margin">9dp</dimen>',
        '<dimen name="modern_rail_divider_margin">5dp</dimen>',
        "Reduce space around rail dividers"
    )


edit(
    "smarttubetv/src/main/res/values/modern_dimens.xml",
    rail_compact
)

def rail_keys(source):
    old = "int index = mItems.indexOf(v);"
    new = (
        "int index = mItems.indexOf(v);\n"
        "\n"
        "            if (keyCode == KeyEvent.KEYCODE_DPAD_UP || keyCode == KeyEvent.KEYCODE_DPAD_DOWN) {\n"
        "                int step = keyCode == KeyEvent.KEYCODE_DPAD_UP ? -1 : 1;\n"
        "\n"
        "                for (int i = index + step; i >= 0 && i < mItems.size(); i += step) {\n"
        "                    View next = mItems.get(i);\n"
        "\n"
        "                    if (next.getVisibility() == View.VISIBLE) {\n"
        "                        next.requestFocus();\n"
        "                        break;\n"
        "                    }\n"
        "                }\n"
        "\n"
        "                return true;\n"
        "            }"
    )
    return replace_once(source, old, new, "Move rail focus strictly between rail items")


edit(
    "smarttubetv/src/main/java/com/liskovsoft/smartyoutubetv2/tv/ui/modern/widgets/ModernNavRail.java",
    rail_keys
)

def vless_tuning(source):
    source = replace_once(
        source,
        "JSONArray inbounds = new JSONArray().put(inbound);",
        "// DNS for resolving the VLESS server address: DoH, direct, IPv4 only.\n"
        "        JSONObject dns = new JSONObject()\n"
        "                .put(\"servers\", new JSONArray()\n"
        "                        .put(\"https+local://1.1.1.1/dns-query\")\n"
        "                        .put(\"https+local://8.8.8.8/dns-query\")\n"
        "                        .put(\"localhost\"))\n"
        "                .put(\"queryStrategy\", \"UseIPv4\");\n"
        "        // Larger per-connection buffer for video streaming.\n"
        "        JSONObject policy = new JSONObject().put(\"levels\", new JSONObject()\n"
        "                .put(\"0\", new JSONObject().put(\"bufferSize\", 512)));\n"
        "        JSONArray inbounds = new JSONArray().put(inbound);",
        "Add DNS and buffer tuning to the Xray config"
    )
    return replace_once(
        source,
        ".put(\"inbounds\", inbounds).put(\"outbounds\", outbounds).put(\"routing\", routing);",
        ".put(\"inbounds\", inbounds).put(\"outbounds\", outbounds).put(\"routing\", routing)\n"
        "                .put(\"dns\", dns).put(\"policy\", policy);",
        "Attach DNS and policy to the Xray config"
    )


edit(
    "common/src/main/java/com/liskovsoft/smartyoutubetv2/common/proxy/vless/VlessConfigBuilder.java",
    vless_tuning
)

def build_byedpi():
    import os
    import shutil
    import subprocess

    ndk = (os.environ.get("ANDROID_NDK_LATEST_HOME")
           or os.environ.get("ANDROID_NDK_ROOT")
           or os.environ.get("ANDROID_NDK_HOME"))
    if not ndk:
        raise SystemExit("Android NDK was not found on the runner")

    bin_dir = Path(ndk) / "toolchains" / "llvm" / "prebuilt" / "linux-x86_64" / "bin"
    work = ROOT / ".work" / "byedpi"
    if work.exists():
        shutil.rmtree(work)
    work.parent.mkdir(parents=True, exist_ok=True)

    subprocess.run(["git", "clone", "--depth", "1",
                    "https://github.com/hufrea/byedpi.git", str(work)], check=True)
    revision = subprocess.run(["git", "-C", str(work), "rev-parse", "HEAD"],
                              check=True, capture_output=True, text=True).stdout.strip()
    print("ByeDPI revision: " + revision)

    targets = {
        "arm64-v8a": "aarch64-linux-android24-clang",
        "armeabi-v7a": "armv7a-linux-androideabi24-clang",
    }

    for abi, compiler in targets.items():
        cc = bin_dir / compiler
        if not cc.is_file():
            raise SystemExit("NDK compiler not found: " + str(cc))

        for old in list(work.glob("*.o")) + [work / "ciadpi"]:
            if old.exists():
                old.unlink()

        subprocess.run(["make", "-C", str(work), "CC=" + str(cc)], check=True)

        out_dir = ROOT / "smarttubetv" / "src" / "main" / "jniLibs" / abi
        out_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(work / "ciadpi", out_dir / "libbyedpi.so")
        print("ByeDPI built for " + abi)


build_byedpi()

def vless_ui_tweaks(source):
    for name in ("startVless", "stopVless"):
        sig = "    private void " + name + "(XrayVlessManager manager, AppDialogPresenter settingsPresenter) {\n"
        source = replace_once(
            source,
            sig + "        settingsPresenter.closeDialog();\n",
            sig,
            "Keep settings open after " + name
        )

    source = replace_once(
        source,
        'settingsPresenter.appendSingleButton(UiOptionItem.from("Remove saved VLESS profile", option -> {',
        'settingsPresenter.appendSingleButton(UiOptionItem.from("Check VLESS ping", option -> testVlessPing()));\n'
        '            settingsPresenter.appendSingleButton(UiOptionItem.from("Remove saved VLESS profile", option -> {',
        "Add VLESS ping button"
    )

    ping_method = '''    private void testVlessPing() {
        new Thread(() -> {
            String result;
            try {
                java.net.Proxy socks = new java.net.Proxy(java.net.Proxy.Type.SOCKS,
                        new java.net.InetSocketAddress("127.0.0.1", 10808));
                long started = System.currentTimeMillis();
                java.net.HttpURLConnection connection = (java.net.HttpURLConnection)
                        new java.net.URL("https://www.google.com/generate_204").openConnection(socks);
                connection.setConnectTimeout(8000);
                connection.setReadTimeout(8000);
                int code = connection.getResponseCode();
                connection.disconnect();
                result = "VLESS ping: " + (System.currentTimeMillis() - started) + " ms (HTTP " + code + ")";
            } catch (Exception e) {
                result = "VLESS ping failed. Start VLESS first.";
            }
            final String message = result;
            new Handler(Looper.getMainLooper()).post(() -> MessageHelpers.showMessage(getContext(), message));
        }, "smarttube-vless-ping").start();
    }

'''
    start_line = "    private void startVless(XrayVlessManager manager, AppDialogPresenter settingsPresenter) {\n"
    return replace_once(source, start_line, ping_method + start_line, "Add VLESS ping check")


edit(
    "common/src/main/java/com/liskovsoft/smartyoutubetv2/common/app/presenters/settings/GeneralSettingsPresenter.java",
    vless_ui_tweaks
)

BYEDPI_JAVA = r'''package com.liskovsoft.smartyoutubetv2.common.proxy.byedpi;

import android.content.Context;
import android.content.SharedPreferences;

import java.io.File;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;

/** Runs the bundled ByeDPI binary as a local SOCKS5 proxy on 127.0.0.1:1080. */
public final class ByeDpiManager {
    public static final int PORT = 1080;
    public static final String DEFAULT_STRATEGY = "-d1 -s1+s -s3+s -s6+s -s9+s -s12+s -s15+s -s20+s -s30+s -a1";
    private static final String PREFS = "byedpi_private";
    private static ByeDpiManager instance;
    private final Context context;
    private final SharedPreferences prefs;
    private Process process;

    private ByeDpiManager(Context context) {
        this.context = context.getApplicationContext();
        prefs = this.context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    public static synchronized ByeDpiManager instance(Context context) {
        if (instance == null) instance = new ByeDpiManager(context);
        return instance;
    }

    public boolean isEnabled() {
        return prefs.getBoolean("enabled", false);
    }

    public void setEnabled(boolean enabled) {
        prefs.edit().putBoolean("enabled", enabled).apply();
    }

    public String getStrategy() {
        return prefs.getString("strategy", DEFAULT_STRATEGY);
    }

    public synchronized boolean isRunning() {
        if (process == null) return false;
        try {
            process.exitValue();
            process = null;
            return false;
        } catch (IllegalThreadStateException running) {
            return true;
        }
    }

    /** Never throws: returns false if the binary is missing or fails to start. */
    public synchronized boolean start() {
        if (isRunning()) return true;
        try {
            File binary = new File(context.getApplicationInfo().nativeLibraryDir, "libbyedpi.so");
            if (!binary.isFile()) return false;
            List<String> command = new ArrayList<>();
            command.add(binary.getAbsolutePath());
            command.add("-i");
            command.add("127.0.0.1");
            command.add("-p");
            command.add(String.valueOf(PORT));
            for (String part : getStrategy().trim().split("\\s+")) {
                if (!part.isEmpty()) command.add(part);
            }
            ProcessBuilder builder = new ProcessBuilder(command);
            builder.redirectErrorStream(true);
            process = builder.start();
            final InputStream output = process.getInputStream();
            Thread drain = new Thread(() -> {
                byte[] buffer = new byte[1024];
                try {
                    while (output.read(buffer) >= 0) { }
                } catch (Exception ignored) { }
            }, "smarttube-byedpi-log");
            drain.setDaemon(true);
            drain.start();
            Thread.sleep(300);
            return isRunning();
        } catch (Exception e) {
            process = null;
            return false;
        }
    }

    public synchronized void stop() {
        if (process != null) {
            process.destroy();
            process = null;
        }
    }
}
'''

ROUTING_ADDON = r'''.put("outboundTag", "secure-proxy")));
        if (byeDpiEnabled) {
            outbounds.put(new JSONObject().put("protocol", "socks").put("tag", "byedpi")
                    .put("settings", new JSONObject().put("servers", new JSONArray()
                            .put(new JSONObject().put("address", "127.0.0.1").put("port", 1080)))));
            JSONArray oldRules = routing.getJSONArray("rules");
            JSONArray newRules = new JSONArray();
            newRules.put(new JSONObject().put("type", "field")
                    .put("domain", new JSONArray().put("regexp:^rr[0-9]+---sn-q4fl.*\\.googlevideo\\.com$"))
                    .put("outboundTag", "secure-proxy"));
            newRules.put(new JSONObject().put("type", "field")
                    .put("domain", new JSONArray().put("domain:googlevideo.com")
                            .put("full:youtubei.googleapis.com").put("full:jnn-pa.googleapis.com"))
                    .put("outboundTag", "byedpi"));
            for (int i = 0; i < oldRules.length(); i++) newRules.put(oldRules.get(i));
            routing.put("rules", newRules);
        }'''

BYEDPI_BUTTON = r'''settingsPresenter.appendSingleButton(UiOptionItem.from("Check VLESS ping", option -> testVlessPing()));
            settingsPresenter.appendSingleButton(UiOptionItem.from("ByeDPI for video: toggle", option -> {
                ByeDpiManager byeDpi = ByeDpiManager.instance(getContext());
                byeDpi.setEnabled(!byeDpi.isEnabled());
                MessageHelpers.showMessage(getContext(), "ByeDPI for video: " + (byeDpi.isEnabled() ? "ON" : "OFF") + ". Stop and start VLESS to apply.");
            }));'''


def byedpi_manager_file():
    folder = ROOT / "common" / "src" / "main" / "java" / "com" / "liskovsoft" / "smartyoutubetv2" / "common" / "proxy" / "byedpi"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "ByeDpiManager.java").write_text(BYEDPI_JAVA, encoding="utf-8")
    print("Created ByeDpiManager.java")


def byedpi_in_builder(source):
    source = replace_once(
        source,
        "private VlessConfigBuilder() { }",
        "private VlessConfigBuilder() { }\n    public static volatile boolean byeDpiEnabled = false;",
        "Add ByeDPI flag"
    )
    return replace_once(
        source,
        '.put("outboundTag", "secure-proxy")));',
        ROUTING_ADDON,
        "Route YouTube video through ByeDPI"
    )


def byedpi_in_manager(source):
    source = replace_once(
        source,
        "import com.liskovsoft.smartyoutubetv2.common.proxy.ProxyManager;",
        "import com.liskovsoft.smartyoutubetv2.common.proxy.ProxyManager;\nimport com.liskovsoft.smartyoutubetv2.common.proxy.byedpi.ByeDpiManager;",
        "Import ByeDPI manager"
    )
    source = replace_once(
        source,
        "JSONObject config = VlessConfigBuilder.buildXrayConfig(link);",
        "ByeDpiManager byeDpi = ByeDpiManager.instance(context);\n"
        "            VlessConfigBuilder.byeDpiEnabled = byeDpi.isEnabled() && byeDpi.start();\n"
        "            JSONObject config = VlessConfigBuilder.buildXrayConfig(link);",
        "Start ByeDPI before Xray"
    )
    return replace_once(
        source,
        "if (failure != null) throw failure;",
        "ByeDpiManager.instance(context).stop();\n"
        "        VlessConfigBuilder.byeDpiEnabled = false;\n"
        "        if (failure != null) throw failure;",
        "Stop ByeDPI together with VLESS"
    )


def byedpi_ui(source):
    source = replace_once(
        source,
        "import com.liskovsoft.smartyoutubetv2.common.proxy.vless.VlessConfigBuilder;",
        "import com.liskovsoft.smartyoutubetv2.common.proxy.byedpi.ByeDpiManager;\n"
        "import com.liskovsoft.smartyoutubetv2.common.proxy.vless.VlessConfigBuilder;",
        "Import ByeDPI manager"
    )
    source = replace_once(
        source,
        'settingsPresenter.appendSingleButton(UiOptionItem.from("Check VLESS ping", option -> testVlessPing()));',
        BYEDPI_BUTTON,
        "Add ByeDPI toggle button"
    )
    source = replace_once(
        source,
        'result = "VLESS ping failed. Start VLESS first.";',
        'result = XrayVlessManager.instance(getContext()).isStarted()\n'
        '                        ? "VLESS ping failed: server unreachable or key not working"\n'
        '                        : "VLESS ping failed. Start VLESS first.";',
        "Clearer ping error"
    )
    return replace_once(
        source,
        '"VLESS started. Only SmartTube requests that honor the app proxy are routed; this is not a device-wide VPN."',
        '"VLESS started. ByeDPI: " + (ByeDpiManager.instance(getContext()).isRunning() ? "running" : "off")',
        "Show ByeDPI status after start"
    )


byedpi_manager_file()
edit(
    "common/src/main/java/com/liskovsoft/smartyoutubetv2/common/proxy/vless/VlessConfigBuilder.java",
    byedpi_in_builder
)
edit(
    "common/src/main/java/com/liskovsoft/smartyoutubetv2/common/proxy/vless/XrayVlessManager.java",
    byedpi_in_manager
)
edit(
    "common/src/main/java/com/liskovsoft/smartyoutubetv2/common/app/presenters/settings/GeneralSettingsPresenter.java",
    byedpi_ui
)

def vless_pin(source):
    return replace_once(
        source,
        'tls.put("allowInsecure", false);',
        'tls.put("allowInsecure", false);\n'
        '                java.util.regex.Matcher pin = java.util.regex.Pattern.compile("[?&]pcs=([^&#]+)").matcher(shareUri);\n'
        '                if (pin.find()) {\n'
        '                    String hex = decode(pin.group(1)).replace(":", "").toLowerCase(Locale.ROOT);\n'
        '                    tls.put("pinnedPeerCertSha256", new JSONArray().put(hex));\n'
        '                }',
        "Support pinned certificate in VLESS links"
    )


edit(
    "common/src/main/java/com/liskovsoft/smartyoutubetv2/common/proxy/vless/VlessConfigBuilder.java",
    vless_pin
)

def vless_pin_fix(source):
    source = replace_once(
        source,
        'String hex = decode(pin.group(1)).replace(":", "").toLowerCase(Locale.ROOT);',
        'String hex = decode(pin.group(1)).toUpperCase(Locale.ROOT);',
        "Keep pinned certificate format as in the provider config"
    )
    return replace_once(
        source,
        'tls.put("pinnedPeerCertSha256", new JSONArray().put(hex));',
        'tls.put("pinnedPeerCertSha256", hex);',
        "Pinned certificate as a string"
    )


edit(
    "common/src/main/java/com/liskovsoft/smartyoutubetv2/common/proxy/vless/VlessConfigBuilder.java",
    vless_pin_fix
)

KEY_LIST_JAVA = r'''package com.liskovsoft.smartyoutubetv2.common.proxy.vless;

import android.content.Context;
import android.content.SharedPreferences;

import java.util.ArrayList;
import java.util.List;

/** Several VLESS links kept in app-private preferences. Never logged. */
public final class VlessKeyList {
    private static final String PREFS = "vless_keys_private";
    private static final String KEY = "keys";
    private final SharedPreferences preferences;

    public VlessKeyList(Context context) {
        preferences = context.getApplicationContext().getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    public List<String> getAll() {
        List<String> result = new ArrayList<>();
        for (String line : preferences.getString(KEY, "").split("\n")) {
            String value = line.trim();
            if (!value.isEmpty() && !result.contains(value)) result.add(value);
        }
        return result;
    }

    public void add(String link) {
        List<String> all = getAll();
        String value = link == null ? "" : link.trim();
        if (value.isEmpty() || all.contains(value)) return;
        all.add(value);
        StringBuilder joined = new StringBuilder();
        for (String item : all) joined.append(item).append('\n');
        preferences.edit().putString(KEY, joined.toString()).apply();
    }
}
'''

ROUTE_STORE_JAVA = r'''package com.liskovsoft.smartyoutubetv2.common.proxy.vless;

import android.content.Context;
import android.content.SharedPreferences;

import java.util.ArrayList;
import java.util.List;

/** Domains that pass through ByeDPI and are therefore routed to it. */
public final class RouteStore {
    private static final String PREFS = "byedpi_routes_private";
    private static final String KEY = "domains";
    private final SharedPreferences preferences;

    public RouteStore(Context context) {
        preferences = context.getApplicationContext().getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    public List<String> getDomains() {
        List<String> result = new ArrayList<>();
        for (String line : preferences.getString(KEY, "").split("\n")) {
            String value = line.trim();
            if (!value.isEmpty()) result.add(value);
        }
        return result;
    }

    public void saveDomains(List<String> domains) {
        StringBuilder joined = new StringBuilder();
        for (String domain : domains) joined.append(domain).append('\n');
        preferences.edit().putString(KEY, joined.toString()).apply();
    }
}
'''

TUNER_JAVA = r'''package com.liskovsoft.smartyoutubetv2.common.proxy.vless;

import android.content.Context;

import com.liskovsoft.smartyoutubetv2.common.proxy.byedpi.ByeDpiManager;

import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.net.URL;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

import javax.net.ssl.SSLSocket;
import javax.net.ssl.SSLSocketFactory;

/** Picks the fastest saved VLESS key and builds per-domain ByeDPI routes. Blocking: call from a thread. */
public final class NetworkAutoTuner {
    public interface Callback {
        void onStatus(String text);
    }

    private static final int VLESS_PORT = 10808;

    private static final String[] TEST_HOSTS = {
            "rr2---sn-hgn7ynek.googlevideo.com", "rr1---sn-gvnuxaxjvh-5gie.googlevideo.com",
            "rr1---sn-4axm-n8vs.googlevideo.com", "rr12---sn-gvnuxaxjvh-bvwz.googlevideo.com",
            "rr1---sn-u5uuxaxjvhg0-ocje.googlevideo.com", "rr1---sn-xguxaxjvh-gufl.googlevideo.com",
            "rr1---sn-gvnuxaxjvh-o8ge.googlevideo.com", "rr1---sn-ug5onuxaxjvh-n8v6.googlevideo.com",
            "rr14---sn-n8v7kn7r.googlevideo.com", "rr1---sn-8ph2xajvh-5xge.googlevideo.com",
            "rr1---sn-ug5onuxaxjvh-p3ul.googlevideo.com", "rr16---sn-axq7sn76.googlevideo.com",
            "rr5---sn-n8v7knez.googlevideo.com", "rr10---sn-gvnuxaxjvh-304z.googlevideo.com",
            "rr4---sn-jvhnu5g-c35d.googlevideo.com", "jnn-pa.googleapis.com",
            "youtubei.googleapis.com", "manifest.googlevideo.com",
            "rr5---sn-gvnuxaxjvh-n8vk.googlevideo.com", "rr1---sn-q4fl6n6y.googlevideo.com",
            "youtu.be", "i.ytimg.com", "youtube.com", "rr2---sn-q4fl6ndl.googlevideo.com",
            "rr4---sn-q4flrnsl.googlevideo.com", "yt3.ggpht.com", "i9.ytimg.com",
            "yt3.googleusercontent.com", "googleusercontent.com", "yt4.ggpht.com",
            "signaler-pa.youtube.com", "googleapis.com"
    };

    private static final String[] STRATEGIES = {
            "-d1 -s1+s -s3+s -s6+s -s9+s -s12+s -s15+s -s20+s -s30+s -a1",
            "--disorder 1 --auto=torst --tlsrec 1+s",
            "--disorder 1",
            "--fake -1 --ttl 8",
            "--split 1+s --disorder 3+s",
            "--disorder 1 --tlsrec 3+s",
            "--oob 3+s",
            "--tlsrec 3+s",
            "--split 2 --tlsrec 3+s",
            "--fake -1 --ttl 8 --tlsrec 3+s",
            "--disorder 1 --fake -1 --ttl 8",
            "-Y --disorder 1 --tlsrec 1+s",
            "--oob 1+s --tlsrec 1+s",
            "--split 1+s --oob 3+s"
    };

    private NetworkAutoTuner() { }

    public static String tuneKeys(Context context, Callback callback) throws Exception {
        VlessKeyList list = new VlessKeyList(context);
        VlessProfileStore store = new VlessProfileStore(context);
        XrayVlessManager manager = XrayVlessManager.instance(context);
        ByeDpiManager byeDpi = ByeDpiManager.instance(context);

        List<String> keys = list.getAll();
        String original = store.getShareUri();
        if (!original.isEmpty() && !keys.contains(original)) keys.add(0, original);
        if (keys.isEmpty()) return "No VLESS keys saved";

        boolean wasStarted = manager.isStarted();
        boolean byeDpiWasEnabled = byeDpi.isEnabled();
        byeDpi.setEnabled(false);
        if (wasStarted) {
            try { manager.stop(); } catch (Exception ignored) { }
        }

        java.net.Proxy socks = new java.net.Proxy(java.net.Proxy.Type.SOCKS, new InetSocketAddress("127.0.0.1", VLESS_PORT));
        String bestKey = null;
        double bestScore = -1e9;
        int bestIndex = -1;
        StringBuilder report = new StringBuilder();

        for (int i = 0; i < keys.size(); i++) {
            String key = keys.get(i);
            String label = "Key " + (i + 1) + "/" + keys.size();
            callback.onStatus(label + ": testing...");
            try {
                VlessConfigBuilder.buildXrayConfig(key);
                store.saveShareUri(key);
                manager.start();
                Thread.sleep(500);

                long ping = medianPing(socks);
                boolean youtubeOk = requestOk("https://www.youtube.com/generate_204", socks);
                double speed = youtubeOk ? downloadMbps(socks) : 0;
                double score = (youtubeOk ? 0 : -1000) + speed - ping / 1000.0;
                report.append(label).append(": ").append(ping).append(" ms, ")
                        .append(String.format(Locale.US, "%.1f", speed)).append(" Mbit/s")
                        .append(youtubeOk ? "" : ", YouTube FAIL").append("; ");
                if (score > bestScore) {
                    bestScore = score;
                    bestKey = key;
                    bestIndex = i + 1;
                }
            } catch (Exception e) {
                report.append(label).append(": failed; ");
            } finally {
                try { manager.stop(); } catch (Exception ignored) { }
            }
        }

        byeDpi.setEnabled(byeDpiWasEnabled);
        String finalKey = bestKey != null ? bestKey : original;
        if (!finalKey.isEmpty()) store.saveShareUri(finalKey);
        if (wasStarted) {
            try { manager.start(); } catch (Exception ignored) { }
        }
        return (bestKey != null ? "Best: key " + bestIndex + ". " : "No working key. ") + report;
    }

    public static String tuneStrategies(Context context, Callback callback) {
        ByeDpiManager byeDpi = ByeDpiManager.instance(context);
        XrayVlessManager manager = XrayVlessManager.instance(context);
        boolean vlessWasStarted = manager.isStarted();

        String previous = byeDpi.getStrategy();
        List<String> candidates = new ArrayList<>();
        candidates.add(previous);
        for (String strategy : STRATEGIES) {
            if (!candidates.contains(strategy)) candidates.add(strategy);
        }

        byeDpi.stop();
        pause(200);
        String best = previous;
        int bestPass = -1;

        for (int i = 0; i < candidates.size(); i++) {
            String strategy = candidates.get(i);
            callback.onStatus("Strategy " + (i + 1) + "/" + candidates.size() + ": testing...");
            byeDpi.setStrategy(strategy);
            byeDpi.stop();
            pause(200);
            int pass = 0;
            if (byeDpi.start()) {
                pass = passing(ByeDpiManager.PORT).size();
            }
            byeDpi.stop();
            if (pass > bestPass) {
                bestPass = pass;
                best = strategy;
            }
        }

        callback.onStatus("Building routes for the best strategy...");
        byeDpi.setStrategy(best);
        byeDpi.stop();
        pause(200);
        List<String> viaByeDpi = new ArrayList<>();
        if (byeDpi.start()) {
            viaByeDpi = passing(ByeDpiManager.PORT);
        }
        byeDpi.stop();
        new RouteStore(context).saveDomains(viaByeDpi);
        byeDpi.setEnabled(!viaByeDpi.isEmpty());

        String vlessPart = "VLESS was not running, start it and repeat to see the combined result";
        if (vlessWasStarted) {
            List<String> viaVless = passing(VLESS_PORT);
            int combined = viaByeDpi.size();
            for (String host : viaVless) {
                if (!viaByeDpi.contains(host)) combined++;
            }
            vlessPart = "VLESS " + viaVless.size() + "/" + TEST_HOSTS.length + ", combined " + combined + "/" + TEST_HOSTS.length;
            try {
                manager.stop();
                manager.start();
            } catch (Exception ignored) { }
        }
        return "ByeDPI " + viaByeDpi.size() + "/" + TEST_HOSTS.length + " (" + best + "); " + vlessPart;
    }

    private static void pause(long ms) {
        try { Thread.sleep(ms); } catch (InterruptedException ignored) { }
    }

    private static long medianPing(java.net.Proxy proxy) throws Exception {
        long[] times = new long[3];
        for (int i = 0; i < times.length; i++) {
            long started = System.currentTimeMillis();
            HttpURLConnection connection = (HttpURLConnection) new URL("https://www.google.com/generate_204").openConnection(proxy);
            connection.setConnectTimeout(8000);
            connection.setReadTimeout(8000);
            connection.getResponseCode();
            connection.disconnect();
            times[i] = System.currentTimeMillis() - started;
        }
        Arrays.sort(times);
        return times[1];
    }

    private static boolean requestOk(String url, java.net.Proxy proxy) {
        try {
            HttpURLConnection connection = (HttpURLConnection) new URL(url).openConnection(proxy);
            connection.setConnectTimeout(8000);
            connection.setReadTimeout(8000);
            int code = connection.getResponseCode();
            connection.disconnect();
            return code == 204 || code == 200;
        } catch (Exception e) {
            return false;
        }
    }

    private static double downloadMbps(java.net.Proxy proxy) {
        try {
            long started = System.currentTimeMillis();
            HttpURLConnection connection = (HttpURLConnection) new URL("https://speed.cloudflare.com/__down?bytes=4000000").openConnection(proxy);
            connection.setConnectTimeout(8000);
            connection.setReadTimeout(8000);
            InputStream input = connection.getInputStream();
            byte[] buffer = new byte[16384];
            long total = 0;
            int read;
            while ((read = input.read(buffer)) >= 0) {
                total += read;
                if (System.currentTimeMillis() - started > 8000) break;
            }
            input.close();
            connection.disconnect();
            long elapsed = Math.max(1, System.currentTimeMillis() - started);
            return total * 8.0 / (elapsed * 1000.0);
        } catch (Exception e) {
            return 0;
        }
    }

    private static List<String> passing(final int port) {
        ExecutorService pool = Executors.newFixedThreadPool(8);
        List<Future<Boolean>> futures = new ArrayList<>();
        for (final String host : TEST_HOSTS) {
            futures.add(pool.submit(new Callable<Boolean>() {
                @Override
                public Boolean call() {
                    return hostOk(host, port);
                }
            }));
        }
        List<String> result = new ArrayList<>();
        for (int i = 0; i < futures.size(); i++) {
            try {
                if (futures.get(i).get(9, TimeUnit.SECONDS)) result.add(TEST_HOSTS[i]);
            } catch (Exception ignored) { }
        }
        pool.shutdownNow();
        return result;
    }

    private static boolean hostOk(String host, int port) {
        Socket tunnel = null;
        try {
            java.net.Proxy socks = new java.net.Proxy(java.net.Proxy.Type.SOCKS,
                    new InetSocketAddress("127.0.0.1", port));
            tunnel = new Socket(socks);
            tunnel.connect(InetSocketAddress.createUnresolved(host, 443), 4000);
            tunnel.setSoTimeout(4000);
            SSLSocket ssl = (SSLSocket) ((SSLSocketFactory) SSLSocketFactory.getDefault()).createSocket(tunnel, host, 443, true);
            ssl.startHandshake();
            OutputStream out = ssl.getOutputStream();
            out.write(("HEAD / HTTP/1.1\r\nHost: " + host + "\r\nConnection: close\r\n\r\n").getBytes("US-ASCII"));
            out.flush();
            return ssl.getInputStream().read() >= 0;
        } catch (Exception e) {
            return false;
        } finally {
            try { if (tunnel != null) tunnel.close(); } catch (Exception ignored) { }
        }
    }
}
'''

TUNER_UI_BUTTONS = r'''settingsPresenter.appendSingleButton(UiOptionItem.from("Check VLESS ping", option -> testVlessPing()));
            settingsPresenter.appendSingleButton(UiOptionItem.from("Add VLESS key to the list", option -> addKeyToList()));
            settingsPresenter.appendSingleButton(UiOptionItem.from("Auto-select best VLESS key", option -> runAutoTuner(true)));
            settingsPresenter.appendSingleButton(UiOptionItem.from("Auto-select ByeDPI strategy + routes", option -> runAutoTuner(false)));'''

TUNER_UI_METHODS = r'''    private void addKeyToList() {
        SimpleEditDialog.show(getContext(), "Add VLESS key", "vless://…", "", value -> {
            try {
                String link = value.trim();
                VlessConfigBuilder.parse(link);
                VlessConfigBuilder.buildXrayConfig(link);
                VlessKeyList list = new VlessKeyList(getContext());
                list.add(link);
                MessageHelpers.showMessage(getContext(), "Key added. Saved keys: " + list.getAll().size());
                return true;
            } catch (Exception e) {
                MessageHelpers.showMessage(getContext(), "Invalid VLESS key");
                return false;
            }
        });
    }

    private void runAutoTuner(boolean keys) {
        final Context appContext = getContext().getApplicationContext();
        final Handler handler = new Handler(Looper.getMainLooper());
        new Thread(() -> {
            NetworkAutoTuner.Callback callback = text -> handler.post(() -> MessageHelpers.showMessage(appContext, text));
            String result;
            try {
                result = keys ? NetworkAutoTuner.tuneKeys(appContext, callback) : NetworkAutoTuner.tuneStrategies(appContext, callback);
            } catch (Exception e) {
                result = "Auto-select failed";
            }
            final String message = result;
            handler.post(() -> MessageHelpers.showMessage(appContext, message));
        }, "smarttube-auto-tuner").start();
    }

'''


def tuner_files():
    folder = ROOT / "common" / "src" / "main" / "java" / "com" / "liskovsoft" / "smartyoutubetv2" / "common" / "proxy" / "vless"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "VlessKeyList.java").write_text(KEY_LIST_JAVA, encoding="utf-8")
    (folder / "RouteStore.java").write_text(ROUTE_STORE_JAVA, encoding="utf-8")
    (folder / "NetworkAutoTuner.java").write_text(TUNER_JAVA, encoding="utf-8")
    print("Created VlessKeyList.java, RouteStore.java and NetworkAutoTuner.java")


def byedpi_set_strategy(source):
    return replace_once(
        source,
        "    public synchronized void stop() {",
        "    public synchronized void setStrategy(String strategy) {\n"
        "        prefs.edit().putString(\"strategy\", strategy).apply();\n"
        "    }\n\n"
        "    public synchronized void stop() {",
        "Add ByeDPI strategy setter"
    )


def routes_in_builder(source):
    source = replace_once(
        source,
        "public static volatile boolean byeDpiEnabled = false;",
        "public static volatile boolean byeDpiEnabled = false;\n"
        "    public static volatile java.util.List<String> byeDpiDomains = new java.util.ArrayList<>();",
        "Add tested ByeDPI domain list"
    )
    source = replace_once(
        source,
        '.put("domain", new JSONArray().put("domain:googlevideo.com")',
        '.put("domain", new JSONArray().put("full:unused-a.invalid")',
        "Disable the broad googlevideo rule"
    )
    source = replace_once(
        source,
        '.put("full:youtubei.googleapis.com").put("full:jnn-pa.googleapis.com"))',
        '.put("full:unused-b.invalid"))',
        "Disable the fixed API rule"
    )
    return replace_once(
        source,
        "for (int i = 0; i < oldRules.length(); i++) newRules.put(oldRules.get(i));",
        "if (!byeDpiDomains.isEmpty()) {\n"
        "                JSONArray learned = new JSONArray();\n"
        "                for (String host : byeDpiDomains) learned.put(\"full:\" + host);\n"
        "                newRules.put(new JSONObject().put(\"type\", \"field\").put(\"domain\", learned).put(\"outboundTag\", \"byedpi\"));\n"
        "            }\n"
        "            for (int i = 0; i < oldRules.length(); i++) newRules.put(oldRules.get(i));",
        "Route only tested domains through ByeDPI"
    )


def routes_in_manager(source):
    return replace_once(
        source,
        "VlessConfigBuilder.byeDpiEnabled = byeDpi.isEnabled() && byeDpi.start();",
        "VlessConfigBuilder.byeDpiEnabled = byeDpi.isEnabled() && byeDpi.start();\n"
        "            VlessConfigBuilder.byeDpiDomains = new RouteStore(context).getDomains();",
        "Load tested ByeDPI domains before building the config"
    )


def tuner_ui(source):
    source = replace_once(
        source,
        "import com.liskovsoft.smartyoutubetv2.common.proxy.byedpi.ByeDpiManager;",
        "import com.liskovsoft.smartyoutubetv2.common.proxy.byedpi.ByeDpiManager;\n"
        "import com.liskovsoft.smartyoutubetv2.common.proxy.vless.NetworkAutoTuner;\n"
        "import com.liskovsoft.smartyoutubetv2.common.proxy.vless.VlessKeyList;",
        "Import auto tuner classes"
    )
    source = replace_once(
        source,
        'settingsPresenter.appendSingleButton(UiOptionItem.from("Check VLESS ping", option -> testVlessPing()));',
        TUNER_UI_BUTTONS,
        "Add auto-select buttons"
    )
    return replace_once(
        source,
        "    private void testVlessPing() {\n",
        TUNER_UI_METHODS + "    private void testVlessPing() {\n",
        "Add auto tuner methods"
    )


tuner_files()
edit(
    "common/src/main/java/com/liskovsoft/smartyoutubetv2/common/proxy/byedpi/ByeDpiManager.java",
    byedpi_set_strategy
)
edit(
    "common/src/main/java/com/liskovsoft/smartyoutubetv2/common/proxy/vless/VlessConfigBuilder.java",
    routes_in_builder
)
edit(
    "common/src/main/java/com/liskovsoft/smartyoutubetv2/common/proxy/vless/XrayVlessManager.java",
    routes_in_manager
)
edit(
    "common/src/main/java/com/liskovsoft/smartyoutubetv2/common/app/presenters/settings/GeneralSettingsPresenter.java",
    tuner_ui
)

