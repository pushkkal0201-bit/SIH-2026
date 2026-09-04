from __future__ import annotations


from datetime import datetime, timezone
from math import isfinite
from typing import Any, Dict, Mapping, Optional

from backend.models.schemas import TelemetryFrame


CAN_ADAPTER_VERSION = "1.1.0"


CAN_TELEMETRY_SOURCE = "can_fadec"


_processed_frames: int = 0

_failed_frames: int = 0

_normalization_count: int = 0

_build_count: int = 0


_latest_frame: Optional[
    TelemetryFrame
] = None


_latest_normalized_payload: Optional[
    Dict[str, Any]
] = None


_latest_error: Optional[str] = None

_latest_error_type: Optional[str] = None

_latest_processing_timestamp: Optional[
    datetime
] = None


def utc_now() -> datetime:

    return datetime.now(
        timezone.utc
    )


def _first_available(
    signals: Mapping[str, Any],
    *keys: str,
) -> Any:

    for key in keys:

        if key not in signals:
            continue

        value = signals[key]

        if value is not None:
            return value

    return None


def _reject_bool(
    value: Any,
    signal_name: str,
) -> None:

    if isinstance(
        value,
        bool,
    ):

        raise ValueError(
            f"{signal_name}: boolean value is not a valid "
            f"engineering measurement."
        )


def _float_or_none(
    value: Any,
    signal_name: str = "signal",
) -> Optional[float]:

    if value is None:

        return None


    _reject_bool(
        value,
        signal_name,
    )


    try:

        result = float(
            value
        )

    except (
        TypeError,
        ValueError,
    ) as exc:

        raise ValueError(
            f"{signal_name}: invalid numeric CAN value "
            f"{value!r}."
        ) from exc


    if not isfinite(
        result
    ):

        raise ValueError(
            f"{signal_name}: non-finite CAN value "
            f"{value!r}."
        )


    return result


def _int_or_none(
    value: Any,
    signal_name: str = "signal",
) -> Optional[int]:

    if value is None:

        return None


    _reject_bool(
        value,
        signal_name,
    )


    try:

        number = float(
            value
        )

    except (
        TypeError,
        ValueError,
    ) as exc:

        raise ValueError(
            f"{signal_name}: invalid integer CAN value "
            f"{value!r}."
        ) from exc


    if not isfinite(
        number
    ):

        raise ValueError(
            f"{signal_name}: non-finite integer value."
        )


    return int(
        number
    )


def _string_or_none(
    value: Any,
) -> Optional[str]:

    if value is None:

        return None


    text = str(
        value
    ).strip()


    if not text:

        return None


    return text


def _timestamp_or_now(
    value: Any,
) -> Any:

    if value is None:

        return utc_now()


    return value


