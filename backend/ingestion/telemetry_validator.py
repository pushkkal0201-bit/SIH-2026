from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from math import isfinite
from typing import Any, Dict, List, Optional


TELEMETRY_VALIDATOR_VERSION = "1.0.0"


@dataclass
class ValidationResult:
    valid: bool
    telemetry: Optional[Dict[str, Any]]
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    validator_version: str = TELEMETRY_VALIDATOR_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "telemetry": self.telemetry,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "validator_version": self.validator_version,
        }


RANGES = {

    "engine.rpm": {
        "min": 0,
        "max": 7000,
    },

    "engine.throttle_percent": {
        "min": 0,
        "max": 100,
    },

    "engine.load_percent": {
        "min": 0,
        "max": 100,
    },

    "engine.power_kw": {
        "min": 0,
        "max": 250,
    },

    "engine.torque_nm": {
        "min": 0,
        "max": 1500,
    },

    "cht.cylinder1_c": {
        "min": -50,
        "max": 400,
    },

    "cht.cylinder2_c": {
        "min": -50,
        "max": 400,
    },

    "cht.cylinder3_c": {
        "min": -50,
        "max": 400,
    },

    "cht.cylinder4_c": {
        "min": -50,
        "max": 400,
    },

    "egt.cylinder1_c": {
        "min": -50,
        "max": 1200,
    },

    "egt.cylinder2_c": {
        "min": -50,
        "max": 1200,
    },

    "egt.cylinder3_c": {
        "min": -50,
        "max": 1200,
    },

    "egt.cylinder4_c": {
        "min": -50,
        "max": 1200,
    },

    "oil.pressure_kpa": {
        "min": 0,
        "max": 1500,
    },

    "oil.temperature_c": {
        "min": -50,
        "max": 250,
    },

    "fuel.flow_kg_per_second": {
        "min": 0,
        "max": 1,
    },

    "fuel.pressure_kpa": {
        "min": 0,
        "max": 3000,
    },

    "fuel.injection_timing_deg": {
        "min": -90,
        "max": 90,
    },

    "vibration.overall_g": {
        "min": 0,
        "max": 50,
    },

    "vibration.x_g": {
        "min": -50,
        "max": 50,
    },

    "vibration.y_g": {
        "min": -50,
        "max": 50,
    },

    "vibration.z_g": {
        "min": -50,
        "max": 50,
    },

    "electrical.battery_voltage_v": {
        "min": 0,
        "max": 60,
    },

    "electrical.battery_current_a": {
        "min": -500,
        "max": 500,
    },

    "electrical.alternator_voltage_v": {
        "min": 0,
        "max": 60,
    },

    "electrical.alternator_current_a": {
        "min": -500,
        "max": 500,
    },

    "environment.altitude_m": {
        "min": -1000,
        "max": 30000,
    },

    "environment.altitude_ft": {
        "min": -3500,
        "max": 100000,
    },

    "environment.ambient_temperature_c": {
        "min": -100,
        "max": 100,
    },

    "environment.ambient_pressure_kpa": {
        "min": 0,
        "max": 150,
    },

    "environment.air_density_kg_m3": {
        "min": 0,
        "max": 2,
    },

    "twin.stateConfidence": {
        "min": 0,
        "max": 1,
    },

    "twin.residualScore": {
        "min": 0,
        "max": 1000,
    },

    "health.overallIndex": {
        "min": 0,
        "max": 100,
    },

    "health.combustion": {
        "min": 0,
        "max": 100,
    },

    "health.lubrication": {
        "min": 0,
        "max": 100,
    },

    "health.cooling": {
        "min": 0,
        "max": 100,
    },

    "health.fuelSystem": {
        "min": 0,
        "max": 100,
    },

    "health.electrical": {
        "min": 0,
        "max": 100,
    },

    "health.vibration": {
        "min": 0,
        "max": 100,
    },

    "diagnostics.anomalyScore": {
        "min": 0,
        "max": 1,
    },

    "prediction.degradationRate": {
        "min": 0,
        "max": 1000,
    },

    "prediction.rulHours": {
        "min": 0,
        "max": 100000,
    },

    "prediction.confidence": {
        "min": 0,
        "max": 1,
    },

}


TOP_LEVEL_SECTIONS = [
    "meta",
    "engine",
    "cht",
    "egt",
    "oil",
    "fuel",
    "vibration",
    "electrical",
    "environment",
    "injection",
    "mission",
    "twin",
    "health",
    "diagnostics",
    "prediction",
]


