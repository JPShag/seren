from resources.lib.modules.providers.settings import SettingsManager

def get_setting(package_name, setting_id):
    """
    Retrieves a setting value for a provider package.
    
    :param package_name: The name of the package.
    :type package_name: str
    :param setting_id: The ID of the setting to retrieve.
    :type setting_id: str
    :return: The value of the specified setting.
    :rtype: object
    """
    settings_manager = SettingsManager()
    return settings_manager.get_setting(package_name, setting_id)

def set_setting(package_name, setting_id, value):
    """
    Sets the value of a setting for a provider package.
    
    :param package_name: The name of the package.
    :type package_name: str
    :param setting_id: The ID of the setting to set.
    :type setting_id: str
    :param value: The new value for the setting.
    :type value: object
    :return: The value of the setting after it is set.
    :rtype: object
    """
    settings_manager = SettingsManager()
    return settings_manager.set_setting(package_name, setting_id, value)
