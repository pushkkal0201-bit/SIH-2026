from __future__ import annotations

import asyncio

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from inspect import iscoroutinefunction
from math import isfinite
from time import perf_counter
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Union,
)

from backend.core.digital_twin import (
    get_observed_state,
    set_expected_state,
)

from backend.core.residual_engine import (
    calculate_from_digital_twin,
)

from backend.physics.atmosphere import (
    atmosphere_model,
)

from backend.physics.thermodynamics import (
    thermodynamics_model,
)

from backend.physics.combustion import (
    combustion_model,
)

from backend.physics.cooling import (
    cooling_model,
)

from backend.physics.lubrication import (
    lubrication_model,
)

from backend.physics.performance_maps import (
    performance_model,
)

MODEL_ORCHESTRATOR_VERSION = "1.1.0"

DEFAULT_MODEL_TIMEOUT_SECONDS = 2.0

AUTO_REGISTER_DEFAULT_MODELS = True

PhysicsModelReturn = Optional[
    Dict[str, Any]
]

PhysicsModelCallable = Callable[
    [Dict[str, Any]],
    Union[
        PhysicsModelReturn,
        Awaitable[PhysicsModelReturn],
    ],
]

@dataclass
class RegisteredModel:

    name: str

    callable: PhysicsModelCallable

    enabled: bool = True

    priority: int = 100

    version: Optional[str] = None

    description: Optional[str] = None

    timeout_seconds: float = (
        DEFAULT_MODEL_TIMEOUT_SECONDS
    )

    execution_count: int = 0

    failure_count: int = 0

    timeout_count: int = 0

    last_error: Optional[str] = None

    last_execution_timestamp: Optional[
        datetime
    ] = None

    last_execution_ms: Optional[
        float
    ] = None

@dataclass
class OrchestrationResult:

    timestamp: datetime

    expected_state: Optional[
        Dict[str, Any]
    ]

    expected_state_available: bool

    expected_value_count: int

    executed_models: List[str]

    failed_models: List[str]

    skipped_models: List[str]

    model_outputs: Dict[
        str,
        Optional[Dict[str, Any]],
    ]

    model_execution_ms: Dict[
        str,
        Optional[float],
    ]

    residual_calculated: bool

    residual_result: Optional[
        Dict[str, Any]
    ]

    warnings: List[str] = field(
        default_factory=list
    )

    total_execution_ms: Optional[
        float
    ] = None

    version: str = (
        MODEL_ORCHESTRATOR_VERSION
    )

    def to_dict(
        self,
    ) -> Dict[str, Any]:

        return {

            "timestamp":
                self.timestamp.isoformat(),

            "version":
                self.version,

            "expected_state":
                deepcopy(
                    self.expected_state
                ),

            "expected_state_available":
                self.expected_state_available,

            "expected_value_count":
                self.expected_value_count,

            "executed_models":
                list(
                    self.executed_models
                ),

            "failed_models":
                list(
                    self.failed_models
                ),

            "skipped_models":
                list(
                    self.skipped_models
                ),

            "model_outputs":
                deepcopy(
                    self.model_outputs
                ),

            "model_execution_ms":
                deepcopy(
                    self.model_execution_ms
                ),

            "residual_calculated":
                self.residual_calculated,

            "residual_result":
                deepcopy(
                    self.residual_result
                ),

            "warnings":
                list(
                    self.warnings
                ),

            "total_execution_ms":
                self.total_execution_ms,
        }

_registered_models: Dict[
    str,
    RegisteredModel
] = {}

_latest_result: Optional[
    OrchestrationResult
] = None

_execution_count = 0

_failed_execution_count = 0

_successful_execution_count = 0

def utc_now() -> datetime:

    return datetime.now(
        timezone.utc
    )

def is_number(
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
        float(
            value
        )
    )

