"""Platform to get if is school vacation for Home Assistant.

Using the French Administration Open API to retrieve the school holidays.
"""

from datetime import datetime
import json
import logging
import os

import aiofiles
import aiohttp
import voluptuous as vol

from homeassistant.components.sensor import (
    ENTITY_ID_FORMAT,
    PLATFORM_SCHEMA as SENSOR_PLATFORM_SCHEMA,
)
from homeassistant.const import CONF_RESOURCES
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity, async_generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType, StateType

__version__ = "1.0.0"

_LOGGER = logging.getLogger(__name__)

SENSOR_PREFIX: str = "fr_school_"
VACATION_ZONE: str = "vacation_zone"
API_URL: str = "api_url"

SENSOR_TYPES: dict = {
    "is_vacation_time": ["mdi:school", "is_vacation_time"],
    "is_weekend_time": ["mdi:school", "is_weekend_time"],
    "summary": ["mdi:rename-box", "summary"],
}

SENSOR_PLATFORM_SCHEMA = SENSOR_PLATFORM_SCHEMA.extend(
    {
        vol.Required(VACATION_ZONE): cv.string,
        vol.Required(API_URL): cv.string,
        vol.Required(CONF_RESOURCES, default=[]): vol.All(
            cv.ensure_list, [vol.In(SENSOR_TYPES)]
        ),
    }
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the fr school holidays config sensors."""
    vacation_zone = config.get(VACATION_ZONE)
    api_url = config.get(API_URL)
    entities = []

    for resource in config[CONF_RESOURCES]:
        sensor_type = resource.lower()
        if sensor_type not in SENSOR_TYPES:
            SENSOR_TYPES[sensor_type] = [sensor_type.title(), "", "mdi:flash"]
        entities.append(SchoolHolidays(hass, sensor_type, vacation_zone, api_url))
    async_add_entities(entities, False)


# pylint: disable=abstract-method


async def fetch(session: aiohttp.ClientSession, url: str) -> str:
    """Fetch the content of a URL using an aiohttp session.

    Args:
        session: An aiohttp ClientSession object.
        url: The URL to fetch.

    Returns:
        The content of the URL as a string.  Returns an empty string if there's an error.

    Raises:
        aiohttp.ClientError: If there's an error during the HTTP request.

    """
    async with session.get(url) as response:
        return await response.text()


class SchoolHolidays(Entity):
    """Representation of a french school vacation."""

    def __init__(
        self, hass: HomeAssistant, sensor_type: [str], vacation_zone: str, api_url: str
    ) -> None:
        """Initialize the sensor."""
        self.type = sensor_type
        self._config_path = (
            hass.config.path() + "/custom_components/fr_school_holidays/"
        )
        self.vacation_zone = vacation_zone
        self.api_url = api_url
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT,
            "_".join([SENSOR_PREFIX, SENSOR_TYPES[self.type][1]]),
            hass=hass,
        )
        self._state = None
        self._summary_name = None
        self._vacation_status = None
        self._weekend_status = None
        self._school_db = []

    @property
    def get_db_filename(self) -> str:
        """Manage the DB French School Holidays."""
        cur_year = datetime.now().year
        last_year = cur_year - 1
        previous_file_name = os.path.join(self._config_path, f"fr_school_data_{last_year}.json")  # noqa: PTH118
        current_file_name = os.path.join(self._config_path, f"fr_school_data_{cur_year}.json")  # noqa: PTH118
        if os.path.isfile(previous_file_name):  # noqa: PTH113
            try:
                os.remove(previous_file_name)  # noqa: PTH107
            except OSError as error:
                _LOGGER.error("Error removing previous file %s with err %s", previous_file_name, error)
            except Exception as error:
                _LOGGER.exception(error)  # noqa: TRY401
        return current_file_name

    @property
    def api_fr(self) -> str:
        """Manage the API French School Holidays."""
        url = str(self.api_url).replace("{year}", str(datetime.now().year))
        url = url.replace("{zone}", self.vacation_zone)
        _LOGGER.debug("url: %s", url)
        return url

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return SENSOR_PREFIX + SENSOR_TYPES[self.type][1]

    @property
    def icon(self) -> str:
        """Icon to use in the frontend, if any."""
        return SENSOR_TYPES[self.type][0]

    @property
    def state(self) -> StateType:
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return the extra state attributes."""
        return {
            "API_URL": self.api_url,
        }

    """
    @property
    def device_info(self) -> DeviceInfo:
        # Return device registry information for this entity.
        return DeviceInfo(
            identifiers={(DOMAIN, self._device.id)},
            manufacturer="Abode",
            model=self._device.type,
            name=self._device.name,
        )
    """

    async def async_update(self) -> None:
        """Update our sensor state."""

        db_filename = self.get_db_filename

        if not self._school_db:
            if os.path.isfile(db_filename):  # noqa: PTH113
                try:
                    async with aiofiles.open(db_filename, encoding='utf8') as jsonfile:
                        # Await the coroutine
                        file_content = await jsonfile.read()
                        # Load the JSON data
                        self._school_db = json.loads(file_content)
                        _LOGGER.debug(
                            "Read fr school vacation time from cache: %s", db_filename
                        )
                except FileNotFoundError:
                    _LOGGER.error("Error: File '{}' not found.".format(db_filename))  # noqa: G001, UP032
                except json.JSONDecodeError:
                    _LOGGER.error("Error: Invalid JSON in '{}'.".format(db_filename))  # noqa: G001, UP032
            else:
                try:
                    async with aiohttp.ClientSession() as session:
                        content = await fetch(session, self.api_fr)
                        data = json.loads(content)
                        self._school_db = data["results"]
                        # saving to cache file
                        async with aiofiles.open(
                            db_filename,
                            "w",
                            encoding="utf-8",
                        ) as outfile:
                            temp_data = json.dumps(
                                self._school_db,
                                skipkeys=False,
                                ensure_ascii=False,
                                indent=4,
                                separators=None,
                                default=None,
                                sort_keys=True,
                            )
                            await outfile.write(temp_data)
                            _LOGGER.debug(
                                "fr school vacation time DB has been saved as a file: %s", db_filename
                            )
                        await self._update_values()
                except OSError as e:  # Catch specific file I/O errors
                    _LOGGER.error("Error saving fr school vacation time DB: %s", e)
                except json.JSONDecodeError as e: #Catch JSON errors
                    _LOGGER.error("Error decoding JSON data: %s", e)

        else:
            await self._update_values()

    async def _update_values(self) -> None:
        """Update the entity state."""
        await self.is_vacation()
        type_to_func = {
            "is_vacation_time": self.get_vacation_status,
            "is_weekend_time": self.get_weekend_status,
            "summary": self.get_summary_name,
        }
        self._state = await type_to_func[self.type]()
        self.async_write_ha_state()

    async def is_vacation(self) -> None:
        """Check if it is a school day."""
        now = datetime.today().date()
        self._weekend_status = "False"
        self._vacation_status = "False"
        self._summary_name = "Non encore mis à jour"

        for extract_data in self._school_db:
            # print(extract_data)
            date_pattern = "%Y-%m-%dT%H:%M:%S%z"
            start = datetime.strptime(
                str(extract_data["start_date"]), date_pattern
            ).date()
            end = datetime.strptime(str(extract_data["end_date"]), date_pattern).date()
            if now >= start and now <= end:
                self._summary_name = (
                    str(extract_data["description"])
                    + " "
                    + str(extract_data["annee_scolaire"])
                    + " "
                    + str(extract_data["zones"])
                )
                self._vacation_status = "True"
                self._summary_name = "En vacances scolaires"
                break

        if self._vacation_status == "False":
            self._summary_name = "Aux études"

        # we are either saturday or sunday
        if now.isoweekday() > 5:
            if self._vacation_status == "True":
                self._summary_name = "En week-end et vacances scolaires"
            else:
                self._summary_name = "En week-end mais pas en vacances scolaires"
            self._weekend_status = "True"

    async def get_summary_name(self) -> str:
        """Return the state of the sensor."""
        if self._summary_name is None:
            self._summary_name = "Error"
        return str(self._summary_name)

    async def get_vacation_status(self) -> str:
        """Return the state of the sensor."""
        if self._vacation_status is None:
            self._vacation_status = "Error"
        return str(self._vacation_status)

    async def get_weekend_status(self) -> str:
        """Return the state of the sensor."""
        if self._weekend_status is None:
            self._weekend_status = "Error"
        return str(self._weekend_status)
