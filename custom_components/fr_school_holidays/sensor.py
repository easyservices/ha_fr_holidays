"""Platform to get if is school vacation for Home Assistant.

Using the French Administration Open API to retrieve the school holidays.
"""

from __future__ import annotations

from datetime import datetime
import json
import logging
from pathlib import Path
from zoneinfo import ZoneInfo

import aiofiles
import aiohttp
from aiohttp import ClientTimeout
import voluptuous as vol

from homeassistant.components.sensor import (
    ENTITY_ID_FORMAT,
    PLATFORM_SCHEMA as SENSOR_PLATFORM_SCHEMA,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_RESOURCES
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import DeviceInfo, Entity, async_generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType, StateType

__version__ = "1.2.0"

DOMAIN = "fr_school_holidays"

_LOGGER = logging.getLogger(__name__)

SENSOR_PREFIX: str = "fr_school_"
VACATION_ZONE: str = "vacation_zone"
API_URL: str = "api_url"
OPT_TIMEZONE: str = "timezone"

DEFAULT_TIMEZONE = "Europe/Paris"
REQUEST_TIMEOUT = 20  # seconds
AIOHTTP_TIMEOUT = ClientTimeout(total=REQUEST_TIMEOUT)

# French-only strings (keys stay English in code)
FR_STRINGS: dict[str, str] = {
    "summary_on_holidays": "Vacances scolaires : {label} (zone {zone}) jusqu'au {end}",
    "summary_weekend_holiday": "Week-end pendant les vacances : {label} jusqu'au {end}",
    "summary_weekend_school": "Week-end (hors vacances)",
    "summary_school_day": "Journée de classe",
    "summary_next_holiday": "Prochaines vacances : {label} du {start} au {end}",
    "not_updated": "Non encore mis à jour",
    "at_school": "Aux études",
    "weekend_prefix": "En week-end, ",
    "weekend_not_holiday": "En week-end mais pas en vacances scolaires",
    "name_is_vacation_time": "Vacances scolaires",
    "name_is_weekend_time": "Week-end",
    "name_is_school_day": "Journée de classe",
    "name_summary": "Résumé vacances scolaires",
}

FRIENDLY_NAMES = {
    "is_vacation_time": FR_STRINGS["name_is_vacation_time"],
    "is_weekend_time": FR_STRINGS["name_is_weekend_time"],
    "is_school_day": FR_STRINGS["name_is_school_day"],
    "summary": FR_STRINGS["name_summary"],
}

SENSOR_TYPES: dict = {
    "is_vacation_time": ["mdi:school", "is_vacation_time"],
    "is_weekend_time": ["mdi:school", "is_weekend_time"],
    "is_school_day": ["mdi:calendar-check", "is_school_day"],
    "summary": ["mdi:rename-box", "summary"],
}

SENSOR_PLATFORM_SCHEMA = SENSOR_PLATFORM_SCHEMA.extend(
    {
        vol.Required(VACATION_ZONE): cv.string,
        vol.Required(API_URL): cv.string,
        vol.Required(CONF_RESOURCES, default=[]): vol.All(
            cv.ensure_list, [vol.In(SENSOR_TYPES)]
        ),
        vol.Optional(OPT_TIMEZONE, default=None): cv.string,
    }
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the fr school holidays config sensors."""
    vacation_zone = str(config.get(VACATION_ZONE, ""))  # ensure str for type checkers
    api_url = str(config.get(API_URL, ""))  # ensure str for type checkers
    tz_name = config.get(OPT_TIMEZONE) or hass.config.time_zone or DEFAULT_TIMEZONE
    entities: list[SchoolHolidays] = []
    for resource in config[CONF_RESOURCES]:
        sensor_type = resource.lower()
        if sensor_type not in SENSOR_TYPES:
            SENSOR_TYPES[sensor_type] = [sensor_type.title(), "", "mdi:flash"]
        entities.append(
            SchoolHolidays(hass, sensor_type, vacation_zone, api_url, tz_name)
        )
    async_add_entities(entities, False)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up sensors from config entry options."""
    data = entry.data
    options = entry.options
    vacation_zone = str(options.get(VACATION_ZONE) or data.get(VACATION_ZONE) or "")
    api_url = str(data.get(API_URL, ""))
    resources = data.get(CONF_RESOURCES, list(SENSOR_TYPES))
    tz_name = options.get(OPT_TIMEZONE) or data.get(OPT_TIMEZONE) or hass.config.time_zone or DEFAULT_TIMEZONE

    entities: list[SchoolHolidays] = []
    for resource in resources:
        sensor_type = resource.lower()
        if sensor_type not in SENSOR_TYPES:
            SENSOR_TYPES[sensor_type] = [sensor_type.title(), "", "mdi:flash"]
        entities.append(SchoolHolidays(hass, sensor_type, vacation_zone, api_url, tz_name))

    async_add_entities(entities, False)


async def fetch(session: aiohttp.ClientSession, url: str, ctx: str = "") -> str:
    """Fetch the content of a URL using an aiohttp session with basic guards."""

    try:
        async with session.get(url, timeout=AIOHTTP_TIMEOUT) as response:
            if response.status >= 400:
                _LOGGER.error("%s HTTP %s when fetching %s", ctx, response.status, url)
                return ""
            return await response.text()
    except TimeoutError as err:
        _LOGGER.error("%s timeout while fetching %s: %s", ctx, url, err)
        return ""
    except aiohttp.ClientError as error:
        _LOGGER.error("%s client error while fetching %s: %s", ctx, url, error)
    return ""


class SchoolHolidays(Entity):
    """Representation of a french school vacation."""

    def __init__(
        self,
        hass: HomeAssistant,
        sensor_type: str,
        vacation_zone: str,
        api_url: str,
        tz_name: str | None = None,
    ) -> None:
        """Initialize the school holiday sensor entity."""
        self.hass = hass
        self.type = sensor_type
        self._config_path = Path(
            hass.config.path("custom_components", "fr_school_holidays")
        )
        self.vacation_zone = vacation_zone
        self.api_url = api_url
        chosen_tz = tz_name or hass.config.time_zone or DEFAULT_TIMEZONE
        try:
            self._tz = ZoneInfo(chosen_tz)
            self._tz_name = chosen_tz
        except Exception:  # noqa: BLE001
            _LOGGER.warning("%s Invalid timezone %s, falling back to %s", self._ctx(), chosen_tz, DEFAULT_TIMEZONE)
            self._tz = ZoneInfo(DEFAULT_TIMEZONE)
            self._tz_name = DEFAULT_TIMEZONE
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT,
            "_".join([SENSOR_PREFIX, SENSOR_TYPES[self.type][1]]),
            hass=hass,
        )
        self._state: StateType | None = None
        self._summary_name: str | None = None
        self._vacation_status: bool | None = None
        self._weekend_status: bool | None = None
        self._school_day_status: bool | None = None
        self._next_holiday_start: datetime | None = None
        self._next_holiday_end: datetime | None = None
        self._school_db: list[dict] = []

    def _ctx(self) -> str:
        return (
            f"[zone={self.vacation_zone} tz={self._tz_name} sensor={self.type}]"
        )

    def _fr(self, key: str, **kwargs) -> str:
        """Return a French string formatted with kwargs."""
        template = FR_STRINGS.get(key, key)
        try:
            return template.format(**kwargs)
        except (KeyError, AttributeError, ValueError):
            return template

    @property
    def get_db_filename(self) -> Path:
        """Return path to cache file for current year and drop previous year cache."""
        cur_year = datetime.now(tz=self._tz).year
        last_year = cur_year - 1
        previous_file = self._config_path / f"fr_school_data_{last_year}.json"
        current_file = self._config_path / f"fr_school_data_{cur_year}.json"
        if previous_file.is_file():
            try:
                previous_file.unlink()
            except OSError as error:
                _LOGGER.error("Error removing previous file %s with err %s", previous_file, error)
            except Exception:
                _LOGGER.exception("Unexpected error removing %s", previous_file)
        return current_file

    @property
    def api_fr(self) -> str:
        """Manage the API French School Holidays."""
        url = str(self.api_url).replace(
            "{year}", str(datetime.now(tz=self._tz).year)
        )
        url = url.replace("{zone}", self.vacation_zone)
        _LOGGER.debug("%s resolved api url: %s", self._ctx(), url)
        return url

    @property
    def name(self) -> str:
        """Return a human friendly name for the sensor."""
        return str(FRIENDLY_NAMES.get(self.type, SENSOR_TYPES[self.type][1].replace("_", " ").title()))

    @property
    def icon(self) -> str:
        """Icon to use in the frontend, if any."""
        return SENSOR_TYPES[self.type][0]

    @property
    def state(self) -> StateType:
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, str | int | None]:
        """Return the extra state attributes."""
        attrs: dict[str, str | int | None] = {
            "API_URL": self.api_fr,
            "timezone": self._tz_name,
        }
        if self._next_holiday_start:
            attrs["next_holiday_start"] = self._next_holiday_start.date().isoformat()
        if self._next_holiday_end:
            attrs["next_holiday_end"] = self._next_holiday_end.date().isoformat()
        if self._next_holiday_start:
            attrs["days_until_next_holiday"] = max(
                0, (self._next_holiday_start.date() - datetime.now(tz=self._tz).date()).days
            )
        return attrs

    @property
    def device_info(self) -> DeviceInfo:
        """Return Home Assistant device metadata for this sensor."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.vacation_zone}"), (DOMAIN, "fr_school_holidays")},
            manufacturer="Ministere de l'Education (open data)",
            model=f"Zone {self.vacation_zone}",
            name="Vacances scolaires France",
        )

    async def async_update(self) -> None:
        """Update our sensor state."""

        db_filename = self.get_db_filename
        self._config_path.mkdir(parents=True, exist_ok=True)

        if not self._school_db:
            if db_filename.is_file():
                try:
                        async with aiofiles.open(db_filename, encoding="utf8") as jsonfile:
                            file_content = await jsonfile.read()
                            self._school_db = json.loads(file_content)
                            if not isinstance(self._school_db, list):
                                raise TypeError("results is not list")
                        _LOGGER.debug("%s cache hit: %s (%s records)", self._ctx(), db_filename, len(self._school_db))
                except (FileNotFoundError, OSError):
                    _LOGGER.error("%s error reading cache file %s", self._ctx(), db_filename)
                except json.JSONDecodeError:
                    _LOGGER.error("%s invalid JSON in %s, refetching", self._ctx(), db_filename)
                    try:
                        db_filename.unlink(missing_ok=True)
                    except OSError:
                        _LOGGER.warning("%s failed to remove corrupted cache %s", self._ctx(), db_filename)

            if not self._school_db:
                try:
                    async with aiohttp.ClientSession() as session:
                        content = await fetch(session, self.api_fr, self._ctx())
                        if not content:
                            return
                        data = json.loads(content)
                        results = data.get("results") if isinstance(data, dict) else None
                        if not isinstance(results, list):
                            _LOGGER.error("%s unexpected API payload, missing 'results'", self._ctx())
                            return
                        self._school_db = results
                        async with aiofiles.open(
                            db_filename,
                            "w",
                            encoding="utf-8",
                        ) as outfile:
                            await outfile.write(
                                json.dumps(
                                    self._school_db,
                                    skipkeys=False,
                                    ensure_ascii=False,
                                    indent=4,
                                    separators=None,
                                    default=None,
                                    sort_keys=True,
                                )
                            )
                            _LOGGER.debug(
                                "%s cached %s records to %s", self._ctx(), len(self._school_db), db_filename
                            )
                except OSError as error:  # Catch specific file I/O errors
                    _LOGGER.error("%s error saving fr school vacation time DB: %s", self._ctx(), error)
                except json.JSONDecodeError as error:  # Catch JSON errors
                    _LOGGER.error("%s error decoding JSON data: %s", self._ctx(), error)

        if self._school_db:
            await self._update_values()

    async def _update_values(self) -> None:
        """Update the entity state."""
        await self.is_vacation()
        type_to_func = {
            "is_vacation_time": self.get_vacation_status,
            "is_weekend_time": self.get_weekend_status,
            "is_school_day": self.get_school_day_status,
            "summary": self.get_summary_name,
        }
        self._state = await type_to_func[self.type]()
        self.async_write_ha_state()

    async def is_vacation(self) -> None:
        """Check if it is a school day."""
        now = datetime.now(tz=self._tz).date()
        self._weekend_status = False
        self._vacation_status = False
        self._school_day_status = None
        self._summary_name = self._fr("not_updated")
        self._next_holiday_start = None
        self._next_holiday_end = None

        # yearly rollover: if cache contains previous-year data, force refresh
        if self._school_db:
            first = self._school_db[0]
            try:
                first_year = datetime.fromisoformat(str(first["start_date"])).year
                if first_year != now.year:
                    self._school_db = []
                    _LOGGER.info("%s cache year %s differs from current %s; refreshing", self._ctx(), first_year, now.year)
                    return await self.async_update()
            except Exception:  # noqa: BLE001
                _LOGGER.debug("%s unable to determine cache year, continuing with existing data", self._ctx())

        for extract_data in sorted(self._school_db, key=lambda item: item.get("start_date", "")):
            start_dt = datetime.fromisoformat(str(extract_data["start_date"])).astimezone(self._tz)
            end_dt = datetime.fromisoformat(str(extract_data["end_date"])).astimezone(self._tz)
            start = start_dt.date()
            end = end_dt.date()
            if start <= now <= end:
                self._next_holiday_start = start_dt
                self._next_holiday_end = end_dt
                self._summary_name = self._fr(
                    "summary_on_holidays",
                    label=str(extract_data["description"]),
                    zone=str(extract_data["zones"]),
                    end=end_dt.date().isoformat(),
                )
                self._vacation_status = True
                _LOGGER.debug("%s matched vacation period %s - %s", self._ctx(), start, end)
                break
            if start > now and self._next_holiday_start is None:
                self._next_holiday_start = start_dt
                self._next_holiday_end = end_dt
                self._summary_name = self._fr(
                    "summary_next_holiday",
                    label=str(extract_data["description"]),
                    start=start_dt.date().isoformat(),
                    end=end_dt.date().isoformat(),
                )
                _LOGGER.debug("%s next holiday starts %s ends %s", self._ctx(), start, end)

        if self._vacation_status is False:
            self._summary_name = self._fr("summary_school_day")

        # we are either saturday or sunday
        if now.isoweekday() > 5:
            if self._vacation_status is True:
                self._summary_name = self._fr(
                    "summary_weekend_holiday",
                    label=self._summary_name or "",
                    end=self._next_holiday_end.date().isoformat() if self._next_holiday_end else "",
                )
            else:
                self._summary_name = self._fr("summary_weekend_school")
            self._weekend_status = True

        self._school_day_status = not self._vacation_status and not self._weekend_status
        return None

    async def get_summary_name(self) -> str:
        """Return the state of the sensor."""
        if self._summary_name is None:
            self._summary_name = "Error"
        return str(self._summary_name)

    async def get_vacation_status(self) -> bool:
        """Return the state of the sensor."""
        if self._vacation_status is None:
            self._vacation_status = False
        return bool(self._vacation_status)

    async def get_weekend_status(self) -> bool:
        """Return the state of the sensor."""
        if self._weekend_status is None:
            self._weekend_status = False
        return bool(self._weekend_status)

    async def get_school_day_status(self) -> bool:
        """Return true when not weekend and not vacation."""
        if self._school_day_status is None:
            self._school_day_status = False
        return bool(self._school_day_status)