def merge_dicts(
    base: Dict[str, Any],
    incoming: Dict[str, Any],
) -> Dict[str, Any]:

    for key, value in incoming.items():

        if (
            key in base
            and isinstance(
                base[key],
                dict,
            )
            and isinstance(
                value,
                dict,
            )
        ):

            merge_dicts(
                base[key],
                value,
            )

        else:

            base[key] = deepcopy(
                value
            )

    return base

def create_expected_state_template() -> Dict[
    str,
    Any,
]:

    return {

        "engine": {

            "rpm":
                None,

            "throttle_percent":
                None,

            "load_percent":
                None,

            "power_kw":
                None,

            "torque_nm":
                None,

        },

        "cht": {

            "cylinder1_c":
                None,

            "cylinder2_c":
                None,

            "cylinder3_c":
                None,

            "cylinder4_c":
                None,

        },

        "egt": {

            "cylinder1_c":
                None,

            "cylinder2_c":
                None,

            "cylinder3_c":
                None,

            "cylinder4_c":
                None,

        },

        "oil": {

            "pressure_kpa":
                None,

            "temperature_c":
                None,

        },

        "fuel": {

            "flow_kg_per_second":
                None,

            "pressure_kpa":
                None,

            "injection_timing_deg":
                None,

        },

        "vibration": {

            "overall_g":
                None,

            "x_g":
                None,

            "y_g":
                None,

            "z_g":
                None,

        },

        "electrical": {

            "battery_voltage_v":
                None,

            "battery_current_a":
                None,

            "alternator_voltage_v":
                None,

            "alternator_current_a":
                None,

        },

        "environment": {

            "altitude_m":
                None,

            "altitude_ft":
                None,

            "ambient_temperature_c":
                None,

            "ambient_pressure_kpa":
                None,

            "air_density_kg_m3":
                None,

        },

        "_physics": {},
    }

def count_available_values(
    value: Any,
    *,
    path: str = "",
) -> int:

    if isinstance(
        value,
        dict,
    ):

        total = 0

        for key, child in value.items():

            child_path = (
                f"{path}.{key}"
                if path
                else key
            )

            if child_path.startswith(
                "_physics"
            ):

                continue

            total += (
                count_available_values(
                    child,
                    path=child_path,
                )
            )

        return total

    if is_number(
        value
    ):

        return 1

    return 0

def register_model(
    name: str,
    model: PhysicsModelCallable,
    *,
    priority: int = 100,
    enabled: bool = True,
    version: Optional[str] = None,
    description: Optional[str] = None,
    timeout_seconds: float = (
        DEFAULT_MODEL_TIMEOUT_SECONDS
    ),
) -> RegisteredModel:

    if (
        not isinstance(
            name,
            str,
        )
        or not name.strip()
    ):

        raise ValueError(
            "Physics model name must be a non-empty string."
        )

    if not callable(
        model
    ):

        raise TypeError(
            "Physics model must be callable."
        )

    if timeout_seconds <= 0:

        raise ValueError(
            "Model timeout must be greater than zero."
        )

    normalized_name = (
        name.strip()
    )

    registration = RegisteredModel(

        name=
            normalized_name,

        callable=
            model,

        enabled=
            bool(
                enabled
            ),

        priority=
            int(
                priority
            ),

        version=
            version,

        description=
            description,

        timeout_seconds=
            float(
                timeout_seconds
            ),
    )

    _registered_models[
        normalized_name
    ] = registration

    return registration

def register_default_models() -> None:

    register_model(

        name=
            "atmosphere",

        model=
            atmosphere_model,

        priority=
            10,

        version=
            "1.0.0",

        description=
            "ISA atmosphere and air-density model.",
    )

    register_model(

        name=
            "thermodynamics",

        model=
            thermodynamics_model,

        priority=
            20,

        version=
            "1.0.0",

        description=
            (
                "Intake, manifold, airflow and "
                "thermodynamic state model."
            ),
    )

    register_model(

        name=
            "combustion",

        model=
            combustion_model,

        priority=
            30,

        version=
            "1.0.0",

        description=
            (
                "Combustion efficiency, EGT, fuel "
                "and pressure model."
            ),
    )

    register_model(

        name=
            "cooling",

        model=
            cooling_model,

        priority=
            40,

        version=
            "1.0.0",

        description=
            "Cylinder-head thermal and cooling model.",
    )

    register_model(

        name=
            "lubrication",

        model=
            lubrication_model,

        priority=
            50,

        version=
            "1.0.0",

        description=
            "Oil pressure and oil temperature model.",
    )

    register_model(

        name=
            "performance",

        model=
            performance_model,

        priority=
            60,

        version=
            "1.0.0",

        description=
            (
                "180 HP baseline power, torque and "
                "altitude-performance model."
            ),
    )

