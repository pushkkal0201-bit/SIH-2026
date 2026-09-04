from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from math import isfinite
from typing import Any, Dict, Iterable, List, Mapping, Optional


FADEC_DECODER_VERSION = "1.1.0"


DEFAULT_SIGNAL_MAX_AGE_SECONDS = 2.0


SIGNAL_MAX_AGE_SECONDS: Dict[str, float] = {

    "engine_rpm": 1.0,
    "throttle_percent": 1.0,
    "load_percent": 1.0,
    "torque_nm": 1.0,
    "power_kw": 1.0,

    "cht_1_c": 3.0,
    "cht_2_c": 3.0,
    "cht_3_c": 3.0,
    "cht_4_c": 3.0,

    "egt_1_c": 2.0,
    "egt_2_c": 2.0,
    "egt_3_c": 2.0,
    "egt_4_c": 2.0,

    "oil_pressure_kpa": 2.0,
    "oil_temperature_c": 5.0,

    "fuel_pressure_kpa": 2.0,
    "fuel_flow_kg_per_second": 2.0,
    "injection_timing_deg": 2.0,

    "altitude_m": 5.0,
    "ambient_pressure_kpa": 5.0,
    "ambient_temperature_c": 10.0,
    "air_density_kg_m3": 5.0,

    "battery_voltage_v": 3.0,
    "battery_current_a": 3.0,
    "alternator_voltage_v": 3.0,
    "alternator_current_a": 3.0,

    "vibration_overall_g": 1.0,
    "vibration_x_g": 1.0,
    "vibration_y_g": 1.0,
    "vibration_z_g": 1.0,
}


class FADECDecoderError(Exception):
    pass


class InvalidCANFrameError(FADECDecoderError):
    pass


class SignalDecodeError(FADECDecoderError):
    pass


class ByteOrder(str, Enum):
    LITTLE = "little"
    BIG = "big"


class SignedMode(str, Enum):
    UNSIGNED = "unsigned"
    SIGNED = "signed"


@dataclass(slots=True)
class RawCANFrame:

    arbitration_id: int

    data: bytes

    timestamp: datetime = field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )

    is_extended_id: bool = False

    channel: Optional[str] = None

    is_remote_frame: bool = False

    is_error_frame: bool = False


@dataclass(frozen=True, slots=True)
class SignalDefinition:

    name: str

    byte_start: int

    byte_length: int

    scale: float = 1.0

    offset: float = 0.0

    byte_order: ByteOrder = ByteOrder.LITTLE

    signed_mode: SignedMode = SignedMode.UNSIGNED

    minimum: Optional[float] = None

    maximum: Optional[float] = None

    required: bool = False


@dataclass(frozen=True, slots=True)
class MessageDefinition:

    arbitration_id: int

    name: str

    signals: tuple[SignalDefinition, ...]

    minimum_dlc: int = 0

    is_extended_id: Optional[bool] = None

    description: str = ""


@dataclass(slots=True)
class DecodeResult:

    success: bool

    recognized: bool

    arbitration_id: int

    message_name: Optional[str]

    signals: Dict[str, Any]

    timestamp: datetime

    warnings: List[str] = field(
        default_factory=list
    )

    error: Optional[str] = None

    decoder_version: str = (
        FADEC_DECODER_VERSION
    )


    def to_dict(
        self,
    ) -> Dict[str, Any]:

        return {

            "success":
                self.success,

            "recognized":
                self.recognized,

            "arbitration_id":
                self.arbitration_id,

            "arbitration_id_hex":
                hex(
                    self.arbitration_id
                ),

            "message_name":
                self.message_name,

            "signals":
                dict(
                    self.signals
                ),

            "timestamp":
                self.timestamp.isoformat(),

            "warnings":
                list(
                    self.warnings
                ),

            "error":
                self.error,

            "decoder_version":
                self.decoder_version,
        }


DEMO_ENGINE_STATUS_ID = 0x100

DEMO_THERMAL_STATUS_ID = 0x101

DEMO_OIL_FUEL_STATUS_ID = 0x102

DEMO_ENVIRONMENT_ID = 0x103

