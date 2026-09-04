"use strict";

const HEALTH_MONITOR_VERSION =
  "1.1.0";

const HEALTH_CONFIG = {

  minimumParameterScore:
    0,

  minimumOverallCoverage:
    0.50,

  tolerances: {

    chtC:
      18,

    egtC:
      35,

    oilTemperatureC:
      15,

    oilPressureKPa:
      70,

    fuelFlowFraction:
      0.15,

    rpm:
      120,

    alternatorVoltageV:
      1.5,

    batteryVoltageV:
      1.5,

    vibrationG:
      0.35

  },

  weights: {

    thermal:
      1.2,

    combustion:
      1.2,

    lubrication:
      1.2,

    fuelSystem:
      1.0,

    electrical:
      0.8,

    vibration:
      1.0,

    mechanical:
      0.8

  },

  bands: {

    nominal:
      85,

    watch:
      70,

    degraded:
      50

  }

};

const healthState = {

  initialized:
    false,

  observedState:
    null,

  expectedState:
    null,

  latestHealth:
    null,

  calculationCount:
    0,

  lastCalculationTimestamp:
    null

};

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

function isFiniteNumber(
  value
) {

  return (
    typeof value === "number" &&
    Number.isFinite(value)
  );

}

function safeNumber(
  value
) {

  return isFiniteNumber(
    value
  )
    ? value
    : null;

}

function clamp(
  value,
  minimum,
  maximum
) {

  if (
    !isFiniteNumber(value)
  ) {

    return null;

  }

  return Math.min(
    maximum,
    Math.max(
      minimum,
      value
    )
  );

}

function scoreResidual(
  observed,
  expected,
  tolerance
) {

  observed =
    safeNumber(
      observed
    );

  expected =
    safeNumber(
      expected
    );

  tolerance =
    safeNumber(
      tolerance
    );

  if (
    observed === null ||
    expected === null ||
    tolerance === null ||
    tolerance <= 0
  ) {

    return null;

  }

  const residual =
    observed -
    expected;

  const absoluteResidual =
    Math.abs(
      residual
    );

  const ratio =
    absoluteResidual /
    tolerance;

  if (
    ratio <= 1
  ) {

    return {

      available:
        true,

      score:
        100 -
        ratio *
        10,

      observed,

      expected,

      tolerance,

      residual,

      absoluteResidual,

      ratio

    };

  }

  const score =

    90 -
    (
      ratio -
      1
    ) *
    20;

  return {

    available:
      true,

    score:
      clamp(
        score,
        HEALTH_CONFIG
          .minimumParameterScore,
        100
      ),

    observed,

    expected,

    tolerance,

    residual,

    absoluteResidual,

    ratio

  };

}

function scoreFractionalResidual(
  observed,
  expected,
  allowedFraction
) {

  observed =
    safeNumber(
      observed
    );

  expected =
    safeNumber(
      expected
    );

  allowedFraction =
    safeNumber(
      allowedFraction
    );

  if (
    observed === null ||
    expected === null ||
    allowedFraction === null ||
    allowedFraction <= 0
  ) {

    return null;

  }

  if (
    Math.abs(
      expected
    ) <
    1e-9
  ) {

    return null;

  }

  const allowedDeviation =

    Math.abs(
      expected
    ) *
    allowedFraction;

  return scoreResidual(
    observed,
    expected,
    allowedDeviation
  );

}

function averageScores(
  results
) {

  if (
    !Array.isArray(
      results
    )
  ) {

    return null;

  }

  const valid =

    results.filter(
      result =>
        result &&
        isFiniteNumber(
          result.score
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
        result
      ) =>
        sum +
        result.score,
      0
    );

  return total /
    valid.length;

}

function calculateParameterCoverage(
  results
) {

  if (
    !Array.isArray(
      results
    ) ||
    results.length === 0
  ) {

    return {

      available:
        0,

      total:
        0,

      fraction:
        0

    };

  }

  const available =

    results.filter(
      result =>
        result &&
        isFiniteNumber(
          result.score
        )
    ).length;

  return {

    available,

    total:
      results.length,

    fraction:
      available /
      results.length

  };

}