def unregister_model(
    name: str,
) -> bool:

    if name not in _registered_models:

        return False

    del _registered_models[
        name
    ]

    return True

def set_model_enabled(
    name: str,
    enabled: bool,
) -> bool:

    model = _registered_models.get(
        name
    )

    if model is None:

        return False

    model.enabled = bool(
        enabled
    )

    return True

def get_registered_models() -> List[
    Dict[str, Any]
]:

    models = sorted(
        _registered_models.values(),
        key=lambda item: (
            item.priority,
            item.name,
        ),
    )

    return [

        {

            "name":
                model.name,

            "enabled":
                model.enabled,

            "priority":
                model.priority,

            "version":
                model.version,

            "description":
                model.description,

            "timeout_seconds":
                model.timeout_seconds,

            "execution_count":
                model.execution_count,

            "failure_count":
                model.failure_count,

            "timeout_count":
                model.timeout_count,

            "last_error":
                model.last_error,

            "last_execution_ms":
                model.last_execution_ms,

            "last_execution_timestamp":
                (
                    model
                    .last_execution_timestamp
                    .isoformat()

                    if model
                    .last_execution_timestamp
                    is not None

                    else None
                ),
        }

        for model
        in models
    ]

async def run_sync_model(
    registration: RegisteredModel,
    observed_state: Dict[str, Any],
) -> PhysicsModelReturn:

    return await asyncio.to_thread(
        registration.callable,
        deepcopy(
            observed_state
        ),
    )

async def execute_model(
    registration: RegisteredModel,
    observed_state: Dict[str, Any],
) -> Optional[
    Dict[str, Any]
]:

    started = perf_counter()

    try:

        if iscoroutinefunction(
            registration.callable
        ):

            model_task = (
                registration.callable(
                    deepcopy(
                        observed_state
                    )
                )
            )

        else:

            model_task = run_sync_model(
                registration,
                observed_state,
            )

        result = await asyncio.wait_for(

            model_task,

            timeout=(
                registration
                .timeout_seconds
            ),
        )

        execution_ms = (
            perf_counter()
            -
            started
        ) * 1000.0

        registration.execution_count += 1

        registration.last_execution_timestamp = (
            utc_now()
        )

        registration.last_execution_ms = (
            execution_ms
        )

        registration.last_error = None

        if result is None:

            return None

        if not isinstance(
            result,
            dict,
        ):

            raise TypeError(
                (
                    f"Physics model '{registration.name}' "
                    "must return dict or None."
                )
            )

        return deepcopy(
            result
        )

    except asyncio.TimeoutError as exc:

        registration.failure_count += 1

        registration.timeout_count += 1

        registration.last_error = (
            "Model execution timed out."
        )

        raise TimeoutError(
            (
                f"Physics model '{registration.name}' "
                "execution timed out."
            )
        ) from exc

    except Exception as exc:

        registration.failure_count += 1

        registration.last_error = str(
            exc
        )

        raise

