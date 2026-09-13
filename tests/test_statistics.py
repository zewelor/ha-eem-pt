"""Tests for Energy statistic synchronization."""

from datetime import UTC, date, timedelta

import pytest

from custom_components.eem_online.coordinator.statistics import async_sync_statistics, period_start, statistic_id
from custom_components.eem_online.data import EemOnlineDailyConsumption
from homeassistant.components.recorder import Recorder
from homeassistant.components.recorder.statistics import get_last_statistics
from homeassistant.core import HomeAssistant
from homeassistant.helpers.recorder import get_instance


def _day(day: date, value: float) -> EemOnlineDailyConsumption:
    return EemOnlineDailyConsumption(day, period_start(day), value)


async def _wait_for_statistics(hass: HomeAssistant, recorder: Recorder) -> None:
    await hass.async_block_till_done()
    await hass.async_add_executor_job(recorder.block_till_done)


async def test_idempotent_corrections_and_gap_fill(recorder_mock: Recorder, hass: HomeAssistant) -> None:
    """Reimports replace periods and recalculate every later sum in the window."""
    contract = "456"
    first = [_day(date(2026, 9, 1), 1), _day(date(2026, 9, 3), 3)]
    await async_sync_statistics(hass, contract, date(2026, 9, 1), first)
    await _wait_for_statistics(hass, recorder_mock)
    await async_sync_statistics(hass, contract, date(2026, 9, 1), first)
    await _wait_for_statistics(hass, recorder_mock)
    await async_sync_statistics(
        hass,
        contract,
        date(2026, 9, 1),
        [_day(date(2026, 9, 2), 2), _day(date(2026, 9, 3), 2.5)],
    )
    await _wait_for_statistics(hass, recorder_mock)

    stats = await get_instance(hass).async_add_executor_job(
        get_last_statistics,
        hass,
        3,
        statistic_id(contract),
        False,
        {"state", "sum"},
    )
    rows = sorted(stats[statistic_id(contract)], key=lambda row: row["start"])
    assert [row["state"] for row in rows] == pytest.approx([1, 2, 2.5])
    assert [row["sum"] for row in rows] == pytest.approx([1, 3, 5.5])


async def test_sum_continues_after_long_gap_and_full_correction_window(
    recorder_mock: Recorder,
    hass: HomeAssistant,
) -> None:
    """A long missing period remains a gap without resetting the cumulative sum."""
    contract = "456"
    base_day = date(2026, 1, 1)
    window_start = date(2026, 2, 1)
    await async_sync_statistics(hass, contract, base_day, [_day(base_day, 10)])
    await _wait_for_statistics(hass, recorder_mock)

    full_window = [_day(window_start + timedelta(days=offset), 1) for offset in range(7)]
    await async_sync_statistics(hass, contract, window_start, full_window)
    await _wait_for_statistics(hass, recorder_mock)
    await async_sync_statistics(hass, contract, window_start, [_day(window_start + timedelta(days=3), 2)])
    await _wait_for_statistics(hass, recorder_mock)

    stats = await get_instance(hass).async_add_executor_job(
        get_last_statistics,
        hass,
        8,
        statistic_id(contract),
        False,
        {"state", "sum"},
    )
    rows = sorted(stats[statistic_id(contract)], key=lambda row: row["start"])
    assert [row["start"] for row in rows] == pytest.approx(
        [period_start(base_day).timestamp(), *(period_start(day.day).timestamp() for day in full_window)]
    )
    assert [row["state"] for row in rows] == pytest.approx([10, 1, 1, 1, 2, 1, 1, 1])
    assert [row["sum"] for row in rows] == pytest.approx([10, 11, 12, 13, 15, 16, 17, 18])


def test_madeira_dst_period_starts_are_hour_aligned() -> None:
    """Madeira civil midnights remain valid hourly starts across DST."""
    before = period_start(date(2026, 3, 29))
    after = period_start(date(2026, 3, 30))
    assert before.tzinfo is UTC
    assert before.minute == after.minute == 0
    assert (after - before).total_seconds() == 23 * 60 * 60