function calculateThermalHealth(
  observed,
  expected
) {

  const results = [

    scoreResidual(
      observed?.cht
        ?.cylinder1C,
      expected?.cht
        ?.cylinder1C,
      HEALTH_CONFIG
        .tolerances
        .chtC
    ),

    scoreResidual(
      observed?.cht
        ?.cylinder2C,
      expected?.cht
        ?.cylinder2C,
      HEALTH_CONFIG
        .tolerances
        .chtC
    ),

    scoreResidual(
      observed?.cht
        ?.cylinder3C,
      expected?.cht
        ?.cylinder3C,
      HEALTH_CONFIG
        .tolerances
        .chtC
    ),

    scoreResidual(
      observed?.cht
        ?.cylinder4C,
      expected?.cht
        ?.cylinder4C,
      HEALTH_CONFIG
        .tolerances
        .chtC
    )

  ];

  const score =
    averageScores(
      results
    );

  return {

    available:
      isFiniteNumber(
        score
      ),

    score,

    coverage:
      calculateParameterCoverage(
        results
      ),

    cylinders:
      results

  };

}

function calculateCombustionHealth(
  observed,
  expected
) {

  const results = [

    scoreResidual(
      observed?.egt
        ?.cylinder1C,
      expected?.egt
        ?.cylinder1C,
      HEALTH_CONFIG
        .tolerances
        .egtC
    ),

    scoreResidual(
      observed?.egt
        ?.cylinder2C,
      expected?.egt
        ?.cylinder2C,
      HEALTH_CONFIG
        .tolerances
        .egtC
    ),

    scoreResidual(
      observed?.egt
        ?.cylinder3C,
      expected?.egt
        ?.cylinder3C,
      HEALTH_CONFIG
        .tolerances
        .egtC
    ),

    scoreResidual(
      observed?.egt
        ?.cylinder4C,
      expected?.egt
        ?.cylinder4C,
      HEALTH_CONFIG
        .tolerances
        .egtC
    )

  ];

  const score =
    averageScores(
      results
    );

  return {

    available:
      isFiniteNumber(
        score
      ),

    score,

    coverage:
      calculateParameterCoverage(
        results
      ),

    cylinders:
      results

  };

}

function calculateLubricationHealth(
  observed,
  expected
) {

  const pressure =
    scoreResidual(

      observed?.oil
        ?.pressureKPa,

      expected?.oil
        ?.pressureKPa,

      HEALTH_CONFIG
        .tolerances
        .oilPressureKPa

    );

  const temperature =
    scoreResidual(

      observed?.oil
        ?.temperatureC,

      expected?.oil
        ?.temperatureC,

      HEALTH_CONFIG
        .tolerances
        .oilTemperatureC

    );

  const results = [
    pressure,
    temperature
  ];

  const score =
    averageScores(
      results
    );

  return {

    available:
      isFiniteNumber(
        score
      ),

    score,

    coverage:
      calculateParameterCoverage(
        results
      ),

    pressure,

    temperature

  };

}

function calculateFuelHealth(
  observed,
  expected
) {

  const flow =
    scoreFractionalResidual(

      observed?.fuel
        ?.flowKgPerSecond,

      expected?.fuel
        ?.flowKgPerSecond,

      HEALTH_CONFIG
        .tolerances
        .fuelFlowFraction

    );

  const results = [
    flow
  ];

  const score =
    averageScores(
      results
    );

  return {

    available:
      isFiniteNumber(
        score
      ),

    score,

    coverage:
      calculateParameterCoverage(
        results
      ),

    flow

  };

}

function calculateMechanicalHealth(
  observed,
  expected
) {

  const rpm =
    scoreResidual(

      observed?.engine
        ?.rpm,

      expected?.engine
        ?.expectedRpm,

      HEALTH_CONFIG
        .tolerances
        .rpm

    );

  const results = [
    rpm
  ];

  const score =
    averageScores(
      results
    );

  return {

    available:
      isFiniteNumber(
        score
      ),

    score,

    coverage:
      calculateParameterCoverage(
        results
      ),

    rpm

  };

}

