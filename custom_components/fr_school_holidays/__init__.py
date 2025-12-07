"""French School Vacation Times custom component for Home Assistant."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_CORE_CONFIG_UPDATE, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .sensor import FRIENDLY_NAMES

DOMAIN = "fr_school_holidays"
PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up via YAML (legacy)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up config entry."""
    await _async_sync_entity_names(hass, entry)
    # Re-sync names when core config changes (keeps names aligned to French defaults).
    async def _handle_core_update(event) -> None:
        await _async_sync_entity_names(hass, entry)

    unsub = hass.bus.async_listen(EVENT_CORE_CONFIG_UPDATE, _handle_core_update)
    entry.async_on_unload(unsub)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old entry titles to a neutral, English label."""
    if entry.title.lower().startswith("vacances scolaires"):
        hass.config_entries.async_update_entry(entry, title="French School Holidays")

    # Drop legacy language option/data; language now fixed to French
    new_data = dict(entry.data)
    new_options = dict(entry.options)
    changed = False
    for store in (new_data, new_options):
        if "language" in store:
            store.pop("language")
            changed = True
    if changed:
        hass.config_entries.async_update_entry(entry, data=new_data, options=new_options)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_sync_entity_names(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Ensure entity names match French friendly defaults."""
    registry = er.async_get(hass)

    def _name_for(sensor_type: str) -> str:
        return FRIENDLY_NAMES.get(sensor_type, sensor_type.replace("_", " ").title())

    for entity_id, entity_entry in list(registry.entities.items()):
        if entity_entry.config_entry_id != entry.entry_id:
            continue
        if entity_entry.platform != "fr_school_holidays":
            continue

        # Infer sensor type from entity_id suffix
        suffix = entity_id.split("fr_school_", 1)[-1]
        sensor_type = suffix

        new_name = _name_for(sensor_type)

        # Force-refresh the registry name to the localized value so it follows user language.
        if entity_entry.name != new_name:
            registry.async_update_entity(entity_id, name=new_name)