DEMO_ELECTRICAL_ID = 0x104

DEMO_VIBRATION_ID = 0x105


DEFAULT_MESSAGE_DEFINITIONS: tuple[
    MessageDefinition,
    ...
] = (

    MessageDefinition(

        arbitration_id=(
            DEMO_ENGINE_STATUS_ID
        ),

        name="DEMO_ENGINE_STATUS",

        minimum_dlc=8,

        description=(
            "PRATIRUP demonstrator engine "
            "operating-state frame."
        ),

        signals=(

            SignalDefinition(
                name="engine_rpm",
                byte_start=0,
                byte_length=2,
                scale=1.0,
                minimum=0.0,
                maximum=10000.0,
                required=True,
            ),

            SignalDefinition(
                name="throttle_percent",
                byte_start=2,
                byte_length=1,
                scale=1.0,
                minimum=0.0,
                maximum=100.0,
                required=True,
            ),

            SignalDefinition(
                name="load_percent",
                byte_start=3,
                byte_length=1,
                scale=1.0,
                minimum=0.0,
                maximum=100.0,
                required=True,
            ),

            SignalDefinition(
                name="torque_nm",
                byte_start=4,
                byte_length=2,
                scale=0.1,
                minimum=0.0,
            ),

            SignalDefinition(
                name="power_kw",
                byte_start=6,
                byte_length=2,
                scale=0.1,
                minimum=0.0,
            ),
        ),
    ),


    MessageDefinition(

        arbitration_id=(
            DEMO_THERMAL_STATUS_ID
        ),

        name="DEMO_THERMAL_STATUS",

        minimum_dlc=8,

        description=(
            "PRATIRUP demonstrator "
            "cylinder thermal frame."
        ),

        signals=(

            SignalDefinition(
                name="cht_1_c",
                byte_start=0,
                byte_length=1,
                scale=1.0,
                offset=-40.0,
                minimum=-40.0,
                maximum=300.0,
            ),

            SignalDefinition(
                name="cht_2_c",
                byte_start=1,
                byte_length=1,
                scale=1.0,
                offset=-40.0,
                minimum=-40.0,
                maximum=300.0,
            ),

            SignalDefinition(
                name="cht_3_c",
                byte_start=2,
                byte_length=1,
                scale=1.0,
                offset=-40.0,
                minimum=-40.0,
                maximum=300.0,
            ),

            SignalDefinition(
                name="cht_4_c",
                byte_start=3,
                byte_length=1,
                scale=1.0,
                offset=-40.0,
                minimum=-40.0,
                maximum=300.0,
            ),

            SignalDefinition(
                name="egt_1_c",
                byte_start=4,
                byte_length=1,
                scale=4.0,
                minimum=0.0,
                maximum=1200.0,
            ),

            SignalDefinition(
                name="egt_2_c",
                byte_start=5,
                byte_length=1,
                scale=4.0,
                minimum=0.0,
                maximum=1200.0,
            ),

            SignalDefinition(
                name="egt_3_c",
                byte_start=6,
                byte_length=1,
                scale=4.0,
                minimum=0.0,
                maximum=1200.0,
            ),

            SignalDefinition(
                name="egt_4_c",
                byte_start=7,
                byte_length=1,
                scale=4.0,
                minimum=0.0,
                maximum=1200.0,
            ),
        ),
    ),


    MessageDefinition(

        arbitration_id=(
            DEMO_OIL_FUEL_STATUS_ID
        ),

        name="DEMO_OIL_FUEL_STATUS",

        minimum_dlc=8,

        description=(
            "PRATIRUP demonstrator "
            "oil and fuel frame."
        ),

        signals=(

            SignalDefinition(
                name="oil_pressure_kpa",
                byte_start=0,
                byte_length=2,
                scale=0.1,
                minimum=0.0,
                maximum=2000.0,
            ),

            SignalDefinition(
                name="oil_temperature_c",
                byte_start=2,
                byte_length=1,
                scale=1.0,
                offset=-40.0,
                minimum=-40.0,
                maximum=250.0,
            ),

            SignalDefinition(
                name="fuel_pressure_kpa",
                byte_start=3,
                byte_length=2,
                scale=0.1,
                minimum=0.0,
            ),

            SignalDefinition(
                name="fuel_flow_kg_per_second",
                byte_start=5,
                byte_length=2,
                scale=0.00001,
                minimum=0.0,
            ),

            SignalDefinition(
                name="injection_timing_deg",
                byte_start=7,
                byte_length=1,
                scale=1.0,
                offset=-50.0,
            ),
        ),
    ),


    MessageDefinition(

        arbitration_id=(
            DEMO_ENVIRONMENT_ID
        ),

        name="DEMO_ENVIRONMENT",

        minimum_dlc=7,

        description=(
            "PRATIRUP demonstrator "
            "environment frame."
        ),

        signals=(

            SignalDefinition(
                name="altitude_m",
                byte_start=0,
                byte_length=2,
                scale=1.0,
                minimum=0.0,
                maximum=30000.0,
            ),

            SignalDefinition(
                name="ambient_pressure_kpa",
                byte_start=2,
                byte_length=2,
                scale=0.1,
                minimum=0.0,
                maximum=150.0,
            ),

            SignalDefinition(
                name="ambient_temperature_c",
                byte_start=4,
                byte_length=1,
                scale=1.0,
                offset=-40.0,
                minimum=-80.0,
                maximum=80.0,
                required=True,
            ),

            SignalDefinition(
                name="air_density_kg_m3",
                byte_start=5,
                byte_length=2,
                scale=0.001,
                minimum=0.0,
                maximum=2.0,
            ),
        ),
    ),


    MessageDefinition(

        arbitration_id=(
            DEMO_ELECTRICAL_ID
        ),

        name="DEMO_ELECTRICAL",

        minimum_dlc=8,

        description=(
            "PRATIRUP demonstrator "
            "electrical-system frame."
        ),

        signals=(

            SignalDefinition(
                name="battery_voltage_v",
                byte_start=0,
                byte_length=2,
                scale=0.01,
                minimum=0.0,
                maximum=100.0,
            ),

            SignalDefinition(
                name="battery_current_a",
                byte_start=2,
                byte_length=2,
                scale=0.1,
                signed_mode=SignedMode.SIGNED,
            ),

            SignalDefinition(
                name="alternator_voltage_v",
                byte_start=4,
                byte_length=2,
                scale=0.01,
                minimum=0.0,
                maximum=100.0,
            ),

            SignalDefinition(
                name="alternator_current_a",
                byte_start=6,
                byte_length=2,
                scale=0.1,
                signed_mode=SignedMode.SIGNED,
            ),
        ),
    ),


    MessageDefinition(

        arbitration_id=(
            DEMO_VIBRATION_ID
        ),

        name="DEMO_VIBRATION",

        minimum_dlc=8,

        description=(
            "PRATIRUP demonstrator "
            "vibration frame."
        ),

        signals=(

            SignalDefinition(
                name="vibration_overall_g",
                byte_start=0,
                byte_length=2,
                scale=0.001,
                minimum=0.0,
            ),

            SignalDefinition(
                name="vibration_x_g",
                byte_start=2,
                byte_length=2,
                scale=0.001,
                signed_mode=SignedMode.SIGNED,
            ),

            SignalDefinition(
                name="vibration_y_g",
                byte_start=4,
                byte_length=2,
                scale=0.001,
                signed_mode=SignedMode.SIGNED,
            ),

            SignalDefinition(
                name="vibration_z_g",
                byte_start=6,
                byte_length=2,
                scale=0.001,
                signed_mode=SignedMode.SIGNED,
            ),
        ),
    ),
)


