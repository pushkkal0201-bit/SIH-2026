from __future__ import annotations

from collections import deque
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

DIGITAL_TWIN_VERSION = "1.0.0"

MAX_TWIN_HISTORY = 500

TELEMETRY_STALE_AFTER_SECONDS = 2.0


def utc_now() -> datetime:

    return datetime.now(
        timezone.utc
    )


def safe_copy(
    value: Any,
) -> Any:

    return deepcopy(
        value
    )


@dataclass
class DigitalTwinState:

    timestamp: datetime

    source: Optional[str]

    sequence: Optional[int]

    observed_state: Optional[
        Dict[str, Any]
    ]

    expected_state: Optional[
        Dict[str, Any]
    ]

    residual_state: Optional[
        Dict[str, Any]
    ]

    synchronized: bool

    synchronization_status: str

    coverage: float

    state_confidence: float

    warnings: List[str] = field(
        default_factory=list
    )

    twin_version: str = (
        DIGITAL_TWIN_VERSION
    )

    def to_dict(
        self,
    ) -> Dict[str, Any]:

        return {

            "timestamp":
                self.timestamp.isoformat(),

            "source":
                self.source,

            "sequence":
                self.sequence,

            "observed_state":
                safe_copy(
                    self.observed_state
                ),

            "expected_state":
                safe_copy(
                    self.expected_state
                ),

            "residual_state":
                safe_copy(
                    self.residual_state
                ),

            "synchronized":
                self.synchronized,

            "synchronization_status":
                self.synchronization_status,

            "coverage":
                self.coverage,

            "state_confidence":
                self.state_confidence,

            "warnings":
                list(
                    self.warnings
                ),

            "twin_version":
                self.twin_version,
        }


_latest_twin_state: Optional[
    DigitalTwinState
] = None

_observed_state: Optional[
    Dict[str, Any]
] = None

_expected_state: Optional[
    Dict[str, Any]
] = None

_residual_state: Optional[
    Dict[str, Any]
] = None

_last_observed_timestamp: Optional[
    datetime
] = None

_last_source: Optional[str] = None

_last_sequence: Optional[int] = None

_latest_coverage: float = 0.0

_latest_confidence: float = 0.0

_twin_update_count = 0

_observed_update_count = 0

_expected_update_count = 0

_residual_update_count = 0

_twin_history: deque[
    DigitalTwinState
] = deque(
    maxlen=MAX_TWIN_HISTORY
)