SIGNAL_ALIASES: Dict[
    str,
    tuple[str, ...],
] = {

    "timestamp": (
        "timestamp",
        "time",
        "ecu_timestamp",
        "fadec_timestamp",
    ),

    "sequence": (
        "sequence",
        "sequence_number",
        "counter",
        "frame_counter",
        "message_counter",
    ),


    "engine.rpm": (
        "engine_rpm",
        "rpm",
        "engine_speed_rpm",
        "shaft_speed_rpm",
    ),

    "engine.throttle_percent": (
        "throttle_percent",
        "throttle",
        "throttle_position_percent",
        "throttle_position",
    ),

    "engine.load_percent": (
        "load_percent",
        "engine_load_percent",
        "engine_load",
        "load",
    ),

    "engine.power_kw": (
        "power_kw",
        "engine_power_kw",
        "shaft_power_kw",
    ),

    "engine.torque_nm": (
        "torque_nm",
        "engine_torque_nm",
        "shaft_torque_nm",
    ),


    "cht.cylinder1_c": (
        "cht_1_c",
        "cht1_c",
        "cylinder1_cht_c",
        "cylinder_1_cht_c",
    ),

    "cht.cylinder2_c": (
        "cht_2_c",
        "cht2_c",
        "cylinder2_cht_c",
        "cylinder_2_cht_c",
    ),

    "cht.cylinder3_c": (
        "cht_3_c",
        "cht3_c",
        "cylinder3_cht_c",
        "cylinder_3_cht_c",
    ),

    "cht.cylinder4_c": (
        "cht_4_c",
        "cht4_c",
        "cylinder4_cht_c",
        "cylinder_4_cht_c",
    ),


    "egt.cylinder1_c": (
        "egt_1_c",
        "egt1_c",
        "cylinder1_egt_c",
        "cylinder_1_egt_c",
    ),

    "egt.cylinder2_c": (
        "egt_2_c",
        "egt2_c",
        "cylinder2_egt_c",
        "cylinder_2_egt_c",
    ),

    "egt.cylinder3_c": (
        "egt_3_c",
        "egt3_c",
        "cylinder3_egt_c",
        "cylinder_3_egt_c",
    ),

    "egt.cylinder4_c": (
        "egt_4_c",
        "egt4_c",
        "cylinder4_egt_c",
        "cylinder_4_egt_c",
    ),


    "oil.pressure_kpa": (
        "oil_pressure_kpa",
        "oil_press_kpa",
        "lubrication_pressure_kpa",
    ),

    "oil.temperature_c": (
        "oil_temperature_c",
        "oil_temp_c",
        "lubrication_temperature_c",
    ),


    "fuel.flow_kg_per_second": (
        "fuel_flow_kg_per_second",
        "fuel_flow_kg_s",
        "fuel_mass_flow_kg_s",
    ),

    "fuel.pressure_kpa": (
        "fuel_pressure_kpa",
        "rail_pressure_kpa",
    ),

    "fuel.injection_timing_deg": (
        "injection_timing_deg",
        "fuel_injection_timing_deg",
        "injection_angle_deg",
    ),


    "vibration.overall_g": (
        "vibration_overall_g",
        "overall_vibration_g",
        "vibration_g",
    ),

    "vibration.x_g": (
        "vibration_x_g",
        "acceleration_x_g",
    ),

    "vibration.y_g": (
        "vibration_y_g",
        "acceleration_y_g",
    ),

    "vibration.z_g": (
        "vibration_z_g",
        "acceleration_z_g",
    ),


    "electrical.battery_voltage_v": (
        "battery_voltage_v",
        "battery_v",
    ),

    "electrical.battery_current_a": (
        "battery_current_a",
        "battery_a",
    ),

    "electrical.alternator_voltage_v": (
        "alternator_voltage_v",
        "generator_voltage_v",
    ),

    "electrical.alternator_current_a": (
        "alternator_current_a",
        "generator_current_a",
    ),


    "environment.altitude_m": (
        "altitude_m",
        "pressure_altitude_m",
    ),

    "environment.altitude_ft": (
        "altitude_ft",
        "pressure_altitude_ft",
    ),

    "environment.ambient_temperature_c": (
        "ambient_temperature_c",
        "ambient_temp_c",
        "outside_air_temperature_c",
        "oat_c",
    ),

    "environment.ambient_pressure_kpa": (
        "ambient_pressure_kpa",
        "barometric_pressure_kpa",
    ),

    "environment.air_density_kg_m3": (
        "air_density_kg_m3",
        "ambient_air_density_kg_m3",
    ),


    "mission.id": (
        "mission_id",
        "missionId",
    ),

    "mission.elapsed_time_sec": (
        "elapsed_time_sec",
        "elapsedTimeSec",
        "mission_elapsed_time_sec",
    ),

    "mission.phase": (
        "mission_phase",
        "phase",
        "flight_phase",
    ),
}


def _resolve(
    signals: Mapping[str, Any],
    canonical_name: str,
) -> Any:

    aliases = SIGNAL_ALIASES.get(
        canonical_name,
        (),
    )


    return _first_available(
        signals,
        *aliases,
    )


