"""Import EEM daily consumption into Home Assistant long-term statistics."""

from datetime import UTC, date, datetime, time

from custom_components.eem_online.const import DOMAIN, MADEIRA_TIME_ZONE
from custom_components.eem_online.data import EemOnlineDailyConsumption
from homeassistant.components.recorder.models import StatisticData, StatisticMeanType, StatisticMetaData
from homeassistant.components.recorder.statistics import async_add_external_statistics, get_last_statistics
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.recorder import get_instance


def statistic_id(contract: str) -> str:
    """Return the stable Energy statistic ID for a contract."""
    return f"{DOMAIN}:{contract}_consumption"


def period_start(day: date) -> datetime:
    """Convert an EEM civil day start in Madeira to UTC."""
    return datetime.combine(day, time.min, tzinfo=MADEIRA_TIME_ZONE).astimezone(UTC)


async def async_sync_statistics(
    hass: HomeAssistant,
    contract: str,
    window_start: date,
    fresh: list[EemOnlineDailyConsumption],
) -> list[EemOnlineDailyConsumption]:
    """Merge the rolling EEM window, recalculate sums, and import it."""
    stat_id = statistic_id(contract)
    instance = get_instance(hass)
    stored_result = await instance.async_add_executor_job(
        get_last_statistics,
        hass,
        8,
        stat_id,
        False,
        {"state", "sum"},
    )
    stored = stored_result.get(stat_id, [])

    base_sum = 0.0
    base_day: date | None = None
    values: dict[date, float] = {}
    for row in stored:
        if (start_timestamp := row.get("start")) is None:
            continue
        day = datetime.fromtimestamp(start_timestamp, UTC).astimezone(MADEIRA_TIME_ZONE).date()
        state = row.get("state")
        row_sum = row.get("sum")
        if day < window_start and row_sum is not None and (base_day is None or day > base_day):
            base_day = day
            base_sum = float(row_sum)
        elif day >= window_start and state is not None:
            values[day] = float(state)

    values.update({item.day: item.value for item in fresh})
    merged = [EemOnlineDailyConsumption(day, period_start(day), value) for day, value in sorted(values.items())]
    if not merged:
        return []

    running_sum = base_sum
    statistics: list[StatisticData] = []
    for item in merged:
        running_sum += item.value
        statistics.append(StatisticData(start=item.start, state=item.value, sum=running_sum))

    metadata: StatisticMetaData = {
        "mean_type": StatisticMeanType.NONE,
        "has_sum": True,
        "name": f"EEM Online {contract} consumption",
        "source": DOMAIN,
        "statistic_id": stat_id,
        "unit_class": "energy",
        "unit_of_measurement": UnitOfEnergy.KILO_WATT_HOUR,
    }
    async_add_external_statistics(hass, metadata, statistics)
    return merged