def is_number(value: Any) -> bool:

    if isinstance(value, bool):
        return False

    if not isinstance(value, (int, float)):
        return False

    return isfinite(float(value))


def get_nested(
    data: Dict[str, Any],
    path: str,
) -> Any:

    current: Any = data

    for key in path.split("."):

        if not isinstance(current, dict):
            return None

        if key not in current:
            return None

        current = current[key]

    return current


def set_nested(
    data: Dict[str, Any],
    path: str,
    value: Any,
) -> None:

    keys = path.split(".")

    current = data

    for key in keys[:-1]:

        if key not in current:
            current[key] = {}

        if not isinstance(current[key], dict):
            current[key] = {}

        current = current[key]

    current[keys[-1]] = value


def validate_timestamp(
    value: Any,
    errors: List[str],
    warnings: List[str],
) -> None:

    if value is None:
        warnings.append(
            "meta.timestamp is unavailable."
        )
        return

    if isinstance(value, (int, float)):

        if not is_number(value):
            errors.append(
                "meta.timestamp is not a valid numeric timestamp."
            )

        return

    if isinstance(value, str):

        timestamp_value = value.strip()

        if not timestamp_value:
            errors.append(
                "meta.timestamp is empty."
            )
            return

        try:

            normalized = timestamp_value.replace(
                "Z",
                "+00:00",
            )

            datetime.fromisoformat(
                normalized
            )

        except ValueError:

            errors.append(
                "meta.timestamp is not a valid ISO-8601 timestamp."
            )

        return

    errors.append(
        "meta.timestamp has an unsupported type."
    )


def validate_meta(
    telemetry: Dict[str, Any],
    errors: List[str],
    warnings: List[str],
) -> None:

    meta = telemetry.get("meta")

    if not isinstance(meta, dict):

        errors.append(
            "meta section is missing or invalid."
        )

        return

    validate_timestamp(
        meta.get("timestamp"),
        errors,
        warnings,
    )


    source = meta.get("source")

    if source is None:

        warnings.append(
            "meta.source is unavailable."
        )

    elif not isinstance(source, str):

        errors.append(
            "meta.source must be a string or null."
        )


    sequence = meta.get("sequence")

    if sequence is not None:

        if (
            isinstance(sequence, bool)
            or not isinstance(sequence, int)
            or sequence < 0
        ):

            errors.append(
                "meta.sequence must be a non-negative integer or null."
            )


def validate_sections(
    telemetry: Dict[str, Any],
    errors: List[str],
    warnings: List[str],
) -> None:

    for section in TOP_LEVEL_SECTIONS:

        if section not in telemetry:

            warnings.append(
                f"{section} section is missing."
            )

            continue

        section_value = telemetry[section]

        if section_value is not None and not isinstance(
            section_value,
            dict,
        ):

            errors.append(
                f"{section} must be an object or null."
            )


def validate_numeric_ranges(
    telemetry: Dict[str, Any],
    errors: List[str],
    warnings: List[str],
) -> None:

    for path, limits in RANGES.items():

        value = get_nested(
            telemetry,
            path,
        )


        if value is None:

            continue


        if not is_number(
            value
        ):

            errors.append(
                f"{path} must be a finite number or null."
            )

            continue


        number_value = float(
            value
        )


        minimum = limits.get(
            "min"
        )

        maximum = limits.get(
            "max"
        )


        if (
            minimum is not None
            and number_value < minimum
        ):

            warnings.append(
                f"{path}={number_value} is below "
                f"the demonstrator sanity range "
                f"minimum {minimum}."
            )


        if (
            maximum is not None
            and number_value > maximum
        ):

            warnings.append(
                f"{path}={number_value} is above "
                f"the demonstrator sanity range "
                f"maximum {maximum}."
            )


def validate_boolean_field(
    telemetry: Dict[str, Any],
    path: str,
    errors: List[str],
) -> None:

    value = get_nested(
        telemetry,
        path,
    )

    if value is None:
        return

    if not isinstance(
        value,
        bool,
    ):

        errors.append(
            f"{path} must be boolean or null."
        )


def validate_collections(
    telemetry: Dict[str, Any],
    errors: List[str],
) -> None:

    active_faults = get_nested(
        telemetry,
        "diagnostics.activeFaults",
    )

    if (
        active_faults is not None
        and not isinstance(
            active_faults,
            list,
        )
    ):

        errors.append(
            "diagnostics.activeFaults must be an array or null."
        )


    probable_faults = get_nested(
        telemetry,
        "diagnostics.probableFaults",
    )

    if (
        probable_faults is not None
        and not isinstance(
            probable_faults,
            list,
        )
    ):

        errors.append(
            "diagnostics.probableFaults must be an array or null."
        )