def normalize_can_signals(
    signals: Mapping[str, Any],
) -> Dict[str, Any]:

    global _normalization_count
    global _latest_normalized_payload


    if not isinstance(
        signals,
        Mapping,
    ):

        raise TypeError(
            "Decoded CAN signals must be provided as a mapping."
        )


    timestamp = _resolve(
        signals,
        "timestamp",
    )


    sequence = _resolve(
        signals,
        "sequence",
    )


    payload: Dict[str, Any] = {

        "meta": {

            "timestamp":
                _timestamp_or_now(
                    timestamp
                ),

            "source":
                CAN_TELEMETRY_SOURCE,

            "sequence":
                _int_or_none(
                    sequence,
                    "sequence",
                ),
        },


        "engine": {

            "rpm":
                _float_or_none(
                    _resolve(
                        signals,
                        "engine.rpm",
                    ),
                    "engine.rpm",
                ),

            "throttle_percent":
                _float_or_none(
                    _resolve(
                        signals,
                        "engine.throttle_percent",
                    ),
                    "engine.throttle_percent",
                ),

            "load_percent":
                _float_or_none(
                    _resolve(
                        signals,
                        "engine.load_percent",
                    ),
                    "engine.load_percent",
                ),

            "power_kw":
                _float_or_none(
                    _resolve(
                        signals,
                        "engine.power_kw",
                    ),
                    "engine.power_kw",
                ),

            "torque_nm":
                _float_or_none(
                    _resolve(
                        signals,
                        "engine.torque_nm",
                    ),
                    "engine.torque_nm",
                ),
        },


        "cht": {

            "cylinder1_c":
                _float_or_none(
                    _resolve(
                        signals,
                        "cht.cylinder1_c",
                    ),
                    "cht.cylinder1_c",
                ),

            "cylinder2_c":
                _float_or_none(
                    _resolve(
                        signals,
                        "cht.cylinder2_c",
                    ),
                    "cht.cylinder2_c",
                ),

            "cylinder3_c":
                _float_or_none(
                    _resolve(
                        signals,
                        "cht.cylinder3_c",
                    ),
                    "cht.cylinder3_c",
                ),

            "cylinder4_c":
                _float_or_none(
                    _resolve(
                        signals,
                        "cht.cylinder4_c",
                    ),
                    "cht.cylinder4_c",
                ),
        },


        "egt": {

            "cylinder1_c":
                _float_or_none(
                    _resolve(
                        signals,
                        "egt.cylinder1_c",
                    ),
                    "egt.cylinder1_c",
                ),

            "cylinder2_c":
                _float_or_none(
                    _resolve(
                        signals,
                        "egt.cylinder2_c",
                    ),
                    "egt.cylinder2_c",
                ),

            "cylinder3_c":
                _float_or_none(
                    _resolve(
                        signals,
                        "egt.cylinder3_c",
                    ),
                    "egt.cylinder3_c",
                ),

            "cylinder4_c":
                _float_or_none(
                    _resolve(
                        signals,
                        "egt.cylinder4_c",
                    ),
                    "egt.cylinder4_c",
                ),
        },


        "oil": {

            "pressure_kpa":
                _float_or_none(
                    _resolve(
                        signals,
                        "oil.pressure_kpa",
                    ),
                    "oil.pressure_kpa",
                ),

            "temperature_c":
                _float_or_none(
                    _resolve(
                        signals,
                        "oil.temperature_c",
                    ),
                    "oil.temperature_c",
                ),
        },


        "fuel": {

            "flow_kg_per_second":
                _float_or_none(
                    _resolve(
                        signals,
                        "fuel.flow_kg_per_second",
                    ),
                    "fuel.flow_kg_per_second",
                ),

            "pressure_kpa":
                _float_or_none(
                    _resolve(
                        signals,
                        "fuel.pressure_kpa",
                    ),
                    "fuel.pressure_kpa",
                ),

            "injection_timing_deg":
                _float_or_none(
                    _resolve(
                        signals,
                        "fuel.injection_timing_deg",
                    ),
                    "fuel.injection_timing_deg",
                ),
        },


        "vibration": {

            "overall_g":
                _float_or_none(
                    _resolve(
                        signals,
                        "vibration.overall_g",
                    ),
                    "vibration.overall_g",
                ),

            "x_g":
                _float_or_none(
                    _resolve(
                        signals,
                        "vibration.x_g",
                    ),
                    "vibration.x_g",
                ),

            "y_g":
                _float_or_none(
                    _resolve(
                        signals,
                        "vibration.y_g",
                    ),
                    "vibration.y_g",
                ),

            "z_g":
                _float_or_none(
                    _resolve(
                        signals,
                        "vibration.z_g",
                    ),
                    "vibration.z_g",
                ),
        },


        "electrical": {

            "battery_voltage_v":
                _float_or_none(
                    _resolve(
                        signals,
                        "electrical.battery_voltage_v",
                    ),
                    "electrical.battery_voltage_v",
                ),

            "battery_current_a":
                _float_or_none(
                    _resolve(
                        signals,
                        "electrical.battery_current_a",
                    ),
                    "electrical.battery_current_a",
                ),

            "alternator_voltage_v":
                _float_or_none(
                    _resolve(
                        signals,
                        "electrical.alternator_voltage_v",
                    ),
                    "electrical.alternator_voltage_v",
                ),

            "alternator_current_a":
                _float_or_none(
                    _resolve(
                        signals,
                        "electrical.alternator_current_a",
                    ),
                    "electrical.alternator_current_a",
                ),
        },


        "environment": {

            "altitude_m":
                _float_or_none(
                    _resolve(
                        signals,
                        "environment.altitude_m",
                    ),
                    "environment.altitude_m",
                ),

            "altitude_ft":
                _float_or_none(
                    _resolve(
                        signals,
                        "environment.altitude_ft",
                    ),
                    "environment.altitude_ft",
                ),

            "ambient_temperature_c":
                _float_or_none(
                    _resolve(
                        signals,
                        "environment.ambient_temperature_c",
                    ),
                    "environment.ambient_temperature_c",
                ),

            "ambient_pressure_kpa":
                _float_or_none(
                    _resolve(
                        signals,
                        "environment.ambient_pressure_kpa",
                    ),
                    "environment.ambient_pressure_kpa",
                ),

            "air_density_kg_m3":
                _float_or_none(
                    _resolve(
                        signals,
                        "environment.air_density_kg_m3",
                    ),
                    "environment.air_density_kg_m3",
                ),
        },


        "mission": {

            "missionId":
                _string_or_none(
                    _resolve(
                        signals,
                        "mission.id",
                    )
                ),

            "elapsedTimeSec":
                _float_or_none(
                    _resolve(
                        signals,
                        "mission.elapsed_time_sec",
                    ),
                    "mission.elapsed_time_sec",
                ),

            "phase":
                _string_or_none(
                    _resolve(
                        signals,
                        "mission.phase",
                    )
                ),
        },
    }


    _normalization_count += 1

    _latest_normalized_payload = payload


    return payload