_decoded_frames: int = 0

_failed_frames: int = 0

_unknown_frames: int = 0

_out_of_range_signals: int = 0

_latest_result: Optional[
    DecodeResult
] = None

_latest_error: Optional[
    str
] = None


class FADECDecoder:

    def __init__(
        self,
        definitions: Optional[
            Iterable[MessageDefinition]
        ] = None,
    ) -> None:

        selected = (
            tuple(definitions)
            if definitions is not None
            else DEFAULT_MESSAGE_DEFINITIONS
        )

        self._definitions: Dict[
            int,
            MessageDefinition,
        ] = {}

        for definition in selected:

            self.register_message(
                definition
            )


    def register_message(
        self,
        definition: MessageDefinition,
    ) -> None:

        if definition.arbitration_id < 0:

            raise ValueError(
                "CAN arbitration ID cannot be negative."
            )

        self._definitions[
            definition.arbitration_id
        ] = definition


    def unregister_message(
        self,
        arbitration_id: int,
    ) -> bool:

        return (
            self._definitions.pop(
                arbitration_id,
                None,
            )
            is not None
        )


    def get_message_definition(
        self,
        arbitration_id: int,
    ) -> Optional[
        MessageDefinition
    ]:

        return self._definitions.get(
            arbitration_id
        )


    def get_registered_messages(
        self,
    ) -> List[
        Dict[str, Any]
    ]:

        messages: List[
            Dict[str, Any]
        ] = []

        for definition in (
            self._definitions.values()
        ):

            messages.append(
                {
                    "arbitration_id":
                        definition.arbitration_id,

                    "arbitration_id_hex":
                        hex(
                            definition.arbitration_id
                        ),

                    "name":
                        definition.name,

                    "minimum_dlc":
                        definition.minimum_dlc,

                    "is_extended_id":
                        definition.is_extended_id,

                    "description":
                        definition.description,

                    "signals": [
                        signal.name
                        for signal
                        in definition.signals
                    ],
                }
            )

        return messages


    @staticmethod
    def _validate_frame(
        frame: RawCANFrame,
    ) -> None:

        if not isinstance(
            frame.arbitration_id,
            int,
        ):

            raise InvalidCANFrameError(
                "CAN arbitration_id must be an integer."
            )


        if frame.arbitration_id < 0:

            raise InvalidCANFrameError(
                "CAN arbitration_id cannot be negative."
            )


        if not isinstance(
            frame.data,
            bytes,
        ):

            raise InvalidCANFrameError(
                "CAN frame data must be bytes."
            )


        if len(frame.data) > 64:

            raise InvalidCANFrameError(
                "CAN payload exceeds 64 bytes."
            )


        if frame.is_remote_frame:

            raise InvalidCANFrameError(
                (
                    "Remote CAN frames do not "
                    "contain telemetry payload."
                )
            )


        if frame.is_error_frame:

            raise InvalidCANFrameError(
                (
                    "CAN error frame cannot be "
                    "decoded as telemetry."
                )
            )


    @staticmethod
    def _decode_signal(
        payload: bytes,
        signal: SignalDefinition,
    ) -> Optional[float]:

        start = (
            signal.byte_start
        )

        end = (
            signal.byte_start
            + signal.byte_length
        )


        if start < 0:

            raise SignalDecodeError(
                (
                    f"{signal.name}: "
                    f"negative byte_start."
                )
            )


        if signal.byte_length <= 0:

            raise SignalDecodeError(
                (
                    f"{signal.name}: "
                    f"byte_length must be positive."
                )
            )


        if end > len(payload):

            return None


        raw_bytes = payload[
            start:end
        ]


        signed = (
            signal.signed_mode
            == SignedMode.SIGNED
        )


        raw_value = int.from_bytes(
            raw_bytes,
            byteorder=(
                signal.byte_order.value
            ),
            signed=signed,
        )


        value = (
            raw_value
            * signal.scale
            + signal.offset
        )


        value = float(
            value
        )


        if not isfinite(
            value
        ):

            raise SignalDecodeError(
                (
                    f"{signal.name}: "
                    f"decoded non-finite value."
                )
            )


        return value


    def decode(
        self,
        frame: RawCANFrame,
    ) -> DecodeResult:

        global _decoded_frames
        global _failed_frames
        global _unknown_frames
        global _out_of_range_signals
        global _latest_result
        global _latest_error


        try:

            self._validate_frame(
                frame
            )


            definition = (
                self.get_message_definition(
                    frame.arbitration_id
                )
            )


            if definition is None:

                _unknown_frames += 1


                result = DecodeResult(

                    success=True,

                    recognized=False,

                    arbitration_id=(
                        frame.arbitration_id
                    ),

                    message_name=None,

                    signals={},

                    timestamp=(
                        frame.timestamp
                    ),

                    warnings=[
                        (
                            "No FADEC message definition "
                            "registered for this "
                            "arbitration ID."
                        )
                    ],
                )


                _latest_result = result

                _latest_error = None


                return result


            if (
                definition.is_extended_id
                is not None
                and
                frame.is_extended_id
                != definition.is_extended_id
            ):

                raise InvalidCANFrameError(
                    (
                        f"{definition.name}: "
                        f"extended-ID configuration "
                        f"does not match frame."
                    )
                )


            if (
                len(frame.data)
                < definition.minimum_dlc
            ):

                raise InvalidCANFrameError(
                    (
                        f"{definition.name}: "
                        f"payload length "
                        f"{len(frame.data)} "
                        f"is below required DLC "
                        f"{definition.minimum_dlc}."
                    )
                )


            signals: Dict[
                str,
                Any,
            ] = {}


            warnings: List[
                str
            ] = []


            for signal in (
                definition.signals
            ):

                value = (
                    self._decode_signal(
                        frame.data,
                        signal,
                    )
                )


                if value is None:

                    signals[
                        signal.name
                    ] = None


                    if signal.required:

                        warnings.append(
                            (
                                f"Required signal "
                                f"{signal.name} "
                                f"is unavailable."
                            )
                        )


                    continue


                out_of_range = False


                if (
                    signal.minimum
                    is not None
                    and
                    value
                    < signal.minimum
                ):

                    out_of_range = True


                if (
                    signal.maximum
                    is not None
                    and
                    value
                    > signal.maximum
                ):

                    out_of_range = True


                if out_of_range:

                    _out_of_range_signals += 1


                    warnings.append(
                        (
                            f"{signal.name} "
                            f"decoded value {value} "
                            f"is outside configured "
                            f"engineering range."
                        )
                    )


                    signals[
                        signal.name
                    ] = None


                    continue


                signals[
                    signal.name
                ] = value


            _decoded_frames += 1


            result = DecodeResult(

                success=True,

                recognized=True,

                arbitration_id=(
                    frame.arbitration_id
                ),

                message_name=(
                    definition.name
                ),

                signals=signals,

                timestamp=(
                    frame.timestamp
                ),

                warnings=warnings,
            )


            _latest_result = result

            _latest_error = None


            return result


        except Exception as exc:

            _failed_frames += 1


            _latest_error = str(
                exc
            )


            result = DecodeResult(

                success=False,

                recognized=(
                    frame.arbitration_id
                    in self._definitions
                ),

                arbitration_id=(
                    frame.arbitration_id
                ),

                message_name=(
                    self._definitions[
                        frame.arbitration_id
                    ].name
                    if frame.arbitration_id
                    in self._definitions
                    else None
                ),

                signals={},

                timestamp=(
                    frame.timestamp
                ),

                warnings=[],

                error=str(
                    exc
                ),
            )


            _latest_result = result


            return result


