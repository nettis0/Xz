#!/usr/bin/env python3
from pathlib import Path

ROOT = Path.cwd() if (Path.cwd() / "common").is_dir() else Path(__file__).resolve().parents[1]


def edit(rel, transform):
    path = ROOT / rel
    if not path.is_file():
        raise SystemExit(f"Required source file missing: {rel}")
    source = path.read_text(encoding="utf-8")
    updated = transform(source)
    if updated != source:
        path.write_text(updated, encoding="utf-8")
        print(f"Shorts fix applied: {rel}")
    else:
        print(f"Shorts fix already present: {rel}")


def replace_once(source, old, new, label):
    count = source.count(old)
    if count == 0 and new in source:
        return source
    if count != 1:
        raise SystemExit(f"{label}: expected one match, found {count}")
    return source.replace(old, new, 1)


def grid(source):
    # Keep the selected Shorts feed identity attached to each item all the way
    # through the modern grid click/selection callbacks and into playback.
    source = source.replace(
        "video.isShorts = true;",
        "video.isShorts = true;\n                    video.sectionId = com.liskovsoft.mediaserviceinterfaces.data.MediaGroup.TYPE_SHORTS;"
    )
    source = source.replace(
        "selected.isShorts = true;",
        "selected.isShorts = true;\n            selected.sectionId = com.liskovsoft.mediaserviceinterfaces.data.MediaGroup.TYPE_SHORTS;"
    )
    return source


def playback(source):
    old = """        if (mIsShortsMode) {
            prefetchNextShort();
        }"""
    new = """        if (mIsShortsMode) {
            // Metadata (including the full description) may arrive after setVideo().
            if (mShorts != null && mVideo != null) {
                mShorts.bind(mVideo);
            }
            prefetchNextShort();
        }"""
    source = replace_once(source, old, new, "Refresh Shorts details after the first decoded frame")
    return source


def overlay(source):
    source = replace_once(
        source,
        "    private TextView mTitle;\n",
        "    private TextView mTitle;\n    private TextView mDescription;\n",
        "Add the Shorts description view"
    )
    source = replace_once(
        source,
        "        mTitle = findViewById(R.id.modern_shorts_title);\n",
        "        mTitle = findViewById(R.id.modern_shorts_title);\n        mDescription = findViewById(R.id.modern_shorts_description);\n",
        "Bind the Shorts description view"
    )
    source = replace_once(
        source,
        """        mTitle.setText(video.getTitle());
        bindRow(mChannel, 0, video.getAuthor());""",
        """        mTitle.setText(video.getTitle());
        CharSequence description = video.description;
        mDescription.setText(description);
        mDescription.setVisibility(description != null && description.length() > 0 ? View.VISIBLE : View.GONE);
        bindRow(mChannel, 0, video.getAuthor());""",
        "Display Shorts description and author"
    )
    # Do not let a delayed metadata refresh erase a working title/channel panel.
    source = replace_once(
        source,
        "        mChannel.setOnClickListener(v -> mListener.onShortsAction(R.id.action_channel));",
        """        mChannel.setOnClickListener(v -> {
            if (mListener != null) {
                mListener.onShortsAction(R.id.action_channel);
            }
        });""",
        "Make the channel row safely open the creator"
    )
    source = replace_once(
        source,
        "        more.setOnClickListener(v -> mListener.onShortsMore());",
        """        more.setOnClickListener(v -> {
            if (mListener != null) {
                mListener.onShortsMore();
            }
        });
        mTitle.setOnClickListener(v -> {
            if (mListener != null) {
                mListener.onShortsMore();
            }
        });
        mDescription.setOnClickListener(v -> {
            if (mListener != null) {
                mListener.onShortsMore();
            }
        });""",
        "Open the full video details from title or description"
    )
    return source


def shorts_layout(source):
    marker = """        <TextView
            android:id="@+id/modern_shorts_title""" 
    if "android:id=\"@+id/modern_shorts_description\"" not in source:
        pos = source.find("        <include\n            android:id=\"@+id/modern_shorts_channel\"")
        if pos < 0:
            raise SystemExit("Could not locate the Shorts channel row for description insertion")
        description = """        <TextView
            android:id="@+id/modern_shorts_description"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginStart="@dimen/modern_shorts_padding"
            android:layout_marginEnd="@dimen/modern_shorts_padding"
            android:layout_marginTop="@dimen/modern_shorts_row_gap"
            android:ellipsize="end"
            android:maxLines="5"
            android:includeFontPadding="false"
            android:textColor="@color/modern_text_secondary"
            android:textSize="@dimen/modern_tile_meta_size"
            android:visibility="gone" />

"""
        source = source[:pos] + description + source[pos:]
    return source


edit(
    "smarttubetv/src/main/java/com/liskovsoft/smartyoutubetv2/tv/ui/modern/browse/ModernGridView.java",
    grid
)
edit(
    "smarttubetv/src/main/java/com/liskovsoft/smartyoutubetv2/tv/ui/modern/playback/ModernPlaybackFragment.java",
    playback
)
edit(
    "smarttubetv/src/main/java/com/liskovsoft/smartyoutubetv2/tv/ui/modern/playback/ModernShortsOverlay.java",
    overlay
)
edit(
    "smarttubetv/src/main/res/layout/modern_shorts_overlay.xml",
    shorts_layout
)

print("Shorts navigation, creator/details panel, description and social actions are now patched.")
