"use strict";

const PHYSICS_INTERFACE_VERSION =
  "1.1.0";

const physicsInterfaceState = {

  initialized:
    false,

  enabled:
    true,

  modelRegistered:
    false,

  modelName:
    null,

  modelVersion:
    null,

  model:
    null,

  lastInput:
    null,

  lastOutput:
    null,

  lastRunTimestamp:
    null,

  lastProcessedTimestamp:
    null,

  lastProcessedSequence:
    null,

  successfulRuns:
    0,

  failedRuns:
    0,

  skippedRuns:
    0

};

let physicsExecutionLocked =
  false;

function cloneValue(
  value
) {

  if (
    value === null ||
    value === undefined
  ) {

    return value;

  }

  if (
    typeof structuredClone ===
    "function"
  ) {

    return structuredClone(
      value
    );

  }

  return JSON.parse(
    JSON.stringify(
      value
    )
  );

}

function createPhysicsInput(
  observedState
) {

  if (
    !observedState
  ) {

    return null;

  }

  return {

    timestamp:
      Date.now(),

    engine: {

      rpm:
        observedState.engine
          ?.rpm ??
        null,

      throttlePercent:
        observedState.engine
          ?.throttlePercent ??
        null,

      loadPercent:
        observedState.engine
          ?.loadPercent ??
        null,

      operatingMode:
        observedState.engine
          ?.operatingMode ??
        null

    },

    environment: {

      altitudeM:
        observedState.environment
          ?.altitudeM ??
        null,

      ambientTemperatureC:
        observedState.environment
          ?.ambientTemperatureC ??
        null,

      ambientPressurePa:
        observedState.environment
          ?.ambientPressurePa ??
        null,

      airDensityKgM3:
        observedState.environment
          ?.airDensityKgM3 ??
        null

    },

    measured: {

      cht: {

        cylinder1C:
          observedState.cht
            ?.cylinder1C ??
          null,

        cylinder2C:
          observedState.cht
            ?.cylinder2C ??
          null,

        cylinder3C:
          observedState.cht
            ?.cylinder3C ??
          null,

        cylinder4C:
          observedState.cht
            ?.cylinder4C ??
          null

      },

      egt: {

        cylinder1C:
          observedState.egt
            ?.cylinder1C ??
          null,

        cylinder2C:
          observedState.egt
            ?.cylinder2C ??
          null,

        cylinder3C:
          observedState.egt
            ?.cylinder3C ??
          null,

        cylinder4C:
          observedState.egt
            ?.cylinder4C ??
          null

      },

      oil: {

        pressureKPa:
          observedState.oil
            ?.pressureKPa ??
          null,

        temperatureC:
          observedState.oil
            ?.temperatureC ??
          null

      },

      fuel: {

        flowKgPerSecond:
          observedState.fuel
            ?.flowKgPerSecond ??
          null,

        pressureKPa:
          observedState.fuel
            ?.pressureKPa ??
          null

      },

      vibration: {

        overallG:
          observedState.vibration
            ?.overallG ??
          null,

        xG:
          observedState.vibration
            ?.xG ??
          null,

        yG:
          observedState.vibration
            ?.yG ??
          null,

        zG:
          observedState.vibration
            ?.zG ??
          null

      },

      electrical: {

        batteryVoltageV:
          observedState.electrical
            ?.batteryVoltageV ??
          null,

        batteryCurrentA:
          observedState.electrical
            ?.batteryCurrentA ??
          null,

        alternatorVoltageV:
          observedState.electrical
            ?.alternatorVoltageV ??
          null,

        alternatorCurrentA:
          observedState.electrical
            ?.alternatorCurrentA ??
          null

      },

      injection: {

        timingDeg:
          observedState.injection
            ?.timingDeg ??
          null,

        injector1PulseMs:
          observedState.injection
            ?.injector1PulseMs ??
          null,

        injector2PulseMs:
          observedState.injection
            ?.injector2PulseMs ??
          null,

        injector3PulseMs:
          observedState.injection
            ?.injector3PulseMs ??
          null,

        injector4PulseMs:
          observedState.injection
            ?.injector4PulseMs ??
          null

      }

    },

    mission: {

      missionId:
        observedState.mission
          ?.missionId ??
        null,

      phase:
        observedState.mission
          ?.phase ??
        null,

      elapsedTimeSec:
        observedState.mission
          ?.elapsedTimeSec ??
        null

    }

  };

}

