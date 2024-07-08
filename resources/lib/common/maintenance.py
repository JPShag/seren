import os
import time

import xbmcgui
import xbmcvfs

from resources.lib.common import tools
from resources.lib.database import cache
from resources.lib.database.premiumizeTransfers import PremiumizeTransfers
from resources.lib.database.skinManager import SkinManager
from resources.lib.debrid import all_debrid, premiumize, real_debrid
from resources.lib.indexers.trakt import TraktAPI
from resources.lib.indexers.tvdb import TVDBAPI
from resources.lib.modules.globals import g
from resources.lib.modules.providers.install_manager import ProviderInstallManager

def update_themes():
    """
    Perform checks for any theme updates.
    """
    if g.get_bool_setting("skin.updateAutomatic"):
        SkinManager().check_for_updates(silent=True)

def update_provider_packages():
    """
    Perform checks for provider package updates.
    """
    provider_check_stamp = g.get_float_runtime_setting("provider.updateCheckTimeStamp", 0)
    automatic = g.get_bool_setting("providers.autoupdates")
    if time.time() > (provider_check_stamp + 24 * 60 * 60):
        available_updates = ProviderInstallManager().check_for_updates(silent=True, automatic=automatic)
        if not automatic and available_updates:
            g.notification(g.ADDON_NAME, g.get_language_string(30253))
        g.set_runtime_setting("provider.updateCheckTimeStamp", str(time.time()))

def refresh_apis():
    """
    Refresh common API tokens.
    """
    TraktAPI().try_refresh_token()
    real_debrid.RealDebrid().try_refresh_token()
    TVDBAPI().try_refresh_token()

def wipe_install():
    """
    Destroys Seren's user_data folder for current user resetting addon to default.
    """
    confirm = xbmcgui.Dialog().yesno(g.ADDON_NAME, g.get_language_string(30083))
    if confirm == 0:
        return

    confirm = xbmcgui.Dialog().yesno(
        g.ADDON_NAME,
        f"{g.get_language_string(30034)}{g.color_string(g.get_language_string(30035))}",
    )
    if confirm == 0:
        return

    path = tools.validate_path(g.ADDON_USERDATA_PATH)
    if xbmcvfs.exists(path):
        xbmcvfs.rmdir(path, True)
    xbmcvfs.mkdir(g.ADDON_USERDATA_PATH)

def premiumize_transfer_cleanup():
    """
    Cleanup transfers created by Seren at Premiumize.
    """
    service = premiumize.Premiumize()
    premiumize_transfers = PremiumizeTransfers()
    fair_usage = service.get_used_space()
    threshold = g.get_float_setting("premiumize.threshold")

    if fair_usage < threshold:
        g.log("Premiumize Fair Usage below threshold, no cleanup required")
        return

    seren_transfers = premiumize_transfers.get_premiumize_transfers()
    if seren_transfers is None:
        g.log("Failed to cleanup transfers, API error", "error")
        return

    if not seren_transfers:
        g.log("No Premiumize transfers have been created")
        return

    g.log("Premiumize Fair Usage is above threshold, cleaning up Seren transfers")
    for transfer in seren_transfers:
        service.delete_transfer(transfer["transfer_id"])
        premiumize_transfers.remove_premiumize_transfer(transfer["transfer_id"])

def account_premium_status_checks():
    """
    Updates premium status settings to reflect current state and advises users of expiries if enabled.
    """
    def set_settings_status(debrid_provider, status):
        """
        Ease of use method to set premium status setting.
        """
        g.set_setting(f"{debrid_provider}.premiumstatus", status.title())

    def display_expiry_notification(display_debrid_name):
        """
        Notify user of expiry of debrid premium status.
        """
        if g.get_bool_setting("general.accountNotifications"):
            g.notification(
                f"{g.ADDON_NAME}",
                g.get_language_string(30036).format(display_debrid_name),
            )

    valid_debrid_providers = [
        ("Real Debrid", real_debrid.RealDebrid, "rd"),
        ("Premiumize", premiumize.Premiumize, "premiumize"),
        ("All Debrid", all_debrid.AllDebrid, "alldebrid"),
    ]

    for name, service_module_class, prefix in valid_debrid_providers:
        service_module = service_module_class()
        if service_module.is_service_enabled():
            status = service_module.get_account_status()
            if status == "expired":
                display_expiry_notification(name)
            g.log(f"{name}: {status}")
            set_settings_status(prefix, status)

def toggle_reuselanguageinvoker(forced_state=None):
    """
    Toggle the state of reuselanguageinvoker setting in addon.xml and reload the profile.
    """
    def _store_and_reload(output):
        with open(file_path, "w+") as addon_xml:
            addon_xml.writelines(output)
        xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30531))
        g.reload_profile()

    file_path = os.path.join(g.ADDON_DATA_PATH, "addon.xml")

    with open(file_path) as addon_xml:
        file_lines = addon_xml.readlines()

    for i, line in enumerate(file_lines):
        if "reuselanguageinvoker" in line:
            if ("false" in line and forced_state is None) or ("false" in line and forced_state):
                file_lines[i] = line.replace("false", "true")
                g.set_setting("reuselanguageinvoker.status", "Enabled")
                _store_and_reload(file_lines)
            elif ("true" in line and forced_state is None) or ("true" in line and forced_state is False):
                file_lines[i] = line.replace("true", "false")
                g.set_setting("reuselanguageinvoker.status", "Disabled")
                _store_and_reload(file_lines)
            break

def run_maintenance():
    """
    Entry point for background maintenance cycle.
    """
    g.log("Performing Maintenance")
    # ADD COMMON HOUSE KEEPING ITEMS HERE #

    # Refresh API tokens
    try:
        refresh_apis()
    except Exception as e:
        g.log(f"Failed to update API keys: {e}", 'error')

    # Check account premium statuses
    try:
        account_premium_status_checks()
    except Exception as e:
        g.log(f"Failed to check account status: {e}", 'error')

    # Update provider packages and themes
    ProviderInstallManager()
    update_provider_packages()
    update_themes()

    # Check Premiumize Fair Usage for cleanup
    if g.get_bool_setting("premiumize.enabled") and g.get_bool_setting("premiumize.autodelete"):
        try:
            premiumize_transfer_cleanup()
        except Exception as e:
            g.log(f"Failed to cleanup PM transfers: {e}", 'error')

    # Cache cleanup
    cache.Cache().check_cleanup()
