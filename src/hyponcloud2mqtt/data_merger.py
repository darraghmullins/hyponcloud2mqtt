from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _to_int(value: Any) -> int | None:
    """
    Safely convert a value to an integer.
    """
    try:
        if value is None or value == "":
            return None

        return int(float(value))

    except (ValueError, TypeError):
        return None


def _to_float(value: Any) -> float | None:
    """
    Safely convert a value to a float.
    """
    try:
        if value is None or value == "":
            return None

        return float(value)

    except (ValueError, TypeError):
        return None


def merge_api_data(
    monitor: dict | None,
    production: dict | None,
    status: dict | None,
    energy: dict | None = None,
) -> dict:
    """
    Merge Hypon Cloud API responses into one MQTT payload.

    monitor:
        /v2/plant/{system_id}/monitor?refresh=true

    production:
        /v2/plant/{system_id}/production2

    status:
        /v2/plant/{system_id}/status

    energy:
        /v2/plant/{system_id}/energy2
    """

    merged = {}

    def add_if_not_none(
        key: str,
        value: Any,
    ) -> None:

        if value is not None:
            merged[key] = value

    # =========================================================
    # MONITOR
    # =========================================================

    if monitor and "data" in monitor:

        data = monitor["data"]

        # Existing fields
        add_if_not_none(
            "percent",
            _to_float(data.get("percent")),
        )

        add_if_not_none(
            "w_cha",
            _to_int(data.get("w_cha")),
        )

        add_if_not_none(
            "power_pv",
            _to_int(data.get("power_pv")),
        )

        # Current power-flow values
        add_if_not_none(
            "meter_power",
            _to_int(data.get("meter_power")),
        )

        add_if_not_none(
            "power_load",
            _to_int(data.get("power_load")),
        )

        add_if_not_none(
            "soc",
            _to_float(data.get("soc")),
        )

        # Some installations may expose this separately.
        add_if_not_none(
            "power_bat",
            _to_int(data.get("power_bat")),
        )

        # Monitor energy counters
        add_if_not_none(
            "e_today",
            _to_float(data.get("e_today")),
        )

        add_if_not_none(
            "e_month",
            _to_float(data.get("e_month")),
        )

        add_if_not_none(
            "e_year",
            _to_float(data.get("e_year")),
        )

        add_if_not_none(
            "e_total",
            _to_float(data.get("e_total")),
        )

        # Environmental information
        add_if_not_none(
            "total_tree",
            _to_float(data.get("total_tree")),
        )

        add_if_not_none(
            "total_co2",
            _to_float(data.get("total_co2")),
        )

        add_if_not_none(
            "total_diesel",
            _to_float(data.get("total_diesel")),
        )

        add_if_not_none(
            "warning",
            data.get("warning"),
        )

        add_if_not_none(
            "invcount",
            _to_int(data.get("invcount")),
        )

    # =========================================================
    # PRODUCTION2
    # =========================================================

    if production and "data" in production:

        data = production["data"]

        # Preserve existing hyponcloud2mqtt fields.
        add_if_not_none(
            "today_generation",
            _to_float(
                data.get("today_generation")
            ),
        )

        add_if_not_none(
            "month_generation",
            _to_float(
                data.get("month_generation")
            ),
        )

        add_if_not_none(
            "year_generation",
            _to_float(
                data.get("year_generation")
            ),
        )

        add_if_not_none(
            "total_generation",
            _to_float(
                data.get("total_generation")
            ),
        )

        add_if_not_none(
            "co2",
            _to_float(data.get("co2")),
        )

        add_if_not_none(
            "tree",
            _to_float(data.get("tree")),
        )

        add_if_not_none(
            "diesel",
            _to_float(data.get("diesel")),
        )

        add_if_not_none(
            "today_revenue",
            _to_float(
                data.get("today_revenue")
            ),
        )

        add_if_not_none(
            "month_revenue",
            _to_float(
                data.get("month_revenue")
            ),
        )

        add_if_not_none(
            "total_revenue",
            _to_float(
                data.get("total_revenue")
            ),
        )

    # =========================================================
    # ENERGY2
    # =========================================================

    if energy and "data" in energy:

        data = energy["data"]

        # AC energy
        add_if_not_none(
            "kwhac",
            _to_float(data.get("kwhac")),
        )

        # Total household/load consumption
        add_if_not_none(
            "load",
            _to_float(data.get("load")),
        )

        # Load energy sources
        add_if_not_none(
            "load_from_bat",
            _to_float(
                data.get("load_from_bat")
            ),
        )

        add_if_not_none(
            "load_from_grid",
            _to_float(
                data.get("load_from_grid")
            ),
        )

        add_if_not_none(
            "load_from_pv",
            _to_float(
                data.get("load_from_pv")
            ),
        )

        # PV generation
        add_if_not_none(
            "pvkwh",
            _to_float(data.get("pvkwh")),
        )

        # PV destinations
        add_if_not_none(
            "pv_to_bat",
            _to_float(
                data.get("pv_to_bat")
            ),
        )

        add_if_not_none(
            "pv_to_grid",
            _to_float(
                data.get("pv_to_grid")
            ),
        )

        add_if_not_none(
            "pv_to_load",
            _to_float(
                data.get("pv_to_load")
            ),
        )

        # Preserve balance, but don't use it for calculations
        # until its exact meaning is established.
        add_if_not_none(
            "balance",
            _to_float(data.get("balance")),
        )

    # =========================================================
    # STATUS
    # =========================================================

    if status and "data" in status:

        data = status["data"]

        # Gateway status
        gateway = data.get("gateway")

        if isinstance(gateway, dict):

            add_if_not_none(
                "gateway_online",
                _to_int(
                    gateway.get("online")
                ),
            )

            add_if_not_none(
                "gateway_offline",
                _to_int(
                    gateway.get("offline")
                ),
            )

        # Inverter status
        inverter = data.get("inverter")

        if isinstance(inverter, dict):

            add_if_not_none(
                "inverter_online",
                _to_int(
                    inverter.get("online")
                ),
            )

            add_if_not_none(
                "inverter_normal",
                _to_int(
                    inverter.get("normal")
                ),
            )

            add_if_not_none(
                "inverter_offline",
                _to_int(
                    inverter.get("offline")
                ),
            )

            add_if_not_none(
                "inverter_fault",
                _to_int(
                    inverter.get("fault")
                ),
            )

            add_if_not_none(
                "inverter_wait",
                _to_int(
                    inverter.get("wait")
                ),
            )

    return merged