def build_telemetry_frame(
    signals: Mapping[str, Any],
) -> TelemetryFrame:

    global _build_count


    payload = normalize_can_signals(
        signals
    )


    frame = TelemetryFrame.model_validate(
        payload
    )


    _build_count += 1


    return frame


async def process_can_signals(
    signals: Mapping[str, Any],
) -> TelemetryFrame:

    global _processed_frames
    global _failed_frames

    global _latest_frame

    global _latest_error
    global _latest_error_type

    global _latest_processing_timestamp


    try:

        telemetry = build_telemetry_frame(
            signals
        )


        from backend.api.telemetry import (
            ingest_telemetry,
        )


        validated = await ingest_telemetry(
            telemetry
        )


        _processed_frames += 1

        _latest_frame = validated

        _latest_error = None

        _latest_error_type = None

        _latest_processing_timestamp = (
            utc_now()
        )


        return validated


    except Exception as exc:

        _failed_frames += 1

        _latest_error = str(
            exc
        )

        _latest_error_type = (
            type(exc).__name__
        )

        _latest_processing_timestamp = (
            utc_now()
        )


        raise


async def ingest_decoded_can_message(
    decoded_message: Mapping[str, Any],
) -> TelemetryFrame:

    return await process_can_signals(
        decoded_message
    )


