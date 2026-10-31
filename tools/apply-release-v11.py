#!/usr/bin/env python3
"""Apply the Shorts/player/settings fixes for the next SmartTube fork release."""
from pathlib import Path

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
    if count == 0 and new in source:
        return source
    if count != 1:
        raise SystemExit(f"{label}: expected one exact match, found {count}")
    return source.replace(old, new, 1)


def shorts_next_in_feed(source):
    old = """        Video result = null;
        Video next = Playlist.instance().getNext();"""
    new = """        Video result = null;

        // Shorts are a feed, not a regular playback queue. Prefer the adjacent
        // item in the same Shorts group before generic queue/recommendation data.
        Video current = getVideo();
        if (current.belongsToShortsGroup()) {
            result = getNextFromGroup(current);
        }
        if (result != null) {
            return result;
        }

        Video next = Playlist.instance().getNext();"""
    source = replace_once(source, old, new, "Prefer the next item in the Shorts feed")

    marker = "    private Video getPreviousFromGroup(Video current) {"
    helper = """    private Video getNextFromGroup(Video current) {
        if (current == null) {
            return null;
        }

        VideoGroup group = current.getGroup();
        if (group == null || group.isEmpty()) {
            return null;
        }

        boolean foundCurrent = false;
        for (Video item : group.getVideos()) {
            if (foundCurrent && item.hasVideo() && !item.isUpcoming) {
                // Every video opened from this group must stay in Shorts mode.
                item.isShorts = true;
                item.sectionId = MediaGroup.TYPE_SHORTS;
                return item;
            }

            if (item.equals(current)) {
                foundCurrent = true;
            }
        }

        return null;
    }

"""
    if "private Video getNextFromGroup(Video current)" not in source:
        source = replace_once(source, marker, helper + marker, "Add Shorts next-item lookup")

    old_previous = """                    if (item.equals(current)) {
                        result = previous;
                        break;
                    }"""
    new_previous = """                    if (item.equals(current)) {
                        if (previous != null && current.belongsToShortsGroup()) {
                            previous.isShorts = true;
                            previous.sectionId = MediaGroup.TYPE_SHORTS;
                        }
                        result = previous;
                        break;
                    }"""
    source = replace_once(source, old_previous, new_previous, "Keep previous item in Shorts mode")
    return source


def shorts_overlay(source):
    source = replace_once(
        source,
        "import android.view.KeyEvent;\n",
        "import android.view.KeyEvent;\nimport android.view.MotionEvent;\n",
        "Import touch gesture events"
    )
    source = replace_once(
        source,
        "import com.liskovsoft.smartyoutubetv2.common.app.models.data.Video;\n",
        "import com.liskovsoft.smartyoutubetv2.common.app.models.data.Video;\n"
        "import com.liskovsoft.smartyoutubetv2.common.app.presenters.SearchPresenter;\n",
        "Import the voice search presenter"
    )

    source = replace_once(
        source,
        "    private float mProgress;\n",
        "    private float mProgress;\n"
        "    private float mTouchDownX;\n"
        "    private float mTouchDownY;\n"
        "    private boolean mTrackingVideoTouch;\n"
        "    private final int mSwipeThresholdPx;\n",
        "Add Shorts gesture state"
    )
    source = replace_once(
        source,
        "        setWillNotDraw(false);\n",
        "        setWillNotDraw(false);\n"
        "        setClickable(true);\n"
        "        mSwipeThresholdPx = Math.round(64 * context.getResources().getDisplayMetrics().density);\n",
        "Enable touch handling on the video area"
    )

    source = replace_once(
        source,
        "        addAction(R.id.action_thumbs_up, R.string.action_like);\n",
        "        addVoiceSearchButton();\n"
        "        addAction(R.id.action_thumbs_up, R.string.action_like);\n",
        "Add the microphone to the Shorts action rail"
    )

    marker = "    private void addAction(int actionId, int labelResId) {"
    voice_method = """    private void addVoiceSearchButton() {
        ImageView button = new ImageView(getContext());
        int size = getResources().getDimensionPixelSize(R.dimen.modern_player_button);
        int padding = (size - getResources().getDimensionPixelSize(R.dimen.modern_player_button_icon)) / 2;
        button.setPadding(padding, padding, padding, padding);
        button.setImageResource(R.drawable.modern_ic_mic);
        button.setBackgroundResource(R.drawable.modern_mic_circle);
        button.setScaleType(ImageView.ScaleType.CENTER_INSIDE);
        button.setFocusable(true);
        button.setFocusableInTouchMode(true);
        button.setClickable(true);
        button.setContentDescription("Voice search");

        ColorStateList tint = ContextCompat.getColorStateList(getContext(), R.color.modern_text_primary);
        ImageViewCompat.setImageTintList(button, tint);

        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(size, size);
        params.bottomMargin = getResources().getDimensionPixelSize(R.dimen.modern_player_group_gap) * 2;
        mActions.addView(button, 0, params);
        button.setOnClickListener(v -> SearchPresenter.instance(getContext()).startVoice());
    }

"""
    if "private void addVoiceSearchButton()" not in source:
        source = replace_once(source, marker, voice_method + marker, "Create the Shorts microphone button")

    # The info action is already available in the rail. Use it for title/description,
    # rather than opening the generic More menu from both text fields.
    old_details = """        mTitle.setOnClickListener(v -> {
            if (mListener != null) {
                mListener.onShortsMore();
            }
        });
        mDescription.setOnClickListener(v -> {
            if (mListener != null) {
                mListener.onShortsMore();
            }
        });"""
    new_details = """        mTitle.setOnClickListener(v -> {
            if (mListener != null) {
                mListener.onShortsAction(R.id.action_info);
            }
        });
        mDescription.setOnClickListener(v -> {
            if (mListener != null) {
                mListener.onShortsAction(R.id.action_info);
            }
        });"""
    source = replace_once(source, old_details, new_details, "Open the Shorts info action from the title and description")

    touch_marker = "    public boolean isPanelFocused() {"
    touch_methods = """    /**
     * Touch controls for devices with a touchscreen: swipe up for the next Short,
     * swipe down for the previous one, and tap the video to pause/resume.
     * Touches that begin in the side panel remain with its buttons.
     */
    @Override
    public boolean onTouchEvent(MotionEvent event) {
        switch (event.getActionMasked()) {
            case MotionEvent.ACTION_DOWN:
                if (!mVideoRect.contains(event.getX(), event.getY())) {
                    mTrackingVideoTouch = false;
                    return false;
                }
                mTouchDownX = event.getX();
                mTouchDownY = event.getY();
                mTrackingVideoTouch = true;
                return true;

            case MotionEvent.ACTION_MOVE:
                return mTrackingVideoTouch;

            case MotionEvent.ACTION_UP:
                if (!mTrackingVideoTouch) {
                    return false;
                }

                float deltaX = event.getX() - mTouchDownX;
                float deltaY = event.getY() - mTouchDownY;
                mTrackingVideoTouch = false;

                if (Math.abs(deltaY) >= mSwipeThresholdPx &&
                        Math.abs(deltaY) > Math.abs(deltaX) * 1.15f) {
                    if (mListener != null) {
                        if (deltaY < 0) {
                            mListener.onShortsNext();
                        } else {
                            mListener.onShortsPrevious();
                        }
                    }
                } else if (Math.abs(deltaX) < mSwipeThresholdPx &&
                        Math.abs(deltaY) < mSwipeThresholdPx && mListener != null) {
                    mListener.onShortsTogglePlayback();
                    post(this::updatePlaybackState);
                }
                return true;

            case MotionEvent.ACTION_CANCEL:
                boolean wasTracking = mTrackingVideoTouch;
                mTrackingVideoTouch = false;
                return wasTracking;

            default:
                return mTrackingVideoTouch;
        }
    }

"""
    if "public boolean onTouchEvent(MotionEvent event)" not in source:
        source = replace_once(source, touch_marker, touch_methods + touch_marker, "Add touch swipes to Shorts playback")

    return source


