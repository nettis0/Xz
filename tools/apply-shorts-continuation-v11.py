#!/usr/bin/env python3
"""Continue the Shorts feed from the player when the current page is exhausted."""
from pathlib import Path

ROOT = Path.cwd() if (Path.cwd() / "common").is_dir() else Path(__file__).resolve().parents[1]


def replace_once(source, old, new, label):
    count = source.count(old)
    if count == 0 and new in source:
        return source
    if count != 1:
        raise SystemExit(f"{label}: expected one exact match, found {count}")
    return source.replace(old, new, 1)


def edit(rel, transform):
    path = ROOT / rel
    if not path.is_file():
        raise SystemExit(f"Required source file missing: {rel}")
    source = path.read_text(encoding="utf-8")
    updated = transform(source)
    if updated != source:
        path.write_text(updated, encoding="utf-8")
        print(f"Shorts continuation applied: {rel}")
    else:
        print(f"Shorts continuation already present: {rel}")


def suggestions(source):
    source = replace_once(
        source,
        "    private int mNextRetryCount;\n",
        "    private int mNextRetryCount;\n    private boolean mShortsContinuationInProgress;\n",
        "Track an in-flight Shorts continuation request"
    )
    source = replace_once(
        source,
        "        disposeActions();\n        //mCurrentGroup = video.getGroup();",
        "        disposeActions();\n        mShortsContinuationInProgress = false;\n        //mCurrentGroup = video.getGroup();",
        "Reset Shorts continuation state when playback changes"
    )

    marker = "    public Video getPrevious() {"
    methods = """    /**
     * Returns the next playable item in the active Shorts feed, without falling
     * back to unrelated playback queues or generic recommendations.
     */
    public Video getNextShortInFeed() {
        Video current = getVideo();

        return current != null && current.belongsToShortsGroup() ?
                getNextFromGroup(current) : null;
    }

    /**
     * Load another page of the active Shorts feed. The callback is delivered
     * once on success, an empty page, or a request error.
     */
    public void continueShortsGroup(Runnable onReady) {
        Video current = getVideo();
        VideoGroup group = current != null ? current.getGroup() : null;

        if (current == null || !current.belongsToShortsGroup() || group == null ||
                group.getNextPageKey() == null || group.getNextPageKey().isEmpty()) {
            if (onReady != null) {
                onReady.run();
            }
            return;
        }

        if (mShortsContinuationInProgress) {
            return;
        }

        mShortsContinuationInProgress = true;
        continueGroup(group, ignored -> {
            mShortsContinuationInProgress = false;
            if (onReady != null) {
                onReady.run();
            }
        }, true);
    }

"""
    if "public Video getNextShortInFeed()" not in source:
        source = replace_once(source, marker, methods + marker, "Expose Shorts feed continuation")

    # Ensure a callback from continueGroup is delivered exactly once, including
    # when the continuation request returns an error or an empty response.
    source = replace_once(
        source,
        "        MediaGroup mediaGroup = group.getMediaGroup();\n\n        Disposable continueAction =",
        "        MediaGroup mediaGroup = group.getMediaGroup();\n"
        "        final boolean[] callbackDelivered = {false};\n\n"
        "        Disposable continueAction =",
        "Track continuation callback completion"
    )

    old_success = """                            if (callback != null) {
                                callback.onVideoGroup(videoGroup);
                            } else {
                                continueGroupIfNeeded(videoGroup);
                            }"""
    new_success = """                            if (callback != null) {
                                if (!callbackDelivered[0]) {
                                    callbackDelivered[0] = true;
                                    callback.onVideoGroup(videoGroup);
                                }
                            } else {
                                continueGroupIfNeeded(videoGroup);
                            }"""
    source = replace_once(source, old_success, new_success, "Avoid duplicate continuation callbacks")

    old_error = """                            if (getPlayer() != null) {
                                getPlayer().showProgressBar(false);
                            }
                        },
                        () -> {
                            if (getPlayer() != null) {
                                getPlayer().showProgressBar(false);
                            }
                        }"""
    new_error = """                            if (getPlayer() != null) {
                                getPlayer().showProgressBar(false);
                            }
                            if (callback != null && !callbackDelivered[0]) {
                                callbackDelivered[0] = true;
                                callback.onVideoGroup(group);
                            }
                        },
                        () -> {
                            if (getPlayer() != null) {
                                getPlayer().showProgressBar(false);
                            }
                            if (callback != null && !callbackDelivered[0]) {
                                callbackDelivered[0] = true;
                                callback.onVideoGroup(group);
                            }
                        }"""
    source = replace_once(source, old_error, new_error, "Complete Shorts continuation callback on error or empty page")
    return source


def video_loader(source):
    old = """        Video next = mSuggestionsController.getNext();

        if (next != null) {
            openVideoInt(next);
        } else {
            waitMetadataSync(getVideo(), true);
        }"""
    new = """        Video current = getVideo();

        if (current.belongsToShortsGroup()) {
            Video nextShort = mSuggestionsController.getNextShortInFeed();

            if (nextShort != null) {
                openVideoInt(nextShort);
            } else if (current.getGroup() != null &&
                    current.getGroup().getNextPageKey() != null &&
                    !current.getGroup().getNextPageKey().isEmpty()) {
                // The loaded page is exhausted: fetch the next Shorts page before
                // asking generic video metadata for an unrelated recommendation.
                mSuggestionsController.continueShortsGroup(() -> {
                    if (getPlayer() == null || getVideo() == null || !current.equals(getVideo())) {
                        return;
                    }

                    Video continuedShort = mSuggestionsController.getNextShortInFeed();
                    if (continuedShort != null) {
                        openVideoInt(continuedShort);
                    } else {
                        waitMetadataSync(current, true);
                    }
                });
            } else {
                Video next = mSuggestionsController.getNext();
                if (next != null) {
                    openVideoInt(next);
                } else {
                    waitMetadataSync(current, true);
                }
            }
        } else {
            Video next = mSuggestionsController.getNext();

            if (next != null) {
                openVideoInt(next);
            } else {
                waitMetadataSync(current, true);
            }
        }"""
    return replace_once(source, old, new, "Continue the Shorts feed after the loaded page ends")


edit(
    "common/src/main/java/com/liskovsoft/smartyoutubetv2/common/app/models/playback/controllers/SuggestionsController.java",
    suggestions
)
edit(
    "common/src/main/java/com/liskovsoft/smartyoutubetv2/common/app/models/playback/controllers/VideoLoaderController.java",
    video_loader
)

print("Shorts feed continuation and next-page loading applied.")
