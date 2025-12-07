"""Config flow for French School Vacation Times."""

from __future__ import annotations

from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_RESOURCES
from homeassistant.core import HomeAssistant, callback
import homeassistant.helpers.config_validation as cv

from . import DOMAIN
from .sensor import API_URL, DEFAULT_TIMEZONE, OPT_TIMEZONE, SENSOR_TYPES, VACATION_ZONE


def _validate_timezone(value: str) -> str:
    """Validate that the provided timezone exists."""
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise vol.Invalid("invalid_timezone") from exc
    return value


def _default_timezone(hass: HomeAssistant) -> str:
    return hass.config.time_zone or DEFAULT_TIMEZONE


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the component."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial user step of the config flow."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                user_input[OPT_TIMEZONE] = _validate_timezone(
                    user_input.get(OPT_TIMEZONE, _default_timezone(self.hass))
                )
            except vol.Invalid:
                errors[OPT_TIMEZONE] = "invalid_timezone"

            if not errors:
                # Use a stable, generic title so it doesn't become stale when zone changes later.
                return self.async_create_entry(title="Vacances scolaires", data=user_input)

        data_schema = vol.Schema(
            {
                vol.Required(VACATION_ZONE): str,
                vol.Required(API_URL, default="https://data.education.gouv.fr/api/explore/v2.1/catalog/datasets/fr-en-calendrier-scolaire/records?limit=99&lang=fr&timezone=Europe%2FParis&refine=start_date:\"{year}\"&refine=zones:\"{zone}\"&refine=population:\"Élèves\"&refine=population:\"-\""):
                    str,
                vol.Required(
                    CONF_RESOURCES,
                    default=list(SENSOR_TYPES.keys()),
                ): cv.multi_select(list(SENSOR_TYPES.keys())),
                vol.Optional(
                    OPT_TIMEZONE,
                    default=_default_timezone(self.hass),
                ): str,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow handler."""
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for the component."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Handle the options flow."""
        errors: dict[str, str] = {}
        current_tz = self.config_entry.options.get(
            OPT_TIMEZONE,
            self.config_entry.data.get(OPT_TIMEZONE, _default_timezone(self.hass)),
        )
        current_zone = self.config_entry.options.get(
            VACATION_ZONE,
            self.config_entry.data.get(VACATION_ZONE, ""),
        )

        if user_input is not None:
            try:
                tz_value = _validate_timezone(user_input.get(OPT_TIMEZONE, current_tz))
            except vol.Invalid:
                errors[OPT_TIMEZONE] = "invalid_timezone"
            else:
                zone_value = user_input.get(VACATION_ZONE, current_zone)
                return self.async_create_entry(
                    title="",
                    data={
                        OPT_TIMEZONE: tz_value,
                        VACATION_ZONE: zone_value,
                    },
                )

        data_schema = vol.Schema(
            {
                vol.Required(VACATION_ZONE, default=current_zone): str,
                vol.Required(OPT_TIMEZONE, default=current_tz): str,
            }
        )
        return self.async_show_form(
            step_id="init", data_schema=data_schema, errors=errors
        )