def trim_general_settings(source):
    source = replace_once(source, "        appendBackgroundPlaybackCategory(settingsPresenter);\n", "",
                          "Remove unused background playback settings")
    source = replace_once(source, "        appendScreenDimmingCategory(settingsPresenter);\n", "",
                          "Remove screen dimming settings")
    return source


def trim_language_settings(source):
    return replace_once(source, "        appendCountryCategory(settingsPresenter);\n", "",
                        "Remove the unused country selector")


def trim_data_source(source):
    source = replace_once(
        source,
        "import com.liskovsoft.smartyoutubetv2.common.app.presenters.settings.BackupSettingsPresenter;\n",
        "",
        "Remove the backup/restore presenter import"
    )
    return replace_once(
        source,
        """        settingItems.add(new SettingsItem(
                context.getString(R.string.app_backup_restore), () -> BackupSettingsPresenter.instance(context).show(), R.drawable.settings_backup));
""",
        "",
        "Remove the unused backup/restore menu entry"
    )


def trim_player_settings(source):
    source = replace_once(
        source,
        "                {R.string.screen_dimming, PlayerTweaksData.PLAYER_BUTTON_SCREEN_DIMMING},\n",
        "",
        "Remove the screen-dimming button setting"
    )
    return replace_once(
        source,
        "                {R.string.run_in_background, PlayerTweaksData.PLAYER_BUTTON_PIP},\n",
        "",
        "Remove the PiP/background player-button setting"
    )


edit(
    "common/src/main/java/com/liskovsoft/smartyoutubetv2/common/app/models/playback/controllers/SuggestionsController.java",
    shorts_next_in_feed
)
edit(
    "smarttubetv/src/main/java/com/liskovsoft/smartyoutubetv2/tv/ui/modern/playback/ModernShortsOverlay.java",
    shorts_overlay
)
edit(
    "common/src/main/java/com/liskovsoft/smartyoutubetv2/common/app/presenters/settings/GeneralSettingsPresenter.java",
    trim_general_settings
)
edit(
    "common/src/main/java/com/liskovsoft/smartyoutubetv2/common/app/presenters/settings/LanguageSettingsPresenter.java",
    trim_language_settings
)
edit(
    "common/src/main/java/com/liskovsoft/smartyoutubetv2/common/misc/AppDataSourceManager.java",
    trim_data_source
)
edit(
    "common/src/main/java/com/liskovsoft/smartyoutubetv2/common/app/presenters/settings/PlayerSettingsPresenter.java",
    trim_player_settings
)

print("Release v11 Shorts navigation, touch gestures, voice search and settings cleanup applied.")