def validate_mission(
    telemetry: Dict[str, Any],
    errors: List[str],
) -> None:

    mission = telemetry.get(
        "mission"
    )

    if mission is None:
        return

    if not isinstance(
        mission,
        dict,
    ):

        return


    mission_id = mission.get(
        "missionId"
    )

    if (
        mission_id is not None
        and not isinstance(
            mission_id,
            str,
        )
    ):

        errors.append(
            "mission.missionId must be string or null."
        )


    phase = mission.get(
        "phase"
    )

    if (
        phase is not None
        and not isinstance(
            phase,
            str,
        )
    ):

        errors.append(
            "mission.phase must be string or null."
        )


    elapsed = mission.get(
        "elapsedTimeSec"
    )

    if (
        elapsed is not None
        and not is_number(
            elapsed
        )
    ):

        errors.append(
            "mission.elapsedTimeSec must be numeric or null."
        )


def validate_semantics(
    telemetry: Dict[str, Any],
    warnings: List[str],
) -> None:

    rpm = get_nested(
        telemetry,
        "engine.rpm",
    )

    throttle = get_nested(
        telemetry,
        "engine.throttle_percent",
    )

    load = get_nested(
        telemetry,
        "engine.load_percent",
    )


    if (
        rpm == 0
        and throttle == 0
        and load == 0
    ):

        return


    if (
        is_number(rpm)
        and rpm == 0
        and is_number(throttle)
        and throttle > 20
    ):

        warnings.append(
            "Engine RPM is 0 while throttle is above 20%. "
            "This may represent a stopped-engine command state, "
            "startup condition, or inconsistent telemetry."
        )


def add_validation_metadata(
    telemetry: Dict[str, Any],
    valid: bool,
    warning_count: int,
) -> None:

    meta = telemetry.setdefault(
        "meta",
        {},
    )


    if not isinstance(
        meta,
        dict,
    ):

        return


    meta["backend_validation"] = {

        "valid":
            valid,

        "warning_count":
            warning_count,

        "validator_version":
            TELEMETRY_VALIDATOR_VERSION,

        "validated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

    }


def validate_telemetry(
    telemetry: Any,
) -> ValidationResult:

    errors: List[str] = []

    warnings: List[str] = []


    if not isinstance(
        telemetry,
        dict,
    ):

        return ValidationResult(

            valid=False,

            telemetry=None,

            errors=[
                "Telemetry payload must be a JSON object."
            ],

            warnings=[],

        )


    normalized = deepcopy(
        telemetry
    )


    validate_sections(
        normalized,
        errors,
        warnings,
    )


    validate_meta(
        normalized,
        errors,
        warnings,
    )


    validate_numeric_ranges(
        normalized,
        errors,
        warnings,
    )


    validate_boolean_field(
        normalized,
        "twin.synchronized",
        errors,
    )


    validate_boolean_field(
        normalized,
        "diagnostics.anomalyDetected",
        errors,
    )


    validate_collections(
        normalized,
        errors,
    )


    validate_mission(
        normalized,
        errors,
    )


    validate_semantics(
        normalized,
        warnings,
    )


    valid = (
        len(errors) == 0
    )


    add_validation_metadata(
        normalized,
        valid,
        len(warnings),
    )


    return ValidationResult(

        valid=
            valid,

        telemetry=
            normalized,

        errors=
            errors,

        warnings=
            warnings,

    )


def is_valid_telemetry(
    telemetry: Any,
) -> bool:

    return validate_telemetry(
        telemetry
    ).valid


def validate_or_raise(
    telemetry: Any,
) -> Dict[str, Any]:

    result =validate_telemetry(
            telemetry
        )


    if not result.valid:

        raise ValueError(
            "Invalid PRATIRUP telemetry: "
            + "; ".join(
                result.errors
            )
        )


    return result.telemetry or {}


def get_validator_info() -> Dict[str, Any]:

    return {

        "name":
            "PRATIRUP Telemetry Validator",

        "version":
            TELEMETRY_VALIDATOR_VERSION,

        "null_policy":
            "None means unavailable; zero remains a valid numeric value.",

        "range_policy":
            "Out-of-range finite values produce warnings; malformed values produce errors.",

    }
