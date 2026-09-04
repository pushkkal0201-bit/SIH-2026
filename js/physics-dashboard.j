"use strict";

const PHYSICS_DASHBOARD_VERSION =
  "1.0.0";

function $(
  id
) {
  return document.getElementById(
    id
  );
}

function formatNumber(
  value,
  digits = 1
) {
  const number =
    Number(
      value
    );

  if (
    !Number.isFinite(
      number
    )
  ) {
    return "--";
  }

  return number.toFixed(
    digits
  );
}

function formatInteger(
  value
) {
  const number =
    Number(
      value
    );

  if (
    !Number.isFinite(
      number
    )
  ) {
    return "--";
  }

  return Math.round(
    number
  ).toString();
}

function setText(
  id,
  value
) {
  const element =
    $(
      id
    );

  if (
    !element
  ) {
    return;
  }

  element.textContent =
    value;
}

function averageValues(
  values
) {
  const valid =
    values.filter(
      value =>
        Number.isFinite(
          Number(
            value
          )
        )
    );

  if (
    valid.length === 0
  ) {
    return null;
  }

  const total =
    valid.reduce(
      (
        sum,
        value
      ) =>
        sum +
        Number(
          value
        ),
      0
    );

  return total /
    valid.length;
}

function handlePhysicsOutput(
  event
) {
  const output =
    event.detail;

  if (
    !output
  ) {
    return;
  }

  setText(
    "telemetryRpm",
    formatInteger(
      output.engine
        ?.expectedRpm
    )
  );

  setText(
    "telemetryPower",
    formatNumber(
      output.engine
        ?.expectedPowerKw,
      1
    )
  );

  setText(
    "telemetryTorque",
    formatNumber(
      output.engine
        ?.expectedTorqueNm,
      1
    )
  );

  const chtValues = [
    output.cht
      ?.cylinder1C,

    output.cht
      ?.cylinder2C,

    output.cht
      ?.cylinder3C,

    output.cht
      ?.cylinder4C
  ];

  setText(
    "telemetryCht1",
    formatNumber(
      chtValues[0],
      1
    )
  );

  setText(
    "telemetryCht2",
    formatNumber(
      chtValues[1],
      1
    )
  );

  setText(
    "telemetryCht3",
    formatNumber(
      chtValues[2],
      1
    )
  );

  setText(
    "telemetryCht4",
    formatNumber(
      chtValues[3],
      1
    )
  );

  setText(
    "telemetryChtAverage",
    formatNumber(
      averageValues(
        chtValues
      ),
      1
    )
  );

  const egtValues = [
    output.egt
      ?.cylinder1C,

    output.egt
      ?.cylinder2C,

    output.egt
      ?.cylinder3C,

    output.egt
      ?.cylinder4C
  ];

  setText(
    "telemetryEgt1",
    formatNumber(
      egtValues[0],
      1
    )
  );

  setText(
    "telemetryEgt2",
    formatNumber(
      egtValues[1],
      1
    )
  );

  setText(
    "telemetryEgt3",
    formatNumber(
      egtValues[2],
      1
    )
  );

  setText(
    "telemetryEgt4",
    formatNumber(
      egtValues[3],
      1
    )
  );

  setText(
    "telemetryEgtAverage",
    formatNumber(
      averageValues(
        egtValues
      ),
      1
    )
  );

  const oilPressure =
    output.oil
      ?.pressureKPa;

  const oilTemperature =
    output.oil
      ?.temperatureC;

  setText(
    "telemetryOilPressure",
    formatNumber(
      oilPressure,
      0
    )
  );

  setText(
    "telemetryOilPressureDetail",
    formatNumber(
      oilPressure,
      0
    )
  );

  setText(
    "telemetryOilTemperature",
    formatNumber(
      oilTemperature,
      1
    )
  );

  setText(
    "telemetryFuelFlow",
    formatNumber(
      output.fuel
        ?.flowKgPerSecond,
      4
    )
  );

  setText(
    "telemetryAltitude",
    formatInteger(
      output.environment
        ?.altitudeM
    )
  );

  setText(
    "telemetryAmbientTemp",
    formatNumber(
      output.environment
        ?.ambientTemperatureC,
      1
    )
  );

  const pressurePa =
    Number(
      output.environment
        ?.ambientPressurePa
    );

  const pressureKPa =
    Number.isFinite(
      pressurePa
    )
      ? pressurePa /
        1000
      : null;

  setText(
    "telemetryAmbientPressure",
    formatNumber(
      pressureKPa,
      1
    )
  );

  setText(
    "telemetryAirDensity",
    formatNumber(
      output.environment
        ?.airDensityKgM3,
      3
    )
  );

  const confidence =
    Number(
      output.confidence
        ?.overall
    );

  const confidencePercent =
    Number.isFinite(
      confidence
    )
      ? confidence *
        100
      : null;

  setText(
    "twinModelConfidence",
    formatNumber(
      confidencePercent,
      0
    )
  );

  setText(
    "physicsModelState",
    "ACTIVE"
  );
}