function calculateElectricalHealth(
  observed,
  expected
) {

  const alternator =
    scoreResidual(

      observed?.electrical
        ?.alternatorVoltageV,

      expected?.electrical
        ?.alternatorVoltageV,

      HEALTH_CONFIG
        .tolerances
        .alternatorVoltageV

    );

  const battery =
    scoreResidual(

      observed?.electrical
        ?.batteryVoltageV,

      expected?.electrical
        ?.batteryVoltageV,

      HEALTH_CONFIG
        .tolerances
        .batteryVoltageV

    );

  const results = [
    alternator,
    battery
  ];

  const score =
    averageScores(
      results
    );

  return {

    available:
      isFiniteNumber(
        score
      ),

    score,

    coverage:
      calculateParameterCoverage(
        results
      ),

    alternator,

    battery

  };

}

function calculateVibrationHealth(
  observed,
  expected
) {

  const overall =
    scoreResidual(

      observed?.vibration
        ?.overallG,

      expected?.vibration
        ?.overallG,

      HEALTH_CONFIG
        .tolerances
        .vibrationG

    );

  const results = [
    overall
  ];

  const score =
    averageScores(
      results
    );

  return {

    available:
      isFiniteNumber(
        score
      ),

    score,

    coverage:
      calculateParameterCoverage(
        results
      ),

    overall

  };

}

function calculateOverallHealth(
  subsystems
) {

  const entries = [

    [
      subsystems.thermal
        ?.score,
      HEALTH_CONFIG
        .weights
        .thermal
    ],

    [
      subsystems.combustion
        ?.score,
      HEALTH_CONFIG
        .weights
        .combustion
    ],

    [
      subsystems.lubrication
        ?.score,
      HEALTH_CONFIG
        .weights
        .lubrication
    ],

    [
      subsystems.fuelSystem
        ?.score,
      HEALTH_CONFIG
        .weights
        .fuelSystem
    ],

    [
      subsystems.electrical
        ?.score,
      HEALTH_CONFIG
        .weights
        .electrical
    ],

    [
      subsystems.vibration
        ?.score,
      HEALTH_CONFIG
        .weights
        .vibration
    ],

    [
      subsystems.mechanical
        ?.score,
      HEALTH_CONFIG
        .weights
        .mechanical
    ]

  ];

  let weightedTotal =
    0;

  let weightTotal =
    0;

  entries.forEach(
    (
      [
        score,
        weight
      ]
    ) => {

      if (
        !isFiniteNumber(
          score
        ) ||
        !isFiniteNumber(
          weight
        ) ||
        weight <= 0
      ) {

        return;

      }

      weightedTotal +=
        score *
        weight;

      weightTotal +=
        weight;

    }
  );

  if (
    weightTotal === 0
  ) {

    return null;

  }

  return weightedTotal /
    weightTotal;

}

function classifyHealth(
  score,
  coverageFraction
) {

  if (
    !isFiniteNumber(
      score
    )
  ) {

    return "INSUFFICIENT_DATA";

  }

  if (
    !isFiniteNumber(
      coverageFraction
    ) ||
    coverageFraction <
      HEALTH_CONFIG
        .minimumOverallCoverage
  ) {

    return "INSUFFICIENT_DATA";

  }

  if (
    score >=
    HEALTH_CONFIG
      .bands
      .nominal
  ) {

    return "NOMINAL";

  }

  if (
    score >=
    HEALTH_CONFIG
      .bands
      .watch
  ) {

    return "WATCH";

  }

  if (
    score >=
    HEALTH_CONFIG
      .bands
      .degraded
  ) {

    return "DEGRADED";

  }

  return "CRITICAL";

}

