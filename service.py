import sqlite3
import sys
from random import randint

import xbmc

from resources.lib.common import tools

# Check if running in a stub environment for testing
if tools.is_stub():
    from mock_kodi import MOCK  # Ensure this import is only in the stub environment

from resources.lib.modules.globals import g
from resources.lib.modules.seren_version import do_version_change
from resources.lib.modules.serenMonitor import SerenMonitor
from resources.lib.modules.update_news import do_update_news
from resources.lib.modules.manual_timezone import validate_timezone_detected

# Initialize global settings and parameters
g.init_globals(sys.argv)
do_version_change()

# Logging service start details
g.log("##################  STARTING SERVICE  ######################")
g.log(f"### {g.ADDON_ID} {g.VERSION}")
g.log(f"### Platform: {g.PLATFORM}")
g.log(f"### Python: {sys.version.split(' ', 1)[0]}")
g.log(f"### SQLite: {sqlite3.sqlite_version}")  # pylint: disable=no-member
g.log(f"### Detected Kodi Version: {g.KODI_VERSION}")
g.log(f"### Detected timezone: {repr(g.LOCAL_TIMEZONE.zone)}")
g.log("#############  SERVICE ENTERED KEEP ALIVE  #################")

monitor = SerenMonitor()

try:
    # Execute various maintenance tasks
    xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=longLifeServiceManager")')

    do_update_news()
    validate_timezone_detected()
    
    try:
        g.clear_kodi_bookmarks()
    except TypeError:
        g.log(
            "Unable to clear bookmarks on service init. This is not a problem if it occurs immediately after install.",
            "warning",
        )

    xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=torrentCacheCleanup")')

    # Allow widget loads to complete by waiting for 30 seconds
    g.wait_for_abort(30)
    
    # Main service loop to run various maintenance tasks at intervals
    while not monitor.abortRequested():
        xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=runMaintenance")')
        
        # Check for abort and run maintenance tasks with appropriate delays
        if not g.wait_for_abort(15):
            xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=syncTraktActivities")')
        
        if not g.wait_for_abort(15):
            xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=cleanOrphanedMetadata")')
        
        if not g.wait_for_abort(15):
            xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=updateLocalTimezone")')
        
        # Sleep for a random interval between 13 and 17 minutes before repeating
        if g.wait_for_abort(60 * randint(13, 17)):
            break

finally:
    del monitor  # Clean up the monitor instance
    g.deinit()  # Deinitialize global settings and parameters
