from __future__ import annotations

import asyncio

from abc import ABC, abstractmethod

from collections import deque

from dataclasses import dataclass

from datetime import datetime, timezone

from enum import Enum

from math import isfinite

from typing import (
    Any,
    Deque,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
)


from backend.ingestion.fadec_decoder import (
    DecodeResult,
    RawCANFrame,
    decode_and_aggregate,
    decode_can_frame,
    get_aggregated_signals,
    get_fresh_aggregated_signals,
    get_aggregator_status,
)


CAN_TRANSPORT_VERSION = "1.1.0"


try:

    import can

    PYTHON_CAN_AVAILABLE = True

except ImportError:

    can = None

    PYTHON_CAN_AVAILABLE = False


DEFAULT_REQUIRED_CAN_SIGNALS: Tuple[str, ...] = (
    "engine_rpm",
    "throttle_percent",
    "load_percent",
    "ambient_temperature_c",
)


class CANTransportError(Exception):
    pass


class CANTransportNotConnectedError(
    CANTransportError
):
    pass


class CANTransportConfigurationError(
    CANTransportError
):
    pass


class CANTransportType(str, Enum):

    VIRTUAL = "virtual"

    PYTHON_CAN = "python_can"

    SOCKETCAN = "socketcan"

    HARDWARE = "hardware"


class CANTransportState(str, Enum):

    DISCONNECTED = "DISCONNECTED"

    CONNECTING = "CONNECTING"

    CONNECTED = "CONNECTED"

    STOPPING = "STOPPING"

    ERROR = "ERROR"


@dataclass(slots=True)
class CANTransportConfig:

    transport_type: CANTransportType = (
        CANTransportType.VIRTUAL
    )

    interface: str = "virtual"

    channel: Optional[str] = None

    bitrate: Optional[int] = 500000

    receive_timeout_seconds: float = 0.1

    receive_poll_seconds: float = 0.01

    auto_aggregate: bool = True

    auto_ingest: bool = False

    required_signals: Tuple[str, ...] = (
        DEFAULT_REQUIRED_CAN_SIGNALS
    )

    minimum_ingestion_interval_seconds: float = 0.05


@dataclass(slots=True)
class CANReadinessResult:

    ready: bool

    required_signals: Tuple[str, ...]

    available_signals: List[str]

    missing_signals: List[str]

    invalid_signals: List[str]

    coverage: float

    timestamp: datetime


    def to_dict(
        self,
    ) -> Dict[str, Any]:

        return {

            "ready":
                self.ready,

            "required_signals":
                list(
                    self.required_signals
                ),

            "available_signals":
                list(
                    self.available_signals
                ),

            "missing_signals":
                list(
                    self.missing_signals
                ),

            "invalid_signals":
                list(
                    self.invalid_signals
                ),

            "coverage":
                self.coverage,

            "coverage_percent":
                self.coverage * 100.0,

            "timestamp":
                self.timestamp.isoformat(),
        }


@dataclass(slots=True)
class CANReceiveResult:

    received: bool

    frame: Optional[RawCANFrame]

    decode_result: Optional[DecodeResult]

    readiness: Optional[CANReadinessResult] = None

    ingested: bool = False

    ingestion_error: Optional[str] = None


    def to_dict(
        self,
    ) -> Dict[str, Any]:

        return {

            "received":
                self.received,

            "frame":
                (
                    {
                        "arbitration_id":
                            self.frame.arbitration_id,

                        "arbitration_id_hex":
                            hex(
                                self.frame.arbitration_id
                            ),

                        "data_hex":
                            self.frame.data.hex(),

                        "dlc":
                            len(
                                self.frame.data
                            ),

                        "timestamp":
                            self.frame.timestamp.isoformat(),

                        "is_extended_id":
                            self.frame.is_extended_id,

                        "channel":
                            self.frame.channel,
                    }

                    if self.frame is not None

                    else None
                ),

            "decode_result":
                (
                    self.decode_result.to_dict()

                    if self.decode_result is not None

                    else None
                ),

            "readiness":
                (
                    self.readiness.to_dict()

                    if self.readiness is not None

                    else None
                ),

            "ingested":
                self.ingested,

            "ingestion_error":
                self.ingestion_error,
        }