function calculateCoverage(
  subsystems
) {

  const subsystemEntries = [

    [
      "thermal",
      subsystems.thermal
        ?.score
    ],

    [
      "combustion",
      subsystems.combustion
        ?.score
    ],

    [
      "lubrication",
      subsystems.lubrication
        ?.score
    ],

    [
      "fuelSystem",
      subsystems.fuelSystem
        ?.score
    ],

    [
      "electrical",
      subsystems.electrical
        ?.score
    ],

    [
      "vibration",
      subsystems.vibration
        ?.score
    ],

    [
      "mechanical",
      subsystems.mechanical
        ?.score
    ]

  ];

  const availableSubsystems =

    subsystemEntries
      .filter(
        (
          [
            ,
            score
          ]
        ) =>
          isFiniteNumber(
            score
          )
      )
      .map(
        (
          [
            name
          ]
        ) =>
          name
      );

  const unavailableSubsystems =

    subsystemEntries
      .filter(
        (
          [
            ,
            score
          ]
        ) =>
          !isFiniteNumber(
            score
          )
      )
      .map(
        (
          [
            name
          ]
        ) =>
          name
      );

  const available =
    availableSubsystems.length;

  const total =
    subsystemEntries.length;

  return {

    availableSubsystems:
      available,

    totalSubsystems:
      total,

    fraction:

      total > 0

        ? available /
          total

        : 0,

    percentage:

      total > 0

        ? (
            available /
            total
          ) *
          100

        : 0,

    available:
      availableSubsystems,

    unavailable:
      unavailableSubsystems

  };

}

function createUnavailableHealth(
  reason
) {

  return {

    timestamp:
      Date.now(),

    status:
      "INSUFFICIENT_DATA",

    overallIndex:
      null,

    confidence:
      0,

    reason:
      reason ||
      "Observed and expected Digital Twin states are not available.",

    coverage: {

      availableSubsystems:
        0,

      totalSubsystems:
        7,

      fraction:
        0,

      percentage:
        0,

      available:
        [],

      unavailable: [

        "thermal",
        "combustion",
        "lubrication",
        "fuelSystem",
        "electrical",
        "vibration",
        "mechanical"

      ]

    },

    subsystems: {

      thermal:
        null,

      combustion:
        null,

      lubrication:
        null,

      fuelSystem:
        null,

      vibration:
        null,

      electrical:
        null,

      mechanical:
        null

    }

  };

}

function calculateHealth() {

  const observed =
    healthState
      .observedState;

  const expected =
    healthState
      .expectedState;

  if (
    !observed ||
    !expected
  ) {

    const unavailable =
      createUnavailableHealth(
        !observed
          ? "Observed engine state unavailable."
          : "Expected physics state unavailable."
      );

    healthState.latestHealth =
      unavailable;

    healthState.calculationCount++;

    healthState.lastCalculationTimestamp =
      unavailable.timestamp;

    publishHealth(
      unavailable
    );

    return unavailable;

  }

  const subsystems = {

    thermal:
      calculateThermalHealth(
        observed,
        expected
      ),

    combustion:
      calculateCombustionHealth(
        observed,
        expected
      ),

    lubrication:
      calculateLubricationHealth(
        observed,
        expected
      ),

    fuelSystem:
      calculateFuelHealth(
        observed,
        expected
      ),

    vibration:
      calculateVibrationHealth(
        observed,
        expected
      ),

    electrical:
      calculateElectricalHealth(
        observed,
        expected
      ),

    mechanical:
      calculateMechanicalHealth(
        observed,
        expected
      )

  };

  const coverage =
    calculateCoverage(
      subsystems
    );

  const calculatedOverallIndex =
    calculateOverallHealth(
      subsystems
    );

  const overallIndex =

    isFiniteNumber(
      calculatedOverallIndex
    )

      ? clamp(
          calculatedOverallIndex,
          0,
          100
        )

      : null;

  const status =
    classifyHealth(
      overallIndex,
      coverage.fraction
    );

  const confidence =
    coverage.fraction;

  const result = {

    timestamp:
      Date.now(),

    version:
      HEALTH_MONITOR_VERSION,

    status,

    overallIndex,

    confidence,

    coverage,

    subsystems

  };

  if (
    status ===
    "INSUFFICIENT_DATA"
  ) {

    result.reason =

      coverage.availableSubsystems ===
      0

        ? "No subsystem has sufficient observed-vs-expected data."

        : "Subsystem coverage is below the minimum required for an overall health classification.";

  }

  healthState.latestHealth =
    result;

  healthState.calculationCount++;

  healthState.lastCalculationTimestamp =
    result.timestamp;

  publishHealth(
    result
  );

  return result;

}

