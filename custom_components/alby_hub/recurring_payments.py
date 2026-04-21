"""Recurring / scheduled Lightning payment management.

Stores payment schedules persistently via HA's storage helper and fires
payments on the configured schedule using ``async_track_point_in_time``.

Supported schedules
-------------------
* daily     – fires once per day at the configured time
* weekly    – fires once per week on the configured day-of-week
* monthly   – fires once per month on the configured day-of-month
* quarterly – fires once per quarter (every 3 months) on the configured day

Each schedule entry carries:
    id          : unique str (UUID)
    label       : human-readable name
    recipient   : BOLT11 invoice OR Lightning address (user@domain)
    amount_sat  : int
    memo        : optional description
    frequency   : "daily" | "weekly" | "monthly" | "quarterly"
    hour        : int 0–23  (time of day to fire, default 8)
    minute      : int 0–59  (default 0)
    day_of_week : int 0–6   (Monday=0, only for weekly)
    day_of_month: int 1–28  (only for monthly / quarterly)
    start_date  : ISO date string "YYYY-MM-DD" (optional, defaults to today)
    end_date    : ISO date string "YYYY-MM-DD" (optional, None = no end)
    last_run    : ISO datetime string | None
    enabled     : bool
    entry_id    : config entry id
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    STORAGE_KEY_SCHEDULED_PAYMENTS,
    STORAGE_VERSION_SCHEDULED_PAYMENTS,
)

_LOGGER = logging.getLogger(__name__)

# ── constants ──────────────────────────────────────────────────────────────────
VALID_FREQUENCIES = ("daily", "weekly", "monthly", "quarterly")
_SCHEDULER_KEY = f"{DOMAIN}_scheduler"


class RecurringPaymentScheduler:
    """Manages scheduled Lightning payments for one HA instance."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._store: Store = Store(
            hass,
            STORAGE_VERSION_SCHEDULED_PAYMENTS,
            STORAGE_KEY_SCHEDULED_PAYMENTS,
        )
        # {schedule_id: cancel_callback}
        self._cancel_callbacks: dict[str, Any] = {}
        self._schedules: list[dict[str, Any]] = []

    # ── lifecycle ──────────────────────────────────────────────────────────────

    async def async_load(self) -> None:
        """Load schedules from storage and arm all enabled timers."""
        data = await self._store.async_load() or {}
        self._schedules = data.get("schedules", [])
        for schedule in self._schedules:
            if schedule.get("enabled", True):
                self._arm(schedule)
        _LOGGER.debug(
            "Loaded %d recurring payment schedule(s)", len(self._schedules)
        )

    async def async_unload(self) -> None:
        """Cancel all pending timers (called on integration unload)."""
        for cancel in list(self._cancel_callbacks.values()):
            cancel()
        self._cancel_callbacks.clear()

    # ── public CRUD API ────────────────────────────────────────────────────────

    async def async_create(self, entry_id: str, params: dict[str, Any]) -> dict[str, Any]:
        """Create and persist a new schedule.  Returns the created schedule."""
        schedule: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "label": str(params.get("label") or ""),
            "recipient": str(params["recipient"]),
            "amount_sat": int(params["amount_sat"]),
            "memo": str(params.get("memo") or ""),
            "frequency": str(params["frequency"]),
            "hour": int(params.get("hour", 8)),
            "minute": int(params.get("minute", 0)),
            "day_of_week": int(params.get("day_of_week", 0)),
            "day_of_month": int(params.get("day_of_month", 1)),
            "start_date": str(params.get("start_date") or date.today().isoformat()),
            "end_date": params.get("end_date") or None,
            "last_run": None,
            "enabled": True,
            "entry_id": entry_id,
        }
        _validate_schedule(schedule)
        self._schedules.append(schedule)
        await self._save()
        self._arm(schedule)
        _LOGGER.info(
            "Created recurring payment schedule '%s' (%s, %s sat)",
            schedule["label"],
            schedule["frequency"],
            schedule["amount_sat"],
        )
        return schedule

    def list_schedules(self, entry_id: str | None = None) -> list[dict[str, Any]]:
        """Return all (or entry-filtered) schedules as safe copies."""
        result = [
            dict(s)
            for s in self._schedules
            if entry_id is None or s.get("entry_id") == entry_id
        ]
        return result

    async def async_delete(self, schedule_id: str) -> bool:
        """Delete a schedule by id.  Returns True if found and removed."""
        before = len(self._schedules)
        self._schedules = [s for s in self._schedules if s["id"] != schedule_id]
        if len(self._schedules) == before:
            return False
        # Cancel timer if active
        cancel = self._cancel_callbacks.pop(schedule_id, None)
        if cancel:
            cancel()
        await self._save()
        return True

    async def async_toggle(self, schedule_id: str, enabled: bool) -> bool:
        """Enable or disable a schedule.  Returns True if found."""
        for schedule in self._schedules:
            if schedule["id"] == schedule_id:
                schedule["enabled"] = enabled
                if enabled:
                    self._arm(schedule)
                else:
                    cancel = self._cancel_callbacks.pop(schedule_id, None)
                    if cancel:
                        cancel()
                await self._save()
                return True
        return False

    # ── scheduling internals ───────────────────────────────────────────────────

    def _arm(self, schedule: dict[str, Any]) -> None:
        """Compute next fire time and register a point-in-time callback."""
        schedule_id = schedule["id"]
        # Cancel any existing timer for this id
        old_cancel = self._cancel_callbacks.pop(schedule_id, None)
        if old_cancel:
            old_cancel()

        next_fire = _next_fire_time(schedule)
        if next_fire is None:
            _LOGGER.debug(
                "Schedule '%s' has expired (end_date in the past); not arming.",
                schedule.get("label") or schedule_id,
            )
            return

        @callback
        def _fire(now: datetime) -> None:
            # Run the payment in a proper task
            self._hass.async_create_task(
                self._execute_and_rearm(schedule_id),
                name=f"alby_hub_recurring_{schedule_id}",
            )

        cancel = async_track_point_in_time(self._hass, _fire, next_fire)
        self._cancel_callbacks[schedule_id] = cancel
        _LOGGER.debug(
            "Schedule '%s' armed for %s",
            schedule.get("label") or schedule_id,
            next_fire.isoformat(),
        )

    async def _execute_and_rearm(self, schedule_id: str) -> None:
        """Execute a payment and rearm the timer for the next occurrence."""
        schedule = next((s for s in self._schedules if s["id"] == schedule_id), None)
        if schedule is None or not schedule.get("enabled", True):
            return

        _LOGGER.info(
            "Executing recurring payment '%s': %s sat → %s",
            schedule.get("label") or schedule_id,
            schedule["amount_sat"],
            schedule["recipient"],
        )

        try:
            await self._send_payment(schedule)
            schedule["last_run"] = dt_util.now().isoformat()
            await self._save()
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning(
                "Recurring payment '%s' failed: %s",
                schedule.get("label") or schedule_id,
                err,
            )

        # Rearm for next occurrence regardless of success/failure
        self._arm(schedule)

    async def _send_payment(self, schedule: dict[str, Any]) -> None:
        """Dispatch the actual payment using the active runtime for entry_id."""
        entry_id = schedule.get("entry_id")
        runtimes = self._hass.data.get(DOMAIN, {})
        if not runtimes:
            raise RuntimeError("No Alby Hub runtimes loaded")

        runtime = runtimes.get(entry_id) if entry_id else next(iter(runtimes.values()), None)
        if runtime is None:
            raise RuntimeError(f"Runtime not found for entry_id={entry_id}")

        from .nwc_client import async_nwc_request  # noqa: PLC0415

        result = await async_nwc_request(
            runtime.session,
            runtime.nwc_info,
            "pay_invoice",
            {"invoice": schedule["recipient"]},
        )
        if result is None or result.get("error"):
            err_detail = result.get("error") if result else "no response"
            raise RuntimeError(f"pay_invoice failed: {err_detail}")

    # ── persistence ────────────────────────────────────────────────────────────

    async def _save(self) -> None:
        await self._store.async_save({"schedules": self._schedules})