function createPhysicsOutput() {

  return {

    timestamp:
      Date.now(),

    model: {

      name:
        physicsInterfaceState
          .modelName,

      version:
        physicsInterfaceState
          .modelVersion

    },

    engine: {

      expectedRpm:
        null,

      expectedTorqueNm:
        null,

      expectedPowerKw:
        null,

      expectedLoadPercent:
        null,

      expectedManifoldPressurePa:
        null,

      expectedAirFlowKgPerSecond:
        null

    },

    cht: {

      cylinder1C:
        null,

      cylinder2C:
        null,

      cylinder3C:
        null,

      cylinder4C:
        null

    },

    egt: {

      cylinder1C:
        null,

      cylinder2C:
        null,

      cylinder3C:
        null,

      cylinder4C:
        null

    },

    oil: {

      pressureKPa:
        null,

      temperatureC:
        null

    },

    fuel: {

      flowKgPerSecond:
        null,

      pressureKPa:
        null,

      airFuelRatio:
        null

    },

    combustion: {

      meanEffectivePressurePa:
        null,

      peakCylinderPressurePa:
        null,

      combustionEfficiency:
        null

    },

    electrical: {

      alternatorVoltageV:
        null,

      alternatorCurrentA:
        null

    },

    environment: {

      altitudeM:
        null,

      ambientTemperatureC:
        null,

      ambientPressurePa:
        null,

      airDensityKgM3:
        null,

      densityRatio:
        null,

      intakeTemperatureC:
        null,

      volumetricEfficiency:
        null

    },

    confidence: {

      overall:
        null,

      engine:
        null,

      thermal:
        null,

      lubrication:
        null,

      fuel:
        null

    }

  };

}

function registerPhysicsModel(
  configuration
) {

  if (
    !configuration ||
    typeof configuration !==
    "object"
  ) {

    console.error(
      "[PRATIRUP PHYSICS] Invalid model configuration."
    );

    return false;

  }

  const {

    name,

    version,

    model

  } =
    configuration;

  if (
    typeof model !==
    "function"
  ) {

    console.error(
      "[PRATIRUP PHYSICS] Physics model must be a function."
    );

    return false;

  }

  physicsInterfaceState.model =
    model;

  physicsInterfaceState.modelName =

    name ||

    "Unnamed Physics Model";

  physicsInterfaceState.modelVersion =

    version ||

    "0.0.0";

  physicsInterfaceState.modelRegistered =
    true;

  window.dispatchEvent(

    new CustomEvent(
      "pratirup:physics-model-registered",
      {

        detail: {

          name:
            physicsInterfaceState
              .modelName,

          version:
            physicsInterfaceState
              .modelVersion

        }

      }
    )

  );

  console.log(
    "[PRATIRUP] Physics model registered:",
    physicsInterfaceState.modelName,
    physicsInterfaceState.modelVersion
  );

  return true;

}

function unregisterPhysicsModel() {

  physicsInterfaceState.model =
    null;

  physicsInterfaceState.modelName =
    null;

  physicsInterfaceState.modelVersion =
    null;

  physicsInterfaceState.modelRegistered =
    false;

  physicsInterfaceState.lastInput =
    null;

  physicsInterfaceState.lastOutput =
    null;

  physicsInterfaceState.lastProcessedTimestamp =
    null;

  physicsInterfaceState.lastProcessedSequence =
    null;

  window
    .PRATIRUP_TWIN
    ?.clearExpectedState?.();

  window.dispatchEvent(

    new CustomEvent(
      "pratirup:physics-model-unregistered"
    )

  );

}