function publishHealth(
  health
) {

  window.dispatchEvent(

    new CustomEvent(
      "pratirup:health-update",
      {

        detail:
          cloneValue(
            health
          )

      }
    )

  );

}

window.addEventListener(
  "pratirup:observed-state",
  event => {

    const observed =
      event.detail
        ?.observedState;

    if (!observed) {

      return;

    }

    healthState.observedState =
      cloneValue(
        observed
      );

    calculateHealth();

  }
);

window.addEventListener(
  "pratirup:expected-state",
  event => {

    healthState.expectedState =

      event.detail

        ? cloneValue(
            event.detail
          )

        : null;

    calculateHealth();

  }
);

window.addEventListener(
  "pratirup:residual-state",
  event => {

    const residual =
      event.detail;

    if (!residual) {

      return;

    }

  }
);

window.addEventListener(
  "pratirup:health-update",
  event => {

    const health =
      event.detail;

    if (!health) {

      return;

    }

    const healthIndexElement =
      document.getElementById(
        "healthIndex"
      );

    const healthStateElement =
      document.getElementById(
        "healthState"
      );

    if (
      healthIndexElement
    ) {

      healthIndexElement.textContent =

        isFiniteNumber(
          health.overallIndex
        )

          ? `${Math.round(
              health.overallIndex
            )}%`

          : "--";

    }

    if (
      healthStateElement
    ) {

      healthStateElement.textContent =
        health.status ||
        "WAITING";

    }

  }
);

function getHealth() {

  return healthState.latestHealth

    ? cloneValue(
        healthState.latestHealth
      )

    : null;

}

function getStatus() {

  const latest =
    healthState.latestHealth;

  return {

    version:
      HEALTH_MONITOR_VERSION,

    initialized:
      healthState.initialized,

    calculationCount:
      healthState.calculationCount,

    lastCalculationTimestamp:
      healthState
        .lastCalculationTimestamp,

    hasObservedState:
      Boolean(
        healthState.observedState
      ),

    hasExpectedState:
      Boolean(
        healthState.expectedState
      ),

    latestStatus:
      latest?.status ??
      null,

    overallIndex:
      latest?.overallIndex ??
      null,

    coverage:
      latest?.coverage
        ?.fraction ??
      0,

    confidence:
      latest?.confidence ??
      0

  };

}

function getObservedState() {

  return healthState.observedState

    ? cloneValue(
        healthState.observedState
      )

    : null;

}

function getExpectedState() {

  return healthState.expectedState

    ? cloneValue(
        healthState.expectedState
      )

    : null;

}

function resetHealthMonitor() {

  healthState.observedState =
    null;

  healthState.expectedState =
    null;

  healthState.latestHealth =
    null;

  healthState.calculationCount =
    0;

  healthState.lastCalculationTimestamp =
    null;

  const healthIndexElement =
    document.getElementById(
      "healthIndex"
    );

  const healthStateElement =
    document.getElementById(
      "healthState"
    );

  if (
    healthIndexElement
  ) {

    healthIndexElement.textContent =
      "--";

  }

  if (
    healthStateElement
  ) {

    healthStateElement.textContent =
      "WAITING";

  }

  window.dispatchEvent(

    new CustomEvent(
      "pratirup:health-reset"
    )

  );

}

window.PRATIRUP_HEALTH = {

  version:
    HEALTH_MONITOR_VERSION,

  get:
    getHealth,

  getStatus,

  getObservedState,

  getExpectedState,

  calculate:
    calculateHealth,

  reset:
    resetHealthMonitor,

  config:
    HEALTH_CONFIG

};

healthState.initialized =
  true;

window.dispatchEvent(

  new CustomEvent(
    "pratirup:health-monitor-ready",
    {

      detail: {

        version:
          HEALTH_MONITOR_VERSION

      }

    }
  )

);

console.log(
  `[PRATIRUP] Health Monitor ${HEALTH_MONITOR_VERSION} ready.`
);

console.log(
  "[PRATIRUP] Health method: null-safe observed-vs-expected residual analysis."
);