# ── helpers ────────────────────────────────────────────────────────────────────

def _next_fire_time(schedule: dict[str, Any]) -> datetime | None:
    """Calculate the next datetime at which the schedule should fire.

    Returns None when the schedule has expired (end_date is in the past).
    """
    now = dt_util.now()
    hour = schedule.get("hour", 8)
    minute = schedule.get("minute", 0)
    frequency = schedule.get("frequency", "monthly")

    # Respect start_date
    start_date_str = schedule.get("start_date")
    if start_date_str:
        try:
            start = date.fromisoformat(start_date_str)
        except (ValueError, TypeError):
            start = now.date()
    else:
        start = now.date()

    # Respect end_date
    end_date_str = schedule.get("end_date")
    end: date | None = None
    if end_date_str:
        try:
            end = date.fromisoformat(end_date_str)
        except (ValueError, TypeError):
            end = None

    # Candidate fire time: earliest possible based on last_run or start
    last_run_str = schedule.get("last_run")
    if last_run_str:
        try:
            last_run = datetime.fromisoformat(last_run_str)
            base_date = last_run.date()
        except (ValueError, TypeError):
            base_date = start
    else:
        # Never run: start from start_date
        base_date = start

    candidate = _advance(base_date, hour, minute, frequency, schedule)

    # If still in the past, advance once more
    if candidate <= now:
        candidate = _advance(candidate.date(), hour, minute, frequency, schedule)

    # Never fire before start_date
    if candidate.date() < start:
        # Compute first fire from start_date directly
        from_start = dt_util.as_local(datetime(start.year, start.month, start.day, hour, minute))
        if from_start > now:
            candidate = from_start
        else:
            candidate = _advance(start, hour, minute, frequency, schedule)

    # Check end_date
    if end is not None and candidate.date() > end:
        return None

    return candidate