def _is_valid_engineering_value(
    value: Any,
) -> bool:

    if value is None:

        return False


    if isinstance(
        value,
        bool,
    ):

        return False


    if not isinstance(
        value,
        (int, float),
    ):

        return False


    return isfinite(
        float(value)
    )


def evaluate_can_snapshot_readiness(
    signals: Mapping[str, Any],
    required_signals: Sequence[str] = (
        DEFAULT_REQUIRED_CAN_SIGNALS
    ),
) -> CANReadinessResult:

    required = tuple(
        required_signals
    )


    available: List[str] = []

    missing: List[str] = []

    invalid: List[str] = []


    for name in required:

        if name not in signals:

            missing.append(
                name
            )

            continue


        value = signals.get(
            name
        )


        if value is None:

            missing.append(
                name
            )

            continue


        if not _is_valid_engineering_value(
            value
        ):

            invalid.append(
                name
            )

            continue


        available.append(
            name
        )


    total = len(
        required
    )


    coverage = (
        len(available) / total

        if total > 0

        else 1.0
    )


    ready = (
        len(missing) == 0
        and
        len(invalid) == 0
    )


    return CANReadinessResult(

        ready=ready,

        required_signals=required,

        available_signals=available,

        missing_signals=missing,

        invalid_signals=invalid,

        coverage=coverage,

        timestamp=datetime.now(
            timezone.utc
        ),
    )


class BaseCANTransport(ABC):

    def __init__(
        self,
        config: CANTransportConfig,
    ) -> None:

        self.config = config

        self.state = (
            CANTransportState.DISCONNECTED
        )

        self.last_error: Optional[
            str
        ] = None


    @abstractmethod
    async def connect(
        self,
    ) -> None:
        pass


    @abstractmethod
    async def disconnect(
        self,
    ) -> None:
        pass


    @abstractmethod
    async def receive(
        self,
    ) -> Optional[RawCANFrame]:
        pass


    @abstractmethod
    async def send(
        self,
        frame: RawCANFrame,
    ) -> None:
        pass


    def is_connected(
        self,
    ) -> bool:

        return (
            self.state
            == CANTransportState.CONNECTED
        )


class VirtualCANTransport(
    BaseCANTransport
):

    def __init__(
        self,
        config: Optional[
            CANTransportConfig
        ] = None,
    ) -> None:

        if config is None:

            config = CANTransportConfig(
                transport_type=(
                    CANTransportType.VIRTUAL
                ),
                interface="virtual",
            )


        super().__init__(
            config
        )


        self._rx_queue: Deque[
            RawCANFrame
        ] = deque()


        self._tx_queue: Deque[
            RawCANFrame
        ] = deque()


    async def connect(
        self,
    ) -> None:

        self.state = (
            CANTransportState.CONNECTING
        )

        self.last_error = None

        self.state = (
            CANTransportState.CONNECTED
        )


    async def disconnect(
        self,
    ) -> None:

        self.state = (
            CANTransportState.STOPPING
        )

        self.state = (
            CANTransportState.DISCONNECTED
        )


    async def receive(
        self,
    ) -> Optional[
        RawCANFrame
    ]:

        if not self.is_connected():

            raise (
                CANTransportNotConnectedError(
                    "Virtual CAN transport is not connected."
                )
            )


        if not self._rx_queue:

            return None


        return self._rx_queue.popleft()


    async def send(
        self,
        frame: RawCANFrame,
    ) -> None:

        if not self.is_connected():

            raise (
                CANTransportNotConnectedError(
                    "Virtual CAN transport is not connected."
                )
            )


        self._tx_queue.append(
            frame
        )


    def inject_frame(
        self,
        frame: RawCANFrame,
    ) -> None:

        self._rx_queue.append(
            frame
        )


    def inject_raw(
        self,
        arbitration_id: int,
        data: bytes,
        *,
        is_extended_id: bool = False,
        timestamp: Optional[
            datetime
        ] = None,
    ) -> RawCANFrame:

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

            channel=(
                self.config.channel
                or "virtual"
            ),
        )


        self.inject_frame(
            frame
        )


        return frame


    def pending_receive_frames(
        self,
    ) -> int:

        return len(
            self._rx_queue
        )


    def pending_transmit_frames(
        self,
    ) -> int:

        return len(
            self._tx_queue
        )


    def get_transmitted_frames(
        self,
    ) -> List[RawCANFrame]:

        return list(
            self._tx_queue
        )


    def clear(
        self,
    ) -> None:

        self._rx_queue.clear()

        self._tx_queue.clear()