async def generate_expected_state(
    observed_state: Optional[
        Dict[str, Any]
    ] = None,
) -> OrchestrationResult:

    global _latest_result

    global _execution_count
    global _successful_execution_count
    global _failed_execution_count

    pipeline_started = (
        perf_counter()
    )

    _execution_count += 1

    executed_models: List[str] = []

    failed_models: List[str] = []

    skipped_models: List[str] = []

    warnings: List[str] = []

    model_outputs: Dict[
        str,
        Optional[Dict[str, Any]],
    ] = {}

    model_execution_ms: Dict[
        str,
        Optional[float],
    ] = {}

    if observed_state is None:

        observed_state = (
            get_observed_state()
        )

    if not isinstance(
        observed_state,
        dict,
    ):

        set_expected_state(
            None
        )

        warnings.append(
            "Observed engine state is unavailable."
        )

        result = OrchestrationResult(

            timestamp=
                utc_now(),

            expected_state=
                None,

            expected_state_available=
                False,

            expected_value_count=
                0,

            executed_models=
                [],

            failed_models=
                [],

            skipped_models=
                [],

            model_outputs=
                {},

            model_execution_ms=
                {},

            residual_calculated=
                False,

            residual_result=
                None,

            warnings=
                warnings,

            total_execution_ms=(
                (
                    perf_counter()
                    -
                    pipeline_started
                )
                *
                1000.0
            ),
        )

        _latest_result = result

        _failed_execution_count += 1

        return result

    expected_state = (
        create_expected_state_template()
    )

    models = sorted(
        _registered_models.values(),
        key=lambda model: (
            model.priority,
            model.name,
        ),
    )

    if not models:

        warnings.append(
            "No backend physics models are registered."
        )

    for registration in models:

        if not registration.enabled:

            skipped_models.append(
                registration.name
            )

            model_outputs[
                registration.name
            ] = None

            model_execution_ms[
                registration.name
            ] = None

            continue

        try:

            output = await execute_model(

                registration,

                observed_state,
            )

            model_outputs[
                registration.name
            ] = output

            model_execution_ms[
                registration.name
            ] = (
                registration
                .last_execution_ms
            )

            executed_models.append(
                registration.name
            )

            if output is not None:

                merge_dicts(
                    expected_state,
                    output,
                )

        except Exception as exc:

            failed_models.append(
                registration.name
            )

            model_outputs[
                registration.name
            ] = None

            model_execution_ms[
                registration.name
            ] = (
                registration
                .last_execution_ms
            )

            warnings.append(
                (
                    f"Physics model "
                    f"'{registration.name}' failed: "
                    f"{str(exc)}"
                )
            )

    expected_value_count = (
        count_available_values(
            expected_state
        )
    )

    expected_state_available = (
        expected_value_count > 0
    )

    if not expected_state_available:

        set_expected_state(
            None
        )

        warnings.append(
            (
                "Physics pipeline produced no valid "
                "expected engine-state values."
            )
        )

        total_execution_ms = (
            (
                perf_counter()
                -
                pipeline_started
            )
            *
            1000.0
        )

        result = OrchestrationResult(

            timestamp=
                utc_now(),

            expected_state=
                None,

            expected_state_available=
                False,

            expected_value_count=
                0,

            executed_models=
                executed_models,

            failed_models=
                failed_models,

            skipped_models=
                skipped_models,

            model_outputs=
                model_outputs,

            model_execution_ms=
                model_execution_ms,

            residual_calculated=
                False,

            residual_result=
                None,

            warnings=
                warnings,

            total_execution_ms=
                total_execution_ms,
        )

        _latest_result = result

        _failed_execution_count += 1

        return result

    set_expected_state(
        expected_state
    )

    residual = None

    try:

        residual = (
            calculate_from_digital_twin()
        )

    except Exception as exc:

        warnings.append(
            (
                "Residual calculation failed: "
                f"{str(exc)}"
            )
        )

    residual_result = (

        residual.to_dict()

        if residual is not None

        else None
    )

    residual_calculated = (
        residual is not None
    )

    if not residual_calculated:

        warnings.append(
            (
                "Expected state is available, but "
                "residual calculation is unavailable."
            )
        )

    total_execution_ms = (
        (
            perf_counter()
            -
            pipeline_started
        )
        *
        1000.0
    )

    result = OrchestrationResult(

        timestamp=
            utc_now(),

        expected_state=
            expected_state,

        expected_state_available=
            True,

        expected_value_count=
            expected_value_count,

        executed_models=
            executed_models,

        failed_models=
            failed_models,

        skipped_models=
            skipped_models,

        model_outputs=
            model_outputs,

        model_execution_ms=
            model_execution_ms,

        residual_calculated=
            residual_calculated,

        residual_result=
            residual_result,

        warnings=
            warnings,

        total_execution_ms=
            total_execution_ms,
    )

    _latest_result = result

    if failed_models:

        _failed_execution_count += 1

    else:

        _successful_execution_count += 1

    return result

