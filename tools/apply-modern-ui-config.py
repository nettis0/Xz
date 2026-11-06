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