class PythonCANTransport(
    BaseCANTransport
):

    def __init__(
        self,
        config: CANTransportConfig,
    ) -> None:

        super().__init__(
            config
        )

        self._bus: Any = None


    async def connect(
        self,
    ) -> None:

        if not PYTHON_CAN_AVAILABLE:

            self.state = (
                CANTransportState.ERROR
            )

            self.last_error = (
                "python-can is not installed."
            )

            raise (
                CANTransportConfigurationError(
                    (
                        "python-can is not installed. "
                        "Virtual CAN mode remains available."
                    )
                )
            )


        self.state = (
            CANTransportState.CONNECTING
        )


        try:

            kwargs: Dict[
                str,
                Any,
            ] = {

                "interface":
                    self.config.interface,
            }


            if (
                self.config.channel
                is not None
            ):

                kwargs[
                    "channel"
                ] = self.config.channel


            if (
                self.config.bitrate
                is not None
                and
                self.config.interface
                != "virtual"
            ):

                kwargs[
                    "bitrate"
                ] = self.config.bitrate


            self._bus = (
                await asyncio.to_thread(
                    can.Bus,
                    **kwargs,
                )
            )


            self.state = (
                CANTransportState.CONNECTED
            )

            self.last_error = None


        except Exception as exc:

            self.state = (
                CANTransportState.ERROR
            )

            self.last_error = str(
                exc
            )

            raise CANTransportError(
                (
                    "Unable to connect CAN transport: "
                    f"{exc}"
                )
            ) from exc


    async def disconnect(
        self,
    ) -> None:

        self.state = (
            CANTransportState.STOPPING
        )


        if self._bus is not None:

            try:

                await asyncio.to_thread(
                    self._bus.shutdown
                )

            finally:

                self._bus = None


        self.state = (
            CANTransportState.DISCONNECTED
        )


    async def receive(
        self,
    ) -> Optional[
        RawCANFrame
    ]:

        if not self.is_connected():

            raise (
                CANTransportNotConnectedError(
                    "python-can transport is not connected."
                )
            )


        message = (
            await asyncio.to_thread(
                self._bus.recv,
                self.config.receive_timeout_seconds,
            )
        )


        if message is None:

            return None


        message_timestamp = getattr(
            message,
            "timestamp",
            None,
        )


        if message_timestamp is not None:

            timestamp = (
                datetime.fromtimestamp(
                    float(
                        message_timestamp
                    ),
                    tz=timezone.utc,
                )
            )

        else:

            timestamp = (
                datetime.now(
                    timezone.utc
                )
            )


        message_channel = getattr(
            message,
            "channel",
            self.config.channel,
        )


        return RawCANFrame(

            arbitration_id=int(
                message.arbitration_id
            ),

            data=bytes(
                message.data
            ),

            timestamp=timestamp,

            is_extended_id=bool(
                getattr(
                    message,
                    "is_extended_id",
                    False,
                )
            ),

            channel=(
                str(
                    message_channel
                )

                if message_channel
                is not None

                else None
            ),

            is_remote_frame=bool(
                getattr(
                    message,
                    "is_remote_frame",
                    False,
                )
            ),

            is_error_frame=bool(
                getattr(
                    message,
                    "is_error_frame",
                    False,
                )
            ),
        )


    async def send(
        self,
        frame: RawCANFrame,
    ) -> None:

        if not self.is_connected():

            raise (
                CANTransportNotConnectedError(
                    "python-can transport is not connected."
                )
            )


        message = can.Message(

            arbitration_id=(
                frame.arbitration_id
            ),

            data=frame.data,

            is_extended_id=(
                frame.is_extended_id
            ),
        )


        await asyncio.to_thread(
            self._bus.send,
            message,
        )