_default_decoder = FADECDecoder()


class FADECSignalAggregator:

    def __init__(
        self,
        default_max_age_seconds: float = (
            DEFAULT_SIGNAL_MAX_AGE_SECONDS
        ),
        signal_max_age_seconds: Optional[
            Mapping[str, float]
        ] = None,
    ) -> None:

        if (
            default_max_age_seconds
            <= 0
        ):

            raise ValueError(
                (
                    "default_max_age_seconds "
                    "must be positive."
                )
            )


        self._signals: Dict[
            str,
            Any,
        ] = {}


        self._last_update: Dict[
            str,
            datetime,
        ] = {}


        self._source_message: Dict[
            str,
            str,
        ] = {}


        self._default_max_age_seconds = (
            float(
                default_max_age_seconds
            )
        )


        self._max_age = dict(
            SIGNAL_MAX_AGE_SECONDS
        )


        if signal_max_age_seconds:

            for (
                name,
                age,
            ) in signal_max_age_seconds.items():

                age_value = float(
                    age
                )


                if age_value <= 0:

                    raise ValueError(
                        (
                            f"Maximum age for "
                            f"{name} must be positive."
                        )
                    )


                self._max_age[
                    name
                ] = age_value


        self._sequence: int = 0

        self._update_count: int = 0

        self._stale_rejections: int = 0

        self._invalid_timestamp_count: int = 0


    @staticmethod
    def _normalize_timestamp(
        timestamp: datetime,
    ) -> datetime:

        if not isinstance(
            timestamp,
            datetime,
        ):

            raise TypeError(
                (
                    "Signal timestamp "
                    "must be a datetime."
                )
            )


        if timestamp.tzinfo is None:

            return timestamp.replace(
                tzinfo=timezone.utc
            )


        return timestamp.astimezone(
            timezone.utc
        )


    def get_signal_max_age(
        self,
        signal_name: str,
    ) -> float:

        return float(
            self._max_age.get(
                signal_name,
                self._default_max_age_seconds,
            )
        )


    def update(
        self,
        result: DecodeResult,
    ) -> None:

        if not result.success:

            return


        if not result.recognized:

            return


        try:

            timestamp = (
                self._normalize_timestamp(
                    result.timestamp
                )
            )

        except Exception:

            self._invalid_timestamp_count += 1

            return


        for (
            name,
            value,
        ) in result.signals.items():

            if value is None:

                continue


            self._signals[
                name
            ] = value


            self._last_update[
                name
            ] = timestamp


            if result.message_name:

                self._source_message[
                    name
                ] = result.message_name


        self._sequence += 1

        self._update_count += 1


    def signal_age_seconds(
        self,
        signal_name: str,
        *,
        now: Optional[
            datetime
        ] = None,
    ) -> Optional[float]:

        timestamp = (
            self._last_update.get(
                signal_name
            )
        )


        if timestamp is None:

            return None


        current_time = (
            self._normalize_timestamp(
                now
                if now is not None
                else datetime.now(
                    timezone.utc
                )
            )
        )


        age = (
            current_time
            - timestamp
        ).total_seconds()


        return max(
            0.0,
            float(
                age
            ),
        )


    def is_signal_fresh(
        self,
        signal_name: str,
        *,
        now: Optional[
            datetime
        ] = None,
    ) -> bool:

        age = (
            self.signal_age_seconds(
                signal_name,
                now=now,
            )
        )


        if age is None:

            return False


        return (
            age
            <= self.get_signal_max_age(
                signal_name
            )
        )


    def get_signal(
        self,
        signal_name: str,
        *,
        now: Optional[
            datetime
        ] = None,
        include_stale: bool = False,
    ) -> Any:

        if (
            signal_name
            not in self._signals
        ):

            return None


        if include_stale:

            return self._signals[
                signal_name
            ]


        if not self.is_signal_fresh(
            signal_name,
            now=now,
        ):

            return None


        return self._signals[
            signal_name
        ]


    def snapshot(
        self,
        *,
        timestamp: Optional[
            datetime
        ] = None,
        include_stale: bool = False,
        include_stale_as_none: bool = True,
    ) -> Dict[str, Any]:

        current_time = (
            self._normalize_timestamp(
                timestamp
                if timestamp is not None
                else datetime.now(
                    timezone.utc
                )
            )
        )


        output: Dict[
            str,
            Any,
        ] = {}


        for (
            name,
            value,
        ) in self._signals.items():

            fresh = (
                self.is_signal_fresh(
                    name,
                    now=current_time,
                )
            )


            if fresh:

                output[
                    name
                ] = value

                continue


            if include_stale:

                output[
                    name
                ] = value

                continue


            if include_stale_as_none:

                output[
                    name
                ] = None


        output[
            "timestamp"
        ] = current_time


        output[
            "sequence"
        ] = self._sequence


        return output


    def fresh_snapshot(
        self,
        *,
        timestamp: Optional[
            datetime
        ] = None,
    ) -> Dict[str, Any]:

        return self.snapshot(
            timestamp=timestamp,
            include_stale=False,
            include_stale_as_none=False,
        )


    def get_stale_signals(
        self,
        *,
        now: Optional[
            datetime
        ] = None,
    ) -> List[str]:

        stale: List[
            str
        ] = []


        for signal_name in (
            self._signals
        ):

            if not self.is_signal_fresh(
                signal_name,
                now=now,
            ):

                stale.append(
                    signal_name
                )


        return sorted(
            stale
        )


    def get_fresh_signals(
        self,
        *,
        now: Optional[
            datetime
        ] = None,
    ) -> List[str]:

        fresh: List[
            str
        ] = []


        for signal_name in (
            self._signals
        ):

            if self.is_signal_fresh(
                signal_name,
                now=now,
            ):

                fresh.append(
                    signal_name
                )


        return sorted(
            fresh
        )


    def purge_stale(
        self,
        *,
        now: Optional[
            datetime
        ] = None,
    ) -> int:

        stale = (
            self.get_stale_signals(
                now=now
            )
        )


        for name in stale:

            self._signals.pop(
                name,
                None,
            )

            self._last_update.pop(
                name,
                None,
            )

            self._source_message.pop(
                name,
                None,
            )


        removed = len(
            stale
        )


        self._stale_rejections += (
            removed
        )


        return removed


    def get_signal_details(
        self,
        *,
        now: Optional[
            datetime
        ] = None,
    ) -> Dict[
        str,
        Dict[str, Any]
    ]:

        current_time = (
            self._normalize_timestamp(
                now
                if now is not None
                else datetime.now(
                    timezone.utc
                )
            )
        )


        details: Dict[
            str,
            Dict[str, Any],
        ] = {}


        for (
            name,
            value,
        ) in self._signals.items():

            age = (
                self.signal_age_seconds(
                    name,
                    now=current_time,
                )
            )


            maximum_age = (
                self.get_signal_max_age(
                    name
                )
            )


            fresh = (
                age is not None
                and
                age <= maximum_age
            )


            details[
                name
            ] = {

                "value":
                    value,

                "fresh":
                    fresh,

                "age_seconds":
                    age,

                "maximum_age_seconds":
                    maximum_age,

                "last_update":
                    (
                        self._last_update[
                            name
                        ].isoformat()
                        if name
                        in self._last_update
                        else None
                    ),

                "source_message":
                    self._source_message.get(
                        name
                    ),
            }


        return details


    def clear(
        self,
    ) -> None:

        self._signals.clear()

        self._last_update.clear()

        self._source_message.clear()


        self._sequence = 0

        self._update_count = 0

        self._stale_rejections = 0

        self._invalid_timestamp_count = 0


    def status(
        self,
    ) -> Dict[str, Any]:

        now = datetime.now(
            timezone.utc
        )


        fresh = (
            self.get_fresh_signals(
                now=now
            )
        )


        stale = (
            self.get_stale_signals(
                now=now
            )
        )


        total = len(
            self._signals
        )


        freshness_fraction = (
            len(fresh) / total
            if total > 0
            else 0.0
        )


        return {

            "status":
                "READY",

            "stored_signals":
                total,

            "fresh_signals":
                len(fresh),

            "stale_signals":
                len(stale),

            "freshness_fraction":
                freshness_fraction,

            "freshness_percent":
                freshness_fraction
                * 100.0,

            "sequence":
                self._sequence,

            "update_count":
                self._update_count,

            "stale_rejections":
                self._stale_rejections,

            "invalid_timestamp_count":
                self._invalid_timestamp_count,

            "default_max_age_seconds":
                self._default_max_age_seconds,

            "fresh_signal_names":
                fresh,

            "stale_signal_names":
                stale,

            "signal_details":
                self.get_signal_details(
                    now=now
                ),

            "timestamp":
                now.isoformat(),
        }


