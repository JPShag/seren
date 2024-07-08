import sys
from resources.lib.modules import router
from resources.lib.modules.globals import g
from resources.lib.modules.serenMonitor import ONWAKE_NETWORK_UP_DELAY
from resources.lib.modules.timeLogger import TimeLogger

def _sleeping_retry_handler():
    """
    Handles retrying when the system is detected to be in a sleeping state.
    For Android platforms, it will check if the system is sleeping and wait for it to wake up.
    """
    sleeping = False

    if g.PLATFORM == "android":
        attempts = 0
        while (
            attempts <= ONWAKE_NETWORK_UP_DELAY
            and (sleeping := g.get_bool_runtime_setting("system.sleeping", False))
            and not g.wait_for_abort(1)
        ):
            attempts += 1
        if sleeping and not g.abort_requested():
            g.log(
                f"Ignoring {g.REQUEST_PARAMS.get('action', '')} plugin action as system is supposed to be \"sleeping\"",
                "info",
            )

    return not sleeping

def seren_recode_endpoint():
    """
    The main endpoint for handling plugin actions for Seren Recode.
    It initializes global settings, checks if the system is in a sleeping state,
    and dispatches the request to the appropriate handler.
    """
    try:
        # Initialize global settings and parameters
        g.init_globals(sys.argv)

        # Check if system is not sleeping and request is not aborted
        if _sleeping_retry_handler() and not g.abort_requested():
            with TimeLogger(f"{g.REQUEST_PARAMS.get('action', '')}"):
                # Dispatch the request based on parameters
                router.dispatch(g.REQUEST_PARAMS)

    except Exception as e:
        # Log the exception and cancel directory if an error occurs
        g.log(f"Exception occurred: {e}", "error")
        g.cancel_directory()
        raise

    finally:
        # Deinitialize global settings and parameters
        g.deinit()

if __name__ == "__main__":  # pragma: no cover
    seren_recode_endpoint()