function validatePhysicsOutput(
  output
) {

  if (
    !output ||
    typeof output !==
    "object"
  ) {

    return {

      valid:
        false,

      errors: [

        "Physics output must be an object."

      ]

    };

  }

  const errors =
    [];

  if (
    !output.engine
  ) {

    errors.push(
      "Missing engine output."
    );

  }

  if (
    !output.cht
  ) {

    errors.push(
      "Missing CHT output."
    );

  }

  if (
    !output.egt
  ) {

    errors.push(
      "Missing EGT output."
    );

  }

  if (
    !output.oil
  ) {

    errors.push(
      "Missing oil output."
    );

  }

  if (
    !output.fuel
  ) {

    errors.push(
      "Missing fuel output."
    );

  }

  if (
    !output.confidence
  ) {

    errors.push(
      "Missing model confidence output."
    );

  }

  return {

    valid:
      errors.length ===
      0,

    errors

  };

}

function runPhysicsModel(
  observedState
) {

  if (
    !physicsInterfaceState.enabled
  ) {

    physicsInterfaceState.skippedRuns++;

    return null;

  }

  if (
    !physicsInterfaceState
      .modelRegistered ||
    typeof physicsInterfaceState
      .model !==
    "function"
  ) {

    physicsInterfaceState.skippedRuns++;

    return null;

  }

  if (
    physicsExecutionLocked
  ) {

    physicsInterfaceState.skippedRuns++;

    return null;

  }

  const input =
    createPhysicsInput(
      observedState
    );

  if (!input) {

    physicsInterfaceState.skippedRuns++;

    return null;

  }

  physicsExecutionLocked =
    true;

  physicsInterfaceState.lastInput =
    cloneValue(
      input
    );

  try {

    const output =

      physicsInterfaceState.model(

        input,

        createPhysicsOutput

      );

    const validation =
      validatePhysicsOutput(
        output
      );

    if (
      !validation.valid
    ) {

      physicsInterfaceState.failedRuns++;

      console.warn(
        "[PRATIRUP PHYSICS] Invalid physics output:",
        validation.errors
      );

      return null;

    }

    physicsInterfaceState.lastOutput =
      cloneValue(
        output
      );

    physicsInterfaceState.lastRunTimestamp =
      Date.now();

    physicsInterfaceState.successfulRuns++;

    window
      .PRATIRUP_TWIN
      ?.setExpectedState?.(
        output
      );

    window.dispatchEvent(

      new CustomEvent(
        "pratirup:physics-output",
        {

          detail:
            cloneValue(
              output
            )

        }
      )

    );

    return output;

  }

  catch (
    error
  ) {

    physicsInterfaceState.failedRuns++;

    console.error(
      "[PRATIRUP PHYSICS] Model execution failed:",
      error
    );

    window.dispatchEvent(

      new CustomEvent(
        "pratirup:physics-error",
        {

          detail: {

            message:

              error?.message ||

              String(error)

          }

        }
      )

    );

    return null;

  }

  finally {

    physicsExecutionLocked =
      false;

  }

}

function handleObservedState(
  event
) {

  if (
    !physicsInterfaceState.enabled ||
    !physicsInterfaceState.modelRegistered
  ) {

    return;

  }

  const detail =
    event.detail;

  if (!detail) {

    return;

  }

  const observed =
    detail.observedState;

  if (!observed) {

    return;

  }

  const sequence =
    detail.sequence;

  const timestamp =
    detail.timestamp;

  if (
    sequence !== null &&
    sequence !== undefined &&
    sequence ===
      physicsInterfaceState
        .lastProcessedSequence
  ) {

    physicsInterfaceState.skippedRuns++;

    return;

  }

  if (
    (
      sequence === null ||
      sequence === undefined
    ) &&
    timestamp !== null &&
    timestamp !== undefined &&
    timestamp ===
      physicsInterfaceState
        .lastProcessedTimestamp
  ) {

    physicsInterfaceState.skippedRuns++;

    return;

  }

  physicsInterfaceState
    .lastProcessedSequence =
    sequence ?? null;

  physicsInterfaceState
    .lastProcessedTimestamp =
    timestamp ?? Date.now();

  runPhysicsModel(
    observed
  );

}