_default_aggregator = (
    FADECSignalAggregator()
)


def decode_can_frame(
    frame: RawCANFrame,
) -> DecodeResult:

    return _default_decoder.decode(
        frame
    )


def decode_raw_frame(
    arbitration_id: int,
    data: bytes,
    *,
    timestamp: Optional[
        datetime
    ] = None,
    is_extended_id: bool = False,
    channel: Optional[str] = None,
) -> DecodeResult:

    frame = RawCANFrame(

        arbitration_id=(
            arbitration_id
        ),

        data=data,

        timestamp=(
            timestamp
            if timestamp is not None
            else datetime.now(
                timezone.utc
            )
        ),

        is_extended_id=(
            is_extended_id
        ),

        channel=channel,
    )


    return decode_can_frame(
        frame
    )


def decode_and_aggregate(
    frame: RawCANFrame,
) -> DecodeResult:

    result = decode_can_frame(
        frame
    )


    _default_aggregator.update(
        result
    )


    return result


def get_aggregated_signals(
) -> Dict[str, Any]:

    return (
        _default_aggregator.snapshot()
    )


def get_fresh_aggregated_signals(
) -> Dict[str, Any]:

    return (
        _default_aggregator
        .fresh_snapshot()
    )


def get_aggregator_status(
) -> Dict[str, Any]:

    return (
        _default_aggregator.status()
    )