async def run_model_pipeline() -> OrchestrationResult:

    return await generate_expected_state()

async def run_for_observed_state(
    observed_state: Dict[str, Any],
) -> OrchestrationResult:

    return await generate_expected_state(
        observed_state
    )

def get_latest_orchestration_result() -> Optional[
    OrchestrationResult
]:

    return _latest_result

def get_latest_orchestration_dict() -> Optional[
    Dict[str, Any]
]:

    if _latest_result is None:

        return None

    return _latest_result.to_dict()

def get_model_orchestrator_status() -> Dict[
    str,
    Any,
]:

    enabled_models = [

        model

        for model
        in _registered_models.values()

        if model.enabled

    ]

    return {

        "service":
            "model_orchestrator",

        "status":
            "READY",

        "version":
            MODEL_ORCHESTRATOR_VERSION,

        "registered_models":
            len(
                _registered_models
            ),

        "enabled_models":
            len(
                enabled_models
            ),

        "execution_count":
            _execution_count,

        "successful_execution_count":
            _successful_execution_count,

        "failed_execution_count":
            _failed_execution_count,

        "latest_result_available":
            _latest_result is not None,

        "latest_expected_state_available":
            (
                _latest_result
                .expected_state_available

                if _latest_result
                is not None

                else False
            ),

        "latest_expected_value_count":
            (
                _latest_result
                .expected_value_count

                if _latest_result
                is not None

                else 0
            ),

        "latest_residual_calculated":
            (
                _latest_result
                .residual_calculated

                if _latest_result
                is not None

                else False
            ),

        "latest_total_execution_ms":
            (
                _latest_result
                .total_execution_ms

                if _latest_result
                is not None

                else None
            ),

        "models":
            get_registered_models(),

        "timestamp":
            utc_now().isoformat(),
    }

def reset_model_orchestrator(
    clear_models: bool = False,
) -> None:

    global _latest_result

    global _execution_count
    global _successful_execution_count
    global _failed_execution_count

    _latest_result = None

    _execution_count = 0

    _successful_execution_count = 0

    _failed_execution_count = 0

    for model in _registered_models.values():

        model.execution_count = 0

        model.failure_count = 0

        model.timeout_count = 0

        model.last_error = None

        model.last_execution_timestamp = None

        model.last_execution_ms = None

    if clear_models:

        _registered_models.clear()

def reload_default_models() -> None:

    _registered_models.clear()

    register_default_models()

def get_model_orchestrator_info() -> Dict[
    str,
    Any,
]:

    return {

        "name":
            "PRATIRUP Model Orchestrator",

        "version":
            MODEL_ORCHESTRATOR_VERSION,

        "purpose":
            (
                "Coordinate the backend physics stack, "
                "generate expected engine state, update "
                "the Digital Twin, and trigger residual "
                "calculation."
            ),

        "physics_pipeline": [

            "atmosphere",

            "thermodynamics",

            "combustion",

            "cooling",

            "lubrication",

            "performance",
        ],

        "pipeline": [

            "observed_state",

            "physics_models",

            "expected_state",

            "digital_twin",

            "residual_engine",
        ],

        "registered_model_count":
            len(
                _registered_models
            ),

        "null_policy":
            (
                "Missing physics outputs remain None. "
                "No unavailable value is replaced with zero."
            ),

        "important":
            (
                "Physics models are baseline engineering "
                "models and require calibration using "
                "verified engine/test data."
            ),
    }

if AUTO_REGISTER_DEFAULT_MODELS:

    register_default_models()
