#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path.cwd() if (Path.cwd() / "common").is_dir() else Path(__file__).resolve().parents[1]
TARGET = ROOT / "common/src/main/java/com/liskovsoft/smartyoutubetv2/common/app/presenters/BrowsePresenter.java"

if not TARGET.is_file():
    raise SystemExit(f"Required source file missing: {TARGET}")

source = TARGET.read_text(encoding="utf-8")

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
    if replacement in source:
        print("Sidebar filter already applied.")
    else:
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

TARGET.write_text(source, encoding="utf-8")
print("Modern UI configuration applied: Home, Shorts, Kids, Subscriptions, History, Settings; custom pinned channels/playlists preserved.")