def get_latest_can_frame() -> Optional[
    TelemetryFrame
]:

    return _latest_frame


def get_latest_can_frame_dict() -> Optional[
    Dict[str, Any]
]:

    if _latest_frame is None:

        return None


    return _latest_frame.model_dump(
        mode="json"
    )


def get_latest_normalized_payload() -> Optional[
    Dict[str, Any]
]:

    return _latest_normalized_payload


def get_can_adapter_status() -> Dict[str, Any]:

    latest_sequence = None

    latest_source = None

    latest_timestamp = None


    if _latest_frame is not None:

        latest_sequence = (
            _latest_frame.meta.sequence
        )

        latest_source = (
            _latest_frame.meta.source
        )


        timestamp_value = (
            _latest_frame.meta.timestamp
        )


        if timestamp_value is not None:

            if hasattr(
                timestamp_value,
                "isoformat",
            ):

                latest_timestamp = (
                    timestamp_value.isoformat()
                )

            else:

                latest_timestamp = str(
                    timestamp_value
                )


    return {

        "service":
            "can_adapter",

        "status":
            "READY",

        "version":
            CAN_ADAPTER_VERSION,

        "source":
            CAN_TELEMETRY_SOURCE,

        "transport":
            "INDEPENDENT",

        "processed_frames":
            _processed_frames,

        "failed_frames":
            _failed_frames,

        "normalization_count":
            _normalization_count,

        "build_count":
            _build_count,

        "latest_frame_available":
            _latest_frame is not None,

        "latest_sequence":
            latest_sequence,

        "latest_source":
            latest_source,

        "latest_frame_timestamp":
            latest_timestamp,

        "latest_processing_timestamp":
            (
                _latest_processing_timestamp.isoformat()

                if _latest_processing_timestamp
                is not None

                else None
            ),

        "latest_error":
            _latest_error,

        "latest_error_type":
            _latest_error_type,

        "null_policy":
            (
                "None = unavailable measurement; "
                "zero = genuine numeric zero"
            ),

        "pipeline_destination":
            "backend.api.telemetry.ingest_telemetry",

        "timestamp":
            utc_now().isoformat(),
    }


def reset_can_adapter() -> None:

    global _processed_frames
    global _failed_frames

    global _normalization_count
    global _build_count

    global _latest_frame
    global _latest_normalized_payload

    global _latest_error
    global _latest_error_type

    global _latest_processing_timestamp


    _processed_frames = 0

    _failed_frames = 0

    _normalization_count = 0

    _build_count = 0


    _latest_frame = None

    _latest_normalized_payload = None


    _latest_error = None

    _latest_error_type = None


    _latest_processing_timestamp = None


def get_can_adapter_info() -> Dict[str, Any]:

    return {

        "name":
            "PRATIRUP CAN / FADEC Adapter",

        "version":
            CAN_ADAPTER_VERSION,

        "source":
            CAN_TELEMETRY_SOURCE,

        "input":
            "Decoded CAN/FADEC engineering signals",

        "output":
            "TelemetryFrame",

        "transport_independent":
            True,

        "raw_can_decoder":
            False,

        "supported_groups": [

            "engine",

            "cht",

            "egt",

            "oil",

            "fuel",

            "vibration",

            "electrical",

            "environment",

            "mission",
        ],

        "supported_source_literals": [

            "simulation",

            "can_fadec",

            "replay",

            "test_rig",

            "unknown",
        ],

        "pipeline_destination":
            "backend.api.telemetry.ingest_telemetry",

        "next_stage":
            "backend.ingestion.fadec_decoder",

        "policy":
            (
                "Missing values remain None; genuine numeric "
                "zero values are preserved."
            ),

        "engineering_disclaimer":
            (
                "CAN arbitration IDs, bit definitions and "
                "scaling must come from a verified interface "
                "definition or DBC. This adapter does not "
                "assume proprietary FADEC definitions."
            ),
    }