def purge_stale_signals(
) -> int:

    return (
        _default_aggregator
        .purge_stale()
    )


async def decode_and_ingest(
    frame: RawCANFrame,
):

    result = decode_can_frame(
        frame
    )


    if not result.success:

        raise FADECDecoderError(
            result.error
            or "FADEC decoding failed."
        )


    if not result.recognized:

        return None


    if not result.signals:

        return None


    from backend.ingestion.can_adapter import (
        process_can_signals,
    )


    signals = dict(
        result.signals
    )


    signals[
        "timestamp"
    ] = result.timestamp


    return await process_can_signals(
        signals
    )


async def ingest_aggregated_telemetry():

    from backend.ingestion.can_adapter import (
        process_can_signals,
    )


    signals = (
        _default_aggregator.snapshot()
    )


    return await process_can_signals(
        signals
    )


def get_fadec_decoder_status(
) -> Dict[str, Any]:

    return {

        "service":
            "fadec_decoder",

        "status":
            "READY",

        "version":
            FADEC_DECODER_VERSION,

        "decoder_type":
            "CONFIGURABLE",

        "default_mapping":
            "PRATIRUP_DEMONSTRATOR",

        "hardware_mapping_verified":
            False,

        "registered_messages":
            len(
                _default_decoder
                .get_registered_messages()
            ),

        "decoded_frames":
            _decoded_frames,

        "failed_frames":
            _failed_frames,

        "unknown_frames":
            _unknown_frames,

        "out_of_range_signals":
            _out_of_range_signals,

        "latest_result":
            (
                _latest_result.to_dict()
                if _latest_result
                is not None
                else None
            ),

        "latest_error":
            _latest_error,

        "aggregator":
            _default_aggregator.status(),

        "freshness_protection":
            True,

        "null_policy":
            (
                "None = unavailable, invalid or stale; "
                "zero = genuine decoded zero"
            ),

        "timestamp":
            datetime.now(
                timezone.utc
            ).isoformat(),
    }