def clamp(
    value: float,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:

    return max(
        minimum,
        min(
            maximum,
            value,
        ),
    )


def parse_datetime(
    value: Any,
) -> Optional[datetime]:

    if isinstance(
        value,
        datetime,
    ):

        if value.tzinfo is None:

            return value.replace(
                tzinfo=timezone.utc
            )

        return value

    if isinstance(
        value,
        str,
    ):

        try:

            normalized = value.replace(
                "Z",
                "+00:00",
            )

            parsed = datetime.fromisoformat(
                normalized
            )

            if parsed.tzinfo is None:

                parsed = parsed.replace(
                    tzinfo=timezone.utc
                )

            return parsed

        except ValueError:

            return None

    return None


def determine_synchronization() -> tuple[
    bool,
    str,
]:

    if _observed_state is None:

        return (
            False,
            "WAITING_FOR_OBSERVED_STATE",
        )

    if _last_observed_timestamp is None:

        return (
            False,
            "OBSERVED_TIMESTAMP_UNAVAILABLE",
        )

    age = (
        utc_now() -
        _last_observed_timestamp
    ).total_seconds()

    if (
        age >
        TELEMETRY_STALE_AFTER_SECONDS
    ):

        return (
            False,
            "OBSERVED_STATE_STALE",
        )

    return (
        True,
        "SYNCHRONIZED",
    )


def build_warnings(
    synchronized: bool,
    coverage: float,
) -> List[str]:

    warnings: List[str] = []

    if not synchronized:

        warnings.append(
            "Digital Twin is not synchronized with fresh observed state."
        )

    if coverage < 0.25:

        warnings.append(
            "Digital Twin observed-state coverage is very low."
        )

    elif coverage < 0.50:

        warnings.append(
            "Digital Twin observed-state coverage is limited."
        )

    if _expected_state is None:

        warnings.append(
            "Expected physics state is not available yet."
        )

    if _residual_state is None:

        warnings.append(
            "Residual state is not available yet."
        )

    return warnings


def build_twin_state() -> DigitalTwinState:

    synchronized, status = (
        determine_synchronization()
    )

    confidence = (
        _latest_confidence
        if synchronized
        else _latest_confidence * 0.5
    )

    confidence = clamp(
        confidence
    )

    warnings = build_warnings(
        synchronized,
        _latest_coverage,
    )

    return DigitalTwinState(

        timestamp=utc_now(),

        source=_last_source,

        sequence=_last_sequence,

        observed_state=(
            safe_copy(
                _observed_state
            )
            if _observed_state is not None
            else None
        ),

        expected_state=(
            safe_copy(
                _expected_state
            )
            if _expected_state is not None
            else None
        ),

        residual_state=(
            safe_copy(
                _residual_state
            )
            if _residual_state is not None
            else None
        ),

        synchronized=synchronized,

        synchronization_status=status,

        coverage=clamp(
            _latest_coverage
        ),

        state_confidence=confidence,

        warnings=warnings,
    )


def refresh_twin_state() -> DigitalTwinState:

    global _latest_twin_state
    global _twin_update_count

    state = build_twin_state()

    _latest_twin_state = state

    _twin_history.append(
        state
    )

    _twin_update_count += 1

    return state


def set_observed_state(
    estimated_state: Dict[str, Any],
) -> DigitalTwinState:

    global _observed_state

    global _last_observed_timestamp
    global _last_source
    global _last_sequence

    global _latest_coverage
    global _latest_confidence

    global _observed_update_count

    if not isinstance(
        estimated_state,
        dict,
    ):

        raise TypeError(
            "Digital Twin observed state must be a dictionary."
        )

    state_payload = estimated_state.get(
        "state"
    )

    if not isinstance(
        state_payload,
        dict,
    ):

        raise ValueError(
            "Estimated state does not contain a valid 'state' object."
        )

    _observed_state = safe_copy(
        state_payload
    )

    timestamp = parse_datetime(
        estimated_state.get(
            "timestamp"
        )
    )

    _last_observed_timestamp = (
        timestamp
        if timestamp is not None
        else utc_now()
    )

    source = estimated_state.get(
        "source"
    )

    _last_source = (
        str(source)
        if source is not None
        else None
    )

    sequence = estimated_state.get(
        "sequence"
    )

    if (
        isinstance(sequence, int)
        and not isinstance(
            sequence,
            bool,
        )
    ):

        _last_sequence = sequence

    else:

        _last_sequence = None

    coverage_section = (
        estimated_state.get(
            "coverage"
        )
    )

    coverage = 0.0

    if isinstance(
        coverage_section,
        dict,
    ):

        fraction = coverage_section.get(
            "fraction"
        )

        if isinstance(
            fraction,
            (int, float),
        ) and not isinstance(
            fraction,
            bool,
        ):

            coverage = float(
                fraction
            )

    _latest_coverage = clamp(
        coverage
    )

    confidence = estimated_state.get(
        "confidence"
    )

    if (
        isinstance(
            confidence,
            (int, float),
        )
        and not isinstance(
            confidence,
            bool,
        )
    ):

        _latest_confidence = clamp(
            float(
                confidence
            )
        )

    else:

        _latest_confidence = 0.0

    _observed_update_count += 1

    return refresh_twin_state()


def set_expected_state(
    expected_state: Optional[
        Dict[str, Any]
    ],
) -> DigitalTwinState:

    global _expected_state
    global _expected_update_count

    if expected_state is not None:

        if not isinstance(
            expected_state,
            dict,
        ):

            raise TypeError(
                "Expected state must be a dictionary or None."
            )

        _expected_state = safe_copy(
            expected_state
        )

    else:

        _expected_state = None

    _expected_update_count += 1

    return refresh_twin_state()


def set_residual_state(
    residual_state: Optional[
        Dict[str, Any]
    ],
) -> DigitalTwinState:

    global _residual_state
    global _residual_update_count

    if residual_state is not None:

        if not isinstance(
            residual_state,
            dict,
        ):

            raise TypeError(
                "Residual state must be a dictionary or None."
            )

        _residual_state = safe_copy(
            residual_state
        )

    else:

        _residual_state = None

    _residual_update_count += 1

    return refresh_twin_state()


def clear_expected_state() -> DigitalTwinState:

    return set_expected_state(
        None
    )


def clear_residual_state() -> DigitalTwinState:

    return set_residual_state(
        None
    )


def get_latest_twin_state() -> Optional[
    DigitalTwinState
]:

    return _latest_twin_state


def get_latest_twin_state_dict() -> Optional[
    Dict[str, Any]
]:

    if _latest_twin_state is None:

        return None

    return _latest_twin_state.to_dict()


def get_observed_state() -> Optional[
    Dict[str, Any]
]:

    return (
        safe_copy(
            _observed_state
        )
        if _observed_state is not None
        else None
    )


def get_expected_state() -> Optional[
    Dict[str, Any]
]:

    return (
        safe_copy(
            _expected_state
        )
        if _expected_state is not None
        else None
    )


def get_residual_state() -> Optional[
    Dict[str, Any]
]:

    return (
        safe_copy(
            _residual_state
        )
        if _residual_state is not None
        else None
    )


def get_twin_history(
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:

    states = list(
        _twin_history
    )

    if (
        limit is not None
        and limit > 0
    ):

        states = states[
            -limit:
        ]

    return [
        state.to_dict()
        for state
        in states
    ]


def get_digital_twin_status() -> Dict[str, Any]:

    synchronized, status = (
        determine_synchronization()
    )

    return {

        "service":
            "digital_twin",

        "status":
            "READY",

        "version":
            DIGITAL_TWIN_VERSION,

        "synchronized":
            synchronized,

        "synchronization_status":
            status,

        "observed_state_available":
            _observed_state is not None,

        "expected_state_available":
            _expected_state is not None,

        "residual_state_available":
            _residual_state is not None,

        "coverage":
            _latest_coverage,

        "state_confidence":
            _latest_confidence,

        "source":
            _last_source,

        "sequence":
            _last_sequence,

        "twin_update_count":
            _twin_update_count,

        "observed_update_count":
            _observed_update_count,

        "expected_update_count":
            _expected_update_count,

        "residual_update_count":
            _residual_update_count,

        "history_size":
            len(
                _twin_history
            ),

        "history_capacity":
            MAX_TWIN_HISTORY,

        "timestamp":
            utc_now().isoformat(),
    }


def reset_digital_twin() -> None:

    global _latest_twin_state

    global _observed_state
    global _expected_state
    global _residual_state

    global _last_observed_timestamp

    global _last_source
    global _last_sequence

    global _latest_coverage
    global _latest_confidence

    global _twin_update_count
    global _observed_update_count
    global _expected_update_count
    global _residual_update_count

    _latest_twin_state = None

    _observed_state = None

    _expected_state = None

    _residual_state = None

    _last_observed_timestamp = None

    _last_source = None

    _last_sequence = None

    _latest_coverage = 0.0

    _latest_confidence = 0.0

    _twin_update_count = 0

    _observed_update_count = 0

    _expected_update_count = 0

    _residual_update_count = 0

    _twin_history.clear()


def get_digital_twin_info() -> Dict[str, Any]:

    return {

        "name":
            "PRATIRUP Backend Digital Twin Core",

        "version":
            DIGITAL_TWIN_VERSION,

        "purpose":
            (
                "Coordinate observed, expected, and residual "
                "engine states."
            ),

        "null_policy":
            (
                "None means unavailable; "
                "zero remains a genuine value."
            ),

        "current_capabilities": [
            "observed_state",
            "state_synchronization",
            "coverage_tracking",
            "confidence_tracking",
            "expected_state_storage",
            "residual_state_storage",
            "history",
        ],

        "future_connections": [
            "physics_models",
            "residual_engine",
            "diagnostics",
            "degradation",
            "rul",
            "mission_intelligence",
        ],
    }