def create_transport(
    config: Optional[
        CANTransportConfig
    ] = None,
) -> BaseCANTransport:

    if config is None:

        config = CANTransportConfig()


    if (
        config.transport_type
        == CANTransportType.VIRTUAL
    ):

        return VirtualCANTransport(
            config
        )


    if (
        config.transport_type
        in {
            CANTransportType.PYTHON_CAN,
            CANTransportType.SOCKETCAN,
            CANTransportType.HARDWARE,
        }
    ):

        return PythonCANTransport(
            config
        )


    raise CANTransportConfigurationError(
        (
            "Unsupported CAN transport type: "
            f"{config.transport_type}"
        )
    )


class CANTransportService:

    def __init__(
        self,
        transport: BaseCANTransport,
    ) -> None:

        self.transport = transport


        self._running = False


        self._frames_received = 0

        self._frames_decoded = 0

        self._frames_unknown = 0

        self._decode_failures = 0


        self._readiness_checks = 0

        self._ready_snapshots = 0

        self._not_ready_snapshots = 0


        self._ingestion_attempts = 0

        self._ingestion_successes = 0

        self._ingestion_failures = 0

        self._ingestion_rate_limited = 0


        self._latest_frame: Optional[
            RawCANFrame
        ] = None


        self._latest_decode_result: Optional[
            DecodeResult
        ] = None


        self._latest_readiness: Optional[
            CANReadinessResult
        ] = None


        self._latest_error: Optional[
            str
        ] = None


        self._latest_ingestion_error: Optional[
            str
        ] = None


        self._started_at: Optional[
            datetime
        ] = None


        self._last_ingestion_at: Optional[
            datetime
        ] = None


    async def start(
        self,
    ) -> None:

        if self._running:

            return


        await self.transport.connect()


        self._running = True


        self._started_at = (
            datetime.now(
                timezone.utc
            )
        )


        self._latest_error = None


    async def stop(
        self,
    ) -> None:

        self._running = False

        await self.transport.disconnect()


    def _ingestion_interval_ready(
        self,
        now: datetime,
    ) -> bool:

        minimum_interval = max(
            0.0,
            float(
                self.transport
                .config
                .minimum_ingestion_interval_seconds
            ),
        )


        if minimum_interval == 0.0:

            return True


        if self._last_ingestion_at is None:

            return True


        elapsed = (
            now
            - self._last_ingestion_at
        ).total_seconds()


        return (
            elapsed
            >= minimum_interval
        )


    def evaluate_readiness(
        self,
    ) -> CANReadinessResult:

        signals = (
            get_aggregated_signals()
        )


        result = (
            evaluate_can_snapshot_readiness(

                signals,

                self.transport
                .config
                .required_signals,
            )
        )


        self._readiness_checks += 1


        if result.ready:

            self._ready_snapshots += 1

        else:

            self._not_ready_snapshots += 1


        self._latest_readiness = (
            result
        )


        return result


    async def process_frame(
        self,
        frame: RawCANFrame,
    ) -> CANReceiveResult:

        self._frames_received += 1

        self._latest_frame = frame


        try:

            if (
                self.transport
                .config
                .auto_aggregate
            ):

                result = (
                    decode_and_aggregate(
                        frame
                    )
                )

            else:

                result = (
                    decode_can_frame(
                        frame
                    )
                )


            self._latest_decode_result = (
                result
            )


            if result.success:

                if result.recognized:

                    self._frames_decoded += 1

                else:

                    self._frames_unknown += 1

            else:

                self._decode_failures += 1


            readiness: Optional[
                CANReadinessResult
            ] = None


            if (
                self.transport
                .config
                .auto_aggregate
                and
                result.success
                and
                result.recognized
            ):

                readiness = (
                    self.evaluate_readiness()
                )


            ingested = False

            ingestion_error = None


            if (
                self.transport
                .config
                .auto_ingest
                and
                readiness is not None
                and
                readiness.ready
            ):

                now = datetime.now(
                    timezone.utc
                )


                if not self._ingestion_interval_ready(
                    now
                ):

                    self._ingestion_rate_limited += 1

                else:

                    self._ingestion_attempts += 1


                    try:

                        from backend.ingestion.can_adapter import (
                            process_can_signals,
                        )


                        signals = (
                            get_fresh_aggregated_signals()
                        )


                        await process_can_signals(
                            signals
                        )


                        self._last_ingestion_at = (
                            now
                        )


                        self._ingestion_successes += 1

                        self._latest_ingestion_error = None

                        ingested = True


                    except Exception as exc:

                        ingestion_error = str(
                            exc
                        )


                        self._latest_ingestion_error = (
                            ingestion_error
                        )


                        self._ingestion_failures += 1


            return CANReceiveResult(

                received=True,

                frame=frame,

                decode_result=result,

                readiness=readiness,

                ingested=ingested,

                ingestion_error=(
                    ingestion_error
                ),
            )


        except Exception as exc:

            self._latest_error = str(
                exc
            )


            self._decode_failures += 1


            return CANReceiveResult(

                received=True,

                frame=frame,

                decode_result=None,

                readiness=None,

                ingested=False,

                ingestion_error=str(
                    exc
                ),
            )


    async def poll_once(
        self,
    ) -> CANReceiveResult:

        if not self._running:

            raise (
                CANTransportNotConnectedError(
                    "CAN service is not running."
                )
            )


        frame = await (
            self.transport.receive()
        )


        if frame is None:

            return CANReceiveResult(

                received=False,

                frame=None,

                decode_result=None,

                readiness=None,
            )


        return await self.process_frame(
            frame
        )


    async def run(
        self,
    ) -> None:

        if not self._running:

            await self.start()


        while self._running:

            try:

                await self.poll_once()


            except asyncio.CancelledError:

                raise


            except Exception as exc:

                self._latest_error = str(
                    exc
                )


            await asyncio.sleep(
                self.transport
                .config
                .receive_poll_seconds
            )


    def status(
        self,
    ) -> Dict[str, Any]:

        return {

            "service":
                "can_transport",

            "version":
                CAN_TRANSPORT_VERSION,

            "running":
                self._running,

            "transport_state":
                self.transport
                .state
                .value,

            "transport_type":
                self.transport
                .config
                .transport_type
                .value,

            "interface":
                self.transport
                .config
                .interface,

            "channel":
                self.transport
                .config
                .channel,

            "bitrate":
                self.transport
                .config
                .bitrate,

            "python_can_available":
                PYTHON_CAN_AVAILABLE,

            "auto_aggregate":
                self.transport
                .config
                .auto_aggregate,

            "auto_ingest":
                self.transport
                .config
                .auto_ingest,

            "required_signals":
                list(
                    self.transport
                    .config
                    .required_signals
                ),

            "minimum_ingestion_interval_seconds":
                (
                    self.transport
                    .config
                    .minimum_ingestion_interval_seconds
                ),

            "frames_received":
                self._frames_received,

            "frames_decoded":
                self._frames_decoded,

            "frames_unknown":
                self._frames_unknown,

            "decode_failures":
                self._decode_failures,

            "readiness_checks":
                self._readiness_checks,

            "ready_snapshots":
                self._ready_snapshots,

            "not_ready_snapshots":
                self._not_ready_snapshots,

            "ingestion_attempts":
                self._ingestion_attempts,

            "ingestion_successes":
                self._ingestion_successes,

            "ingestion_failures":
                self._ingestion_failures,

            "ingestion_rate_limited":
                self._ingestion_rate_limited,

            "latest_readiness":
                (
                    self._latest_readiness
                    .to_dict()

                    if self._latest_readiness
                    is not None

                    else None
                ),

            "latest_frame":
                (
                    {
                        "arbitration_id":
                            self._latest_frame
                            .arbitration_id,

                        "arbitration_id_hex":
                            hex(
                                self._latest_frame
                                .arbitration_id
                            ),

                        "data_hex":
                            self._latest_frame
                            .data
                            .hex(),

                        "timestamp":
                            self._latest_frame
                            .timestamp
                            .isoformat(),
                    }

                    if self._latest_frame
                    is not None

                    else None
                ),

            "latest_decode_result":
                (
                    self._latest_decode_result
                    .to_dict()

                    if self._latest_decode_result
                    is not None

                    else None
                ),

            "latest_error":
                self._latest_error,

            "latest_ingestion_error":
                self._latest_ingestion_error,

            "started_at":
                (
                    self._started_at.isoformat()

                    if self._started_at
                    is not None

                    else None
                ),

            "last_ingestion_at":
                (
                    self._last_ingestion_at
                    .isoformat()

                    if self._last_ingestion_at
                    is not None

                    else None
                ),

            "aggregator":
                get_aggregator_status(),

            "timestamp":
                datetime.now(
                    timezone.utc
                ).isoformat(),
        }


