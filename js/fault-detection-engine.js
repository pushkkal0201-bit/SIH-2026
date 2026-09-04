(function () {

  "use strict";

  const CONFIG = {

    historyLimit: 120,

    minimumSamplesForTrend: 5,

    thresholds: {

      egtSpreadWarning: 60,

      egtSpreadCritical: 120,

      chtSpreadWarning: 25,

      chtSpreadCritical: 60,

      chtWarning: 220,

      chtCritical: 260,

      egtWarning: 850,

      egtCritical: 950,

      vibrationWarning: 1.5,

      vibrationCritical: 3.0,

      oilPressureLow: 250,

      oilPressureCritical: 150,

      oilTemperatureWarning: 115,

      oilTemperatureCritical: 135,

      fuelDeviationWarning: 0.20,

      batteryVoltageLow: 11.5,

      alternatorVoltageLow: 12.5

    }

  };

  let running = true;

  let latestResult = null;

  let lastTimestamp = 0;

  const history = [];

  function clamp(
    value,
    minimum = 0,
    maximum = 1
  ) {

    return Math.min(
      maximum,
      Math.max(
        minimum,
        value
      )
    );

  }

  function finiteNumber(
    value,
    fallback = 0
  ) {

    return (
      typeof value === "number" &&
      Number.isFinite(value)
    )
      ? value
      : fallback;

  }

  function average(values) {

    if (
      !Array.isArray(values) ||
      values.length === 0
    ) {

      return 0;

    }

    const valid =
      values.filter(
        value =>
          typeof value === "number" &&
          Number.isFinite(value)
      );

    if (valid.length === 0) {

      return 0;

    }

    return (
      valid.reduce(
        (sum, value) =>
          sum + value,
        0
      ) /
      valid.length
    );

  }

  function maximum(values) {

    if (
      !Array.isArray(values)
    ) {

      return 0;

    }

    const valid =
      values.filter(
        value =>
          typeof value === "number" &&
          Number.isFinite(value)
      );

    if (valid.length === 0) {

      return 0;

    }

    return Math.max(
      ...valid
    );

  }

  function minimum(values) {

    if (
      !Array.isArray(values)
    ) {

      return 0;

    }

    const valid =
      values.filter(
        value =>
          typeof value === "number" &&
          Number.isFinite(value)
      );

    if (valid.length === 0) {

      return 0;

    }

    return Math.min(
      ...valid
    );

  }

  function spread(values) {

    if (
      !Array.isArray(values)
    ) {

      return 0;

    }

    const valid =
      values.filter(
        value =>
          typeof value === "number" &&
          Number.isFinite(value)
      );

    if (valid.length < 2) {

      return 0;

    }

    return (
      Math.max(...valid) -
      Math.min(...valid)
    );

  }

  function normalizedRisk(
    value,
    warning,
    critical
  ) {

    value =
      finiteNumber(
        value
      );

    if (
      value <= warning
    ) {

      return 0;

    }

    if (
      value >= critical
    ) {

      return 1;

    }

    return clamp(
      (
        value -
        warning
      ) /
      (
        critical -
        warning
      )
    );

  }

  function inverseRisk(
    value,
    warning,
    critical
  ) {

    value =
      finiteNumber(
        value
      );

    if (
      value >= warning
    ) {

      return 0;

    }

    if (
      value <= critical
    ) {

      return 1;

    }

    return clamp(
      (
        warning -
        value
      ) /
      (
        warning -
        critical
      )
    );

  }

  function severity(score) {

    if (
      score >= 0.80
    ) {

      return "CRITICAL";

    }

    if (
      score >= 0.55
    ) {

      return "HIGH";

    }

    if (
      score >= 0.30
    ) {

      return "WARNING";

    }

    if (
      score >= 0.10
    ) {

      return "ADVISORY";

    }

    return "NORMAL";

  }

  function extractTelemetry(state) {

    const source =

      state?.observedState ||

      state?.observed ||

      state?.telemetry ||

      state?.engine ||

      state ||

      {};

    const engine =
      source.engine ||
      {};

    const cht =
      source.cht ||
      {};

    const egt =
      source.egt ||
      {};

    const oil =
      source.oil ||
      {};

    const fuel =
      source.fuel ||
      {};

    const vibration =
      source.vibration ||
      {};

    const electrical =
      source.electrical ||
      {};

    const environment =
      source.environment ||
      {};

    const mission =
      source.mission ||
      {};

    return {

      timestamp:
        Date.now(),

      rpm:
        finiteNumber(
          engine.rpm
        ),

      throttle:
        finiteNumber(
          engine.throttlePercent
        ),

      load:
        finiteNumber(
          engine.loadPercent
        ),

      power:
        finiteNumber(
          engine.powerKw
        ),

      torque:
        finiteNumber(
          engine.torqueNm
        ),

      cht: [

        finiteNumber(
          cht.cylinder1C
        ),

        finiteNumber(
          cht.cylinder2C
        ),

        finiteNumber(
          cht.cylinder3C
        ),

        finiteNumber(
          cht.cylinder4C
        )

      ],

      egt: [

        finiteNumber(
          egt.cylinder1C
        ),

        finiteNumber(
          egt.cylinder2C
        ),

        finiteNumber(
          egt.cylinder3C
        ),

        finiteNumber(
          egt.cylinder4C
        )

      ],

      oilPressure:
        finiteNumber(
          oil.pressureKPa
        ),

      oilTemperature:
        finiteNumber(
          oil.temperatureC
        ),

      fuelFlow:
        finiteNumber(
          fuel.flowKgPerSecond
        ),

      fuelPressure:
        finiteNumber(
          fuel.pressureKPa
        ),

      vibration:
        finiteNumber(
          vibration.overallG
        ),

      vibrationX:
        finiteNumber(
          vibration.xG
        ),

      vibrationY:
        finiteNumber(
          vibration.yG
        ),

      vibrationZ:
        finiteNumber(
          vibration.zG
        ),

      batteryVoltage:
        finiteNumber(
          electrical.batteryVoltageV
        ),

      batteryCurrent:
        finiteNumber(
          electrical.batteryCurrentA
        ),

      alternatorVoltage:
        finiteNumber(
          electrical.alternatorVoltageV
        ),

      alternatorCurrent:
        finiteNumber(
          electrical.alternatorCurrentA
        ),

      altitude:
        finiteNumber(
          environment.altitudeM
        ),

      ambientTemperature:
        finiteNumber(
          environment.ambientTemperatureC
        ),

      missionId:
        mission.missionId ||
        null,

      missionPhase:
        mission.phase ||
        null,

      elapsedTime:
        finiteNumber(
          mission.elapsedTimeSec
        )

    };

  }

  function pushHistory(sample) {

    history.push(
      sample
    );

    while (
      history.length >
      CONFIG.historyLimit
    ) {

      history.shift();

    }

  }

  function calculateTrend(key) {

    if (
      history.length <
      CONFIG.minimumSamplesForTrend
    ) {

      return 0;

    }

    const recent =
      history.slice(
        -CONFIG.minimumSamplesForTrend
      );

    const first =
      finiteNumber(
        recent[0]?.[key]
      );

    const last =
      finiteNumber(
        recent[
          recent.length - 1
        ]?.[key]
      );

    return (
      last -
      first
    );

  }

  function calculateArrayAverageTrend(key) {

    if (
      history.length <
      CONFIG.minimumSamplesForTrend
    ) {

      return 0;

    }

    const recent =
      history.slice(
        -CONFIG.minimumSamplesForTrend
      );

    const first =
      average(
        recent[0]?.[key]
      );

    const last =
      average(
        recent[
          recent.length - 1
        ]?.[key]
      );

    return (
      last -
      first
    );

  }

  function createFault(
    id,
    name,
    score,
    evidence,
    subsystem
  ) {

    score =
      clamp(
        finiteNumber(
          score
        )
      );

    return {

      id,

      name,

      subsystem,

      score:
        Number(
          score.toFixed(3)
        ),

      probability:
        Number(
          (
            score *
            100
          ).toFixed(1)
        ),

      severity:
        severity(
          score
        ),

      active:
        score >= 0.30,

      evidence:
        Array.isArray(
          evidence
        )
          ? evidence
          : [],

      timestamp:
        Date.now()

    };

  }

  function detectMisfire(sample) {

    const egtSpread =
      spread(
        sample.egt
      );

    const chtSpread =
      spread(
        sample.cht
      );

    const vibrationRisk =
      normalizedRisk(
        sample.vibration,
        CONFIG.thresholds.vibrationWarning,
        CONFIG.thresholds.vibrationCritical
      );

    const egtRisk =
      normalizedRisk(
        egtSpread,
        CONFIG.thresholds.egtSpreadWarning,
        CONFIG.thresholds.egtSpreadCritical
      );

    const chtRisk =
      normalizedRisk(
        chtSpread,
        CONFIG.thresholds.chtSpreadWarning,
        CONFIG.thresholds.chtSpreadCritical
      );

    const score =
      (
        egtRisk * 0.45 +
        vibrationRisk * 0.35 +
        chtRisk * 0.20
      );

    const evidence = [];

    if (
      egtSpread >
      CONFIG.thresholds.egtSpreadWarning
    ) {

      evidence.push(
        `EGT cylinder spread ${egtSpread.toFixed(1)} °C`
      );

    }

    if (
      sample.vibration >
      CONFIG.thresholds.vibrationWarning
    ) {

      evidence.push(
        `Vibration ${sample.vibration.toFixed(2)} g`
      );

    }

    if (
      chtSpread >
      CONFIG.thresholds.chtSpreadWarning
    ) {

      evidence.push(
        `CHT cylinder spread ${chtSpread.toFixed(1)} °C`
      );

    }

    return createFault(
      "misfire",
      "Misfire Condition",
      score,
      evidence,
      "combustion"
    );

  }

  function detectInjector(sample) {

    const egtSpread =
      spread(
        sample.egt
      );

    const chtSpread =
      spread(
        sample.cht
      );

    const egtRisk =
      normalizedRisk(
        egtSpread,
        45,
        100
      );

    const chtRisk =
      normalizedRisk(
        chtSpread,
        20,
        50
      );

    const expectedFuelFlow =
      sample.power > 0
        ? sample.power * 0.00007
        : 0;

    let fuelResidual = 0;

    if (
      expectedFuelFlow > 0 &&
      sample.fuelFlow > 0
    ) {

      fuelResidual =
        Math.abs(
          sample.fuelFlow -
          expectedFuelFlow
        ) /
        expectedFuelFlow;

    }

    const fuelRisk =
      normalizedRisk(
        fuelResidual,
        CONFIG.thresholds.fuelDeviationWarning,
        0.45
      );

    const score =
      (
        egtRisk * 0.45 +
        chtRisk * 0.20 +
        fuelRisk * 0.35
      );

    const evidence = [];

    if (
      egtRisk > 0
    ) {

      evidence.push(
        `Cylinder EGT imbalance ${egtSpread.toFixed(1)} °C`
      );

    }

    if (
      fuelRisk > 0
    ) {

      evidence.push(
        `Fuel-flow deviation ${(fuelResidual * 100).toFixed(1)} %`
      );

    }

    return createFault(
      "injector",
      "Injector Abnormality",
      score,
      evidence,
      "fuel"
    );

  }

  function detectCooling(sample) {

    const avgCht =
      average(
        sample.cht
      );

    const chtTrend =
      calculateArrayAverageTrend(
        "cht"
      );

    const temperatureRisk =
      normalizedRisk(
        avgCht,
        CONFIG.thresholds.chtWarning,
        CONFIG.thresholds.chtCritical
      );

    const trendRisk =
      normalizedRisk(
        chtTrend,
        4,
        18
      );

    const score =
      (
        temperatureRisk * 0.65 +
        trendRisk * 0.35
      );

    const evidence = [];

    if (
      temperatureRisk > 0
    ) {

      evidence.push(
        `Average CHT ${avgCht.toFixed(1)} °C`
      );

    }

    if (
      trendRisk > 0
    ) {

      evidence.push(
        `CHT rising trend +${chtTrend.toFixed(1)} °C`
      );

    }

    return createFault(
      "cooling",
      "Cooling Degradation",
      score,
      evidence,
      "thermal"
    );

  }

  function detectLubrication(sample) {

    const pressureRisk =
      inverseRisk(
        sample.oilPressure,
        CONFIG.thresholds.oilPressureLow,
        CONFIG.thresholds.oilPressureCritical
      );

    const temperatureRisk =
      normalizedRisk(
        sample.oilTemperature,
        CONFIG.thresholds.oilTemperatureWarning,
        CONFIG.thresholds.oilTemperatureCritical
      );

    const pressureTrend =
      calculateTrend(
        "oilPressure"
      );

    const trendRisk =
      normalizedRisk(
        -pressureTrend,
        10,
        50
      );

    const score =
      (
        pressureRisk * 0.55 +
        temperatureRisk * 0.30 +
        trendRisk * 0.15
      );

    const evidence = [];

    if (
      pressureRisk > 0
    ) {

      evidence.push(
        `Low oil pressure ${sample.oilPressure.toFixed(1)} kPa`
      );

    }

    if (
      temperatureRisk > 0
    ) {

      evidence.push(
        `Oil temperature ${sample.oilTemperature.toFixed(1)} °C`
      );

    }

    if (
      trendRisk > 0
    ) {

      evidence.push(
        "Oil pressure shows a decreasing trend"
      );

    }

    return createFault(
      "lubrication",
      "Lubrication Issue",
      score,
      evidence,
      "lubrication"
    );

  }

  function detectSensorDrift(sample) {

    if (
      history.length < 3
    ) {

      return createFault(
        "sensor-drift",
        "Sensor Drift / Failure",
        0,
        [],
        "instrumentation"
      );

    }

    const previous =
      history[
        history.length - 2
      ];

    const rpmDelta =
      Math.abs(
        sample.rpm -
        previous.rpm
      );

    const oilDelta =
      Math.abs(
        sample.oilPressure -
        previous.oilPressure
      );

    const batteryDelta =
      Math.abs(
        sample.batteryVoltage -
        previous.batteryVoltage
      );

    let score = 0;

    const evidence = [];

    if (
      rpmDelta > 1800
    ) {

      score += 0.35;

      evidence.push(
        `Abrupt RPM change ${rpmDelta.toFixed(0)} rpm`
      );

    }

    if (
      oilDelta > 150
    ) {

      score += 0.35;

      evidence.push(
        `Abrupt oil-pressure change ${oilDelta.toFixed(1)} kPa`
      );

    }

    if (
      batteryDelta > 5
    ) {

      score += 0.30;

      evidence.push(
        `Abrupt battery-voltage change ${batteryDelta.toFixed(1)} V`
      );

    }

    if (
      sample.rpm < 0 ||
      sample.oilPressure < 0 ||
      sample.batteryVoltage < 0
    ) {

      score =
        Math.max(
          score,
          0.9
        );

      evidence.push(
        "Physically invalid sensor value detected"
      );

    }

    return createFault(
      "sensor-drift",
      "Sensor Drift / Failure",
      score,
      evidence,
      "instrumentation"
    );

  }

  function detectCombustion(sample) {

    const egtSpread =
      spread(
        sample.egt
      );

    const chtSpread =
      spread(
        sample.cht
      );

    const egtRisk =
      normalizedRisk(
        egtSpread,
        45,
        100
      );

    const chtRisk =
      normalizedRisk(
        chtSpread,
        20,
        50
      );

    const vibrationRisk =
      normalizedRisk(
        sample.vibration,
        1.2,
        2.5
      );

    const score =
      (
        egtRisk * 0.40 +
        chtRisk * 0.25 +
        vibrationRisk * 0.35
      );

    const evidence = [];

    if (
      egtRisk > 0
    ) {

      evidence.push(
        `EGT imbalance ${egtSpread.toFixed(1)} °C`
      );

    }

    if (
      chtRisk > 0
    ) {

      evidence.push(
        `CHT imbalance ${chtSpread.toFixed(1)} °C`
      );

    }

    if (
      vibrationRisk > 0
    ) {

      evidence.push(
        `Combustion-associated vibration ${sample.vibration.toFixed(2)} g`
      );

    }

    return createFault(
      "combustion-instability",
      "Combustion Instability",
      score,
      evidence,
      "combustion"
    );

  }

  function detectOverheating(sample) {

    const avgCht =
      average(
        sample.cht
      );

    const avgEgt =
      average(
        sample.egt
      );

    const chtRisk =
      normalizedRisk(
        avgCht,
        CONFIG.thresholds.chtWarning,
        CONFIG.thresholds.chtCritical
      );

    const egtRisk =
      normalizedRisk(
        avgEgt,
        CONFIG.thresholds.egtWarning,
        CONFIG.thresholds.egtCritical
      );

    const chtTrend =
      calculateArrayAverageTrend(
        "cht"
      );

    const egtTrend =
      calculateArrayAverageTrend(
        "egt"
      );

    const trendRisk =
      Math.max(

        normalizedRisk(
          chtTrend,
          5,
          20
        ),

        normalizedRisk(
          egtTrend,
          10,
          45
        )

      );

    const score =
      (
        chtRisk * 0.40 +
        egtRisk * 0.35 +
        trendRisk * 0.25
      );

    const evidence = [];

    if (
      chtRisk > 0
    ) {

      evidence.push(
        `High average CHT ${avgCht.toFixed(1)} °C`
      );

    }

    if (
      egtRisk > 0
    ) {

      evidence.push(
        `High average EGT ${avgEgt.toFixed(1)} °C`
      );

    }

    if (
      trendRisk > 0
    ) {

      evidence.push(
        "Sustained thermal rise detected"
      );

    }

    return createFault(
      "overheating",
      "Overheating Trend",
      score,
      evidence,
      "thermal"
    );

  }

  function detectVibration(sample) {

    const vibrationRisk =
      normalizedRisk(
        sample.vibration,
        CONFIG.thresholds.vibrationWarning,
        CONFIG.thresholds.vibrationCritical
      );

    const vibrationTrend =
      calculateTrend(
        "vibration"
      );

    const trendRisk =
      normalizedRisk(
        vibrationTrend,
        0.2,
        1.0
      );

    const score =
      (
        vibrationRisk * 0.75 +
        trendRisk * 0.25
      );

    const evidence = [];

    if (
      vibrationRisk > 0
    ) {

      evidence.push(
        `Vibration amplitude ${sample.vibration.toFixed(2)} g`
      );

    }

    if (
      trendRisk > 0
    ) {

      evidence.push(
        `Increasing vibration trend +${vibrationTrend.toFixed(2)} g`
      );

    }

    return createFault(
      "vibration",
      "Abnormal Vibration",
      score,
      evidence,
      "mechanical"
    );

  }

  function evaluateElectrical(sample) {

    const batteryRisk =
      inverseRisk(
        sample.batteryVoltage,
        CONFIG.thresholds.batteryVoltageLow,
        9.5
      );

    const alternatorRisk =
      inverseRisk(
        sample.alternatorVoltage,
        CONFIG.thresholds.alternatorVoltageLow,
        10.5
      );

    const score =
      Math.max(
        batteryRisk,
        alternatorRisk
      );

    const evidence = [];

    if (
      batteryRisk > 0
    ) {

      evidence.push(
        `Battery voltage ${sample.batteryVoltage.toFixed(1)} V`
      );

    }

    if (
      alternatorRisk > 0
    ) {

      evidence.push(
        `Alternator voltage ${sample.alternatorVoltage.toFixed(1)} V`
      );

    }

    return createFault(
      "electrical",
      "Electrical Health Issue",
      score,
      evidence,
      "electrical"
    );

  }

  function evaluate(state) {

    if (!running) {

      return latestResult;

    }

    const sample =
      extractTelemetry(
        state
      );

    pushHistory(
      sample
    );

    const faults = [

      detectMisfire(
        sample
      ),

      detectInjector(
        sample
      ),

      detectCooling(
        sample
      ),

      detectLubrication(
        sample
      ),

      detectSensorDrift(
        sample
      ),

      detectCombustion(
        sample
      ),

      detectOverheating(
        sample
      ),

      detectVibration(
        sample
      ),

      evaluateElectrical(
        sample
      )

    ];

    faults.sort(
      (a, b) =>
        b.score -
        a.score
    );

    const activeFaults =
      faults.filter(
        fault =>
          fault.active
      );

    const highestRisk =
      faults.length
        ? faults[0]
        : null;

    const overallRisk =
      highestRisk
        ? highestRisk.score
        : 0;

    latestResult = {

      timestamp:
        Date.now(),

      sampleCount:
        history.length,

      overallRisk:
        Number(
          overallRisk.toFixed(3)
        ),

      overallRiskPercent:
        Number(
          (
            overallRisk *
            100
          ).toFixed(1)
        ),

      status:
        severity(
          overallRisk
        ),

      highestRisk,

      activeFaultCount:
        activeFaults.length,

      activeFaults,

      faults,

      telemetry:
        sample

    };

    publishResult(
      latestResult
    );

    return latestResult;

  }

  function publishResult(result) {

    window.dispatchEvent(

      new CustomEvent(
        "pratirup:fault-analysis",
        {

          detail:
            result

        }
      )

    );

    if (
      typeof
      window.onPratirupFaultAnalysis
      ===
      "function"
    ) {

      try {

        window.onPratirupFaultAnalysis(
          result
        );

      }

      catch (error) {

        console.error(
          "[PRATIRUP Fault Engine] callback error:",
          error
        );

      }

    }

  }

  function connectDigitalTwin() {

    const twin =

      window.PRATIRUP_TWIN ||

      window.PRATIRUP_DIGITAL_TWIN ||

      window.PratirupDigitalTwin ||

      window.DigitalTwinCore ||

      window.digitalTwinCore;

    if (!twin) {

      console.warn(
        "[PRATIRUP Fault Engine] Digital Twin API not found. Event mode enabled."
      );

      return false;

    }

    if (
      typeof twin.getState ===
      "function"
    ) {

      console.info(
        `[PRATIRUP Fault Engine] Connected to Digital Twin Core ${twin.version || "unknown"}.`
      );

      try {

        const currentState =
          twin.getState();

        if (
          currentState &&
          currentState.observedState
        ) {

          evaluate(
            currentState
          );

        }

      }

      catch (error) {

        console.warn(
          "[PRATIRUP Fault Engine] Initial Digital Twin state read failed.",
          error
        );

      }

      return true;

    }

    const callback =
      state => {

        const now =
          performance.now();

        if (
          now -
          lastTimestamp <
          20
        ) {

          return;

        }

        lastTimestamp =
          now;

        evaluate(
          state
        );

      };

    const possibleMethods = [

      "subscribe",

      "onState",

      "addListener",

      "listen"

    ];

    for (
      const method
      of possibleMethods
    ) {

      if (
        typeof twin[method] ===
        "function"
      ) {

        try {

          twin[method](
            callback
          );

          console.info(
            `[PRATIRUP Fault Engine] Connected through ${method}().`
          );

          return true;

        }

        catch (error) {

          console.warn(
            `[PRATIRUP Fault Engine] ${method}() connection failed.`,
            error
          );

        }

      }

    }

    console.info(
      "[PRATIRUP Fault Engine] Digital Twin detected. Using twin-state event mode."
    );

    return true;

  }

  const stateEvents = [

    "pratirup:twin-state",

    "pratirup:telemetry",

    "pratirup:engine-state"

  ];

  stateEvents.forEach(

    eventName => {

      window.addEventListener(

        eventName,

        event => {

          if (
            !event.detail
          ) {

            return;

          }

          const now =
            performance.now();

          if (
            now -
            lastTimestamp <
            20
          ) {

            return;

          }

          lastTimestamp =
            now;

          evaluate(
            event.detail
          );

        }

      );

    }

  );

  window.PratirupFaultDetection = {

    evaluate,

    getLatest() {

      return latestResult;

    },

    getFault(id) {

      if (
        !latestResult ||
        !Array.isArray(
          latestResult.faults
        )
      ) {

        return null;

      }

      return (

        latestResult.faults.find(
          fault =>
            fault.id === id
        ) ||

        null

      );

    },

    getActiveFaults() {

      return latestResult

        ? [
            ...latestResult.activeFaults
          ]

        : [];

    },

    getHistory() {

      return [
        ...history
      ];

    },

    clearHistory() {

      history.length =
        0;

    },

    start() {

      running =
        true;

    },

    stop() {

      running =
        false;

    },

    isRunning() {

      return running;

    },

    config:
      CONFIG

  };

  function initialize() {

    console.info(
      "[PRATIRUP] Fault Detection Engine initializing..."
    );

    connectDigitalTwin();

    console.info(
      "[PRATIRUP] Fault Detection Engine ready."
    );

  }

  if (
    document.readyState ===
    "loading"
  ) {

    document.addEventListener(
      "DOMContentLoaded",
      initialize,
      {
        once: true
      }
    );

  }

  else {

    initialize();

  }

})();