function handleTwinState(
  event
) {
  const state =
    event.detail;

  if (
    !state
  ) {
    return;
  }

  const source =
    state.activeSource
      ? String(
          state.activeSource
        ).toUpperCase()
      : "--";

  setText(
    "twinSource",
    source
  );

  setText(
    "twinSourceDetail",
    source
  );

  setText(
    "twinSynchronization",
    state
      .synchronizationStatus ||
    "--"
  );

  setText(
    "twinSyncStatus",
    state.synchronized
      ? "SYNCHRONIZED"
      : "NOT SYNCHRONIZED"
  );
}

function handleTelemetry(
  event
) {
  const frame =
    event.detail;

  if (
    !frame
  ) {
    return;
  }

  if (
    frame.engine
      ?.rpm !==
    null &&
    frame.engine
      ?.rpm !==
    undefined
  ) {
    setText(
      "telemetryRpm",
      formatInteger(
        frame.engine.rpm
      )
    );
  }

  if (
    frame.environment
      ?.altitudeM !==
    null &&
    frame.environment
      ?.altitudeM !==
    undefined
  ) {
    setText(
      "telemetryAltitude",
      formatInteger(
        frame.environment
          .altitudeM
      )
    );
  }

  if (
    frame.environment
      ?.ambientTemperatureC !==
    null &&
    frame.environment
      ?.ambientTemperatureC !==
    undefined
  ) {
    setText(
      "telemetryAmbientTemp",
      formatNumber(
        frame.environment
          .ambientTemperatureC,
        1
      )
    );
  }
}

function initializeUnavailableValues() {
  setText(
    "telemetryVibration",
    "--"
  );

  setText(
    "telemetryBatteryVoltage",
    "--"
  );

  setText(
    "telemetryAlternatorVoltage",
    "--"
  );

  setText(
    "healthIndex",
    "--"
  );

  setText(
    "estimatedRul",
    "--"
  );

  setText(
    "activeFaultCount",
    "0"
  );
}

function initializePhysicsStatus() {
  const status =
    window
      .PRATIRUP_PHYSICS
      ?.getStatus?.();

  if (
    !status
  ) {
    setText(
      "physicsModelState",
      "WAITING"
    );

    return;
  }

  if (
    status.modelRegistered
  ) {
    setText(
      "physicsModelState",
      "CONNECTED"
    );
  } else {
    setText(
      "physicsModelState",
      "WAITING"
    );
  }
}

window.addEventListener(
  "pratirup:physics-model-registered",
  () => {
    setText(
      "physicsModelState",
      "CONNECTED"
    );
  }
);

window.addEventListener(
  "pratirup:physics-model-unregistered",
  () => {
    setText(
      "physicsModelState",
      "DISCONNECTED"
    );
  }
);

window.addEventListener(
  "pratirup:physics-output",
  handlePhysicsOutput
);

window.addEventListener(
  "pratirup:twin-state",
  handleTwinState
);

window.addEventListener(
  "pratirup:telemetry",
  handleTelemetry
);

window.addEventListener(
  "pratirup:component-selected",
  event => {
    const name =
      event.detail?.name ||
      "COMPONENT";

    setText(
      "selectedComponentStatus",
      name
    );

    setText(
      "selectedComponentName",
      name
    );
  }
);

window.addEventListener(
  "pratirup:component-cleared",
  () => {
    setText(
      "selectedComponentStatus",
      "NONE"
    );

    setText(
      "selectedComponentName",
      "NO COMPONENT SELECTED"
    );
  }
);

window.addEventListener(
  "pratirup:isolation-change",
  event => {
    setText(
      "isolationStateText",
      event.detail?.value
        ? "ON"
        : "OFF"
    );
  }
);

function initializePhysicsDashboard() {
  initializeUnavailableValues();

  initializePhysicsStatus();

  const twinState =
    window
      .PRATIRUP_TWIN
      ?.getState?.();

  if (
    twinState
  ) {
    handleTwinState({
      detail:
        twinState
    });
  }

  const output =
    window
      .PRATIRUP_PHYSICS
      ?.getLastOutput?.();

  if (
    output
  ) {
    handlePhysicsOutput({
      detail:
        output
    });
  }

  console.log(
    `[PRATIRUP] Physics Dashboard ${PHYSICS_DASHBOARD_VERSION} ready.`
  );
}

if (
  document.readyState ===
  "loading"
) {
  document.addEventListener(
    "DOMContentLoaded",
    initializePhysicsDashboard,
    {
      once: true
    }
  );
} else {
  initializePhysicsDashboard();
}

window.PRATIRUP_PHYSICS_DASHBOARD = {
  version:
    PHYSICS_DASHBOARD_VERSION,

  refresh() {
    const output =
      window
        .PRATIRUP_PHYSICS
        ?.getLastOutput?.();

    if (
      output
    ) {
      handlePhysicsOutput({
        detail:
          output
      });
    }
  }
};