_default_config = CANTransportConfig(

    transport_type=(
        CANTransportType.VIRTUAL
    ),

    interface="virtual",

    channel="pratirup-demo",

    bitrate=500000,

    auto_aggregate=True,

    auto_ingest=False,

    required_signals=(
        DEFAULT_REQUIRED_CAN_SIGNALS
    ),

    minimum_ingestion_interval_seconds=0.05,
)


_default_transport = (
    VirtualCANTransport(
        _default_config
    )
)


_default_service = (
    CANTransportService(
        _default_transport
    )
)


def get_default_can_service(
) -> CANTransportService:

    return _default_service


def get_default_virtual_transport(
) -> VirtualCANTransport:

    return _default_transport


async def start_can_transport(
) -> None:

    await _default_service.start()


async def stop_can_transport(
) -> None:

    await _default_service.stop()


async def poll_can_once(
) -> CANReceiveResult:

    return await (
        _default_service.poll_once()
    )


def inject_virtual_can_frame(
    arbitration_id: int,
    data: bytes,
    *,
    is_extended_id: bool = False,
) -> RawCANFrame:

    return (
        _default_transport.inject_raw(

            arbitration_id=(
                arbitration_id
            ),

            data=data,

            is_extended_id=(
                is_extended_id
            ),
        )
    )


