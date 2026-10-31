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
                if (focused == mChannel) {
                    return mSubscribe.requestFocus();
                }
                if (focused == mSubscribe) {
                    return mActions.getChildAt(0).requestFocus();
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
                return focused == mChannel;

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
    # A Shorts grid is authoritative: some API responses omit the isShorts
    # marker even though the item came from the dedicated Shorts feed.
    source = replace_once(
        source,
        "    private boolean mChannelGrid;\\n",
        "    private boolean mChannelGrid;\\n    private boolean mShortsSection;\\n",
        "Track whether this grid is the dedicated Shorts section"
    )
    source = replace_once(
        source,
        "    public void setShorts(boolean shorts) {\\n        if (!shorts) {",
        "    public void setShorts(boolean shorts) {\\n        mShortsSection = shorts;\\n        if (!shorts) {",
        "Remember Shorts section mode"
    )
    source = replace_once(
        source,
        "    public void update(VideoGroup group) {\\n        int action = group.getAction();",
        "    public void update(VideoGroup group) {\\n        if (mShortsSection && group.getVideos() != null) {\\n            for (Video video : group.getVideos()) {\\n                if (video != null) {\\n                    video.isShorts = true;\\n                }\\n            }\\n        }\\n\\n        int action = group.getAction();",
        "Mark every item loaded from the Shorts feed as a Short"
    )
    source = replace_once(
        source,
        "                viewHolder.itemView.setOnClickListener(v -> mPresenter.onVideoItemClicked((Video) viewHolder.getItem()));",
        "                viewHolder.itemView.setOnClickListener(v -> {\\n                    Video video = (Video) viewHolder.getItem();\\n                    if (mShortsSection) {\\n                        video.isShorts = true;\\n                    }\\n                    mPresenter.onVideoItemClicked(video);\\n                });",
        "Preserve Shorts mode when opening a video from the Shorts grid"
    )
    source = replace_once(
        source,
        "        mPresenter.onVideoItemSelected((Video) mAdapter.get(position));",
        "        Video selected = (Video) mAdapter.get(position);\\n        if (mShortsSection) {\\n            selected.isShorts = true;\\n        }\\n        mPresenter.onVideoItemSelected(selected);",
        "Keep the selected Shorts item marked for correct playback navigation"
    )
    return source


def shorts_overlay_interactions(source):
    source = replace_once(
        source,
        "        mTime = findViewById(R.id.modern_shorts_time);\\n",
        "        mTime = findViewById(R.id.modern_shorts_time);\\n\\n        // The title opens the video's menu, which includes the full description.\\n        mTitle.setFocusable(true);\\n        mTitle.setFocusableInTouchMode(true);\\n        mTitle.setOnClickListener(v -> {\\n            if (mListener != null) {\\n                mListener.onShortsMore();\\n            }\\n        });\\n",
        "Make Shorts title open details and description"
    )
    source = replace_once(
        source,
        "            case KeyEvent.KEYCODE_DPAD_RIGHT:\\n                mTitle.setFocusable(false);\\n                mChannel.requestFocus();\\n                return true;",
        "            case KeyEvent.KEYCODE_DPAD_RIGHT:\\n                return mTitle.requestFocus();",
        "Enter the Shorts details panel at its title"
    )
    source = replace_once(
        source,
        "            case KeyEvent.KEYCODE_DPAD_DOWN:\\n                if (focused == mChannel) {",
        "            case KeyEvent.KEYCODE_DPAD_DOWN:\\n                if (focused == mTitle) {\\n                    return mChannel.requestFocus();\\n                }\\n                if (focused == mChannel) {",
        "Include the title in vertical panel focus navigation"
    )
    source = replace_once(
        source,
        "            case KeyEvent.KEYCODE_DPAD_UP:\\n                if (inActions) {",
        "            case KeyEvent.KEYCODE_DPAD_UP:\\n                if (focused == mChannel) {\\n                    return mTitle.requestFocus();\\n                }\\n                if (inActions) {",
        "Return focus from the channel row to the Shorts title"
    )
    return source


def shorts_dimensions(source):
    return replace_once(
        source,
        '<dimen name="modern_shorts_panel_top">279dp</dimen>',
        '<dimen name="modern_shorts_panel_top">70dp</dimen>',
        "Move the Shorts side rail up so the full vertical action stack fits"
    )


def shorts_layout_interactions(source):
    return replace_once(
        source,
        '            android:textStyle="bold" />',
        '            android:textStyle="bold"\\n'
        '            android:focusable="true"\\n'
        '            android:clickable="true" />',
        "Make the Shorts title focusable and clickable for description access"
    )


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
    "smarttubetv/src/main/java/com/liskovsoft/smartyoutubetv2/tv/ui/modern/widgets/ModernCardPresenter.java",
    card_image_optimization
)

print("Modern YouTube TV pass applied: modern player routing, vertical Shorts side rail and D-pad navigation, plus app-wide thumbnail and playback optimizations.")