def _advance(
    base: date, hour: int, minute: int, frequency: str, schedule: dict[str, Any]
) -> datetime:
    """Return the next fire datetime on or after *base* for the given frequency."""
    if frequency == "daily":
        candidate = dt_util.as_local(
            datetime(base.year, base.month, base.day, hour, minute)
        )
        now = dt_util.now()
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate

    if frequency == "weekly":
        day_of_week = int(schedule.get("day_of_week", 0))  # 0=Monday
        # Find next occurrence of target weekday on or after base
        days_ahead = (day_of_week - base.weekday()) % 7
        target_date = base + timedelta(days=days_ahead)
        candidate = dt_util.as_local(
            datetime(target_date.year, target_date.month, target_date.day, hour, minute)
        )
        now = dt_util.now()
        if candidate <= now:
            candidate += timedelta(weeks=1)
        return candidate

    if frequency in ("monthly", "quarterly"):
        months_step = 1 if frequency == "monthly" else 3
        day = int(schedule.get("day_of_month", 1))
        # Clamp to 28 for safety across all months
        day = max(1, min(day, 28))
        candidate_date = _next_month_day(base, day, months_step)
        candidate = dt_util.as_local(
            datetime(candidate_date.year, candidate_date.month, candidate_date.day, hour, minute)
        )
        now = dt_util.now()
        if candidate <= now:
            candidate_date = _next_month_day(candidate_date, day, months_step)
            candidate = dt_util.as_local(
                datetime(candidate_date.year, candidate_date.month, candidate_date.day, hour, minute)
            )
        return candidate

    # Fallback: daily
    return dt_util.as_local(datetime(base.year, base.month, base.day, hour, minute)) + timedelta(days=1)


def _next_month_day(base: date, target_day: int, months_step: int) -> date:
    """Return the first date >= *base* that is the *target_day* of a month
    occurring on or after *base*, stepping by *months_step* months."""
    year, month = base.year, base.month
    candidate = date(year, month, target_day)
    if candidate < base:
        # Advance by months_step months
        month += months_step
        year += (month - 1) // 12
        month = ((month - 1) % 12) + 1
        candidate = date(year, month, target_day)
    return candidate


def _validate_schedule(schedule: dict[str, Any]) -> None:
    if schedule["frequency"] not in VALID_FREQUENCIES:
        raise ValueError(
            f"Invalid frequency '{schedule['frequency']}'. "
            f"Must be one of: {', '.join(VALID_FREQUENCIES)}"
        )
    if schedule["amount_sat"] < 1:
        raise ValueError("amount_sat must be ≥ 1")
    if not schedule["recipient"].strip():
        raise ValueError("recipient must not be empty")
    if not (0 <= schedule["hour"] <= 23):
        raise ValueError("hour must be 0–23")
    if not (0 <= schedule["minute"] <= 59):
        raise ValueError("minute must be 0–59")


# ── global accessor ────────────────────────────────────────────────────────────

def get_scheduler(hass: HomeAssistant) -> RecurringPaymentScheduler | None:
    """Return the global scheduler instance, if already initialised."""
    return hass.data.get(_SCHEDULER_KEY)


async def async_setup_scheduler(hass: HomeAssistant) -> RecurringPaymentScheduler:
    """Initialise (or return existing) scheduler and load persisted schedules."""
    existing = hass.data.get(_SCHEDULER_KEY)
    if existing is not None:
        return existing
    scheduler = RecurringPaymentScheduler(hass)
    hass.data[_SCHEDULER_KEY] = scheduler
    await scheduler.async_load()
    return scheduler


async def async_unload_scheduler(hass: HomeAssistant) -> None:
    """Unload the scheduler (call when last entry is removed)."""
    scheduler = hass.data.pop(_SCHEDULER_KEY, None)
    if scheduler is not None:
        await scheduler.async_unload()