def get_fadec_decoder_info(
) -> Dict[str, Any]:

    return {

        "name":
            "PRATIRUP Configurable FADEC Decoder",

        "version":
            FADEC_DECODER_VERSION,

        "input":
            "RawCANFrame",

        "output":
            "Fresh decoded engineering signals",

        "byte_aligned_signals":
            True,

        "configurable":
            True,

        "can_classic_supported":
            True,

        "can_fd_payload_supported":
            True,

        "transport_independent":
            True,

        "freshness_protection":
            True,

        "official_vrde_mapping":
            False,

        "message_definitions":
            (
                _default_decoder
                .get_registered_messages()
            ),

        "next_stage":
            "backend.ingestion.socketcan",

        "engineering_disclaimer":
            (
                "Default IDs and layouts are PRATIRUP "
                "demonstrator definitions only. Verified "
                "hardware integration requires authorized "
                "CAN/FADEC interface definitions."
            ),
    }


def reset_fadec_decoder(
) -> None:

    global _decoded_frames
    global _failed_frames
    global _unknown_frames
    global _out_of_range_signals
    global _latest_result
    global _latest_error


    _decoded_frames = 0

    _failed_frames = 0

    _unknown_frames = 0

    _out_of_range_signals = 0

    _latest_result = None

    _latest_error = None


    _default_aggregator.clear()