window.addEventListener(
  "pratirup:observed-state",
  handleObservedState
);

function setPhysicsEnabled(
  enabled
) {

  physicsInterfaceState.enabled =
    Boolean(
      enabled
    );

  if (
    !physicsInterfaceState.enabled
  ) {

    window
      .PRATIRUP_TWIN
      ?.clearExpectedState?.();

  }

  window.dispatchEvent(

    new CustomEvent(
      "pratirup:physics-enabled-change",
      {

        detail: {

          enabled:
            physicsInterfaceState.enabled

        }

      }
    )

  );

}

function getPhysicsStatus() {

  return {

    version:
      PHYSICS_INTERFACE_VERSION,

    initialized:
      physicsInterfaceState
        .initialized,

    enabled:
      physicsInterfaceState
        .enabled,

    modelRegistered:
      physicsInterfaceState
        .modelRegistered,

    modelName:
      physicsInterfaceState
        .modelName,

    modelVersion:
      physicsInterfaceState
        .modelVersion,

    executionLocked:
      physicsExecutionLocked,

    successfulRuns:
      physicsInterfaceState
        .successfulRuns,

    failedRuns:
      physicsInterfaceState
        .failedRuns,

    skippedRuns:
      physicsInterfaceState
        .skippedRuns,

    lastRunTimestamp:
      physicsInterfaceState
        .lastRunTimestamp,

    lastProcessedSequence:
      physicsInterfaceState
        .lastProcessedSequence,

    lastProcessedTimestamp:
      physicsInterfaceState
        .lastProcessedTimestamp

  };

}

function getLastInput() {

  return physicsInterfaceState
    .lastInput

      ? cloneValue(
          physicsInterfaceState
            .lastInput
        )

      : null;

}

function getLastOutput() {

  return physicsInterfaceState
    .lastOutput

      ? cloneValue(
          physicsInterfaceState
            .lastOutput
        )

      : null;

}

function resetPhysicsInterface() {

  physicsInterfaceState.lastInput =
    null;

  physicsInterfaceState.lastOutput =
    null;

  physicsInterfaceState.lastRunTimestamp =
    null;

  physicsInterfaceState.lastProcessedSequence =
    null;

  physicsInterfaceState.lastProcessedTimestamp =
    null;

  physicsInterfaceState.successfulRuns =
    0;

  physicsInterfaceState.failedRuns =
    0;

  physicsInterfaceState.skippedRuns =
    0;

  physicsExecutionLocked =
    false;

  window
    .PRATIRUP_TWIN
    ?.clearExpectedState?.();

}

window.PRATIRUP_PHYSICS = {

  version:
    PHYSICS_INTERFACE_VERSION,

  register:
    registerPhysicsModel,

  unregister:
    unregisterPhysicsModel,

  run:
    runPhysicsModel,

  enable() {

    setPhysicsEnabled(
      true
    );

  },

  disable() {

    setPhysicsEnabled(
      false
    );

  },

  setEnabled:
    setPhysicsEnabled,

  getStatus:
    getPhysicsStatus,

  getLastInput,

  getLastOutput,

  createInput:
    createPhysicsInput,

  createOutput:
    createPhysicsOutput,

  reset:
    resetPhysicsInterface

};

physicsInterfaceState.initialized =
  true;

window.dispatchEvent(

  new CustomEvent(
    "pratirup:physics-interface-ready",
    {

      detail: {

        version:
          PHYSICS_INTERFACE_VERSION

      }

    }
  )

);

console.log(
  `[PRATIRUP] Physics Model Interface ${PHYSICS_INTERFACE_VERSION} ready.`
);

console.log(
  "[PRATIRUP] Physics trigger: pratirup:observed-state"
);