def get_can_readiness(
) -> Dict[str, Any]:

    return (
        _default_service
        .evaluate_readiness()
        .to_dict()
    )


def get_can_transport_status(
) -> Dict[str, Any]:

    return (
        _default_service.status()
    )


def get_can_transport_info(
) -> Dict[str, Any]:

    return {

        "name":
            "PRATIRUP Cross-Platform CAN Transport",

        "version":
            CAN_TRANSPORT_VERSION,

        "default_transport":
            "virtual",

        "python_can_available":
            PYTHON_CAN_AVAILABLE,

        "windows_safe":
            True,

        "linux_socketcan_optional":
            True,

        "hardware_required":
            False,

        "freshness_aware":
            True,

        "readiness_gate":
            True,

        "default_required_signals":
            list(
                DEFAULT_REQUIRED_CAN_SIGNALS
            ),

        "decoder":
            "backend.ingestion.fadec_decoder",

        "canonical_adapter":
            "backend.ingestion.can_adapter",

        "real_vrde_can_configuration":
            False,

        "supported_architecture": [

            "virtual",

            "python-can",

            "SocketCAN through python-can",

            "vendor CAN interfaces through python-can",
        ],

        "engineering_disclaimer":
            (
                "Transport configuration and readiness "
                "thresholds are PRATIRUP demonstrator "
                "settings, not official DRDO/VRDE FADEC "
                "interface requirements."
            ),
    }
