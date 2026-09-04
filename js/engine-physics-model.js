"use strict";

const ENGINE_PHYSICS_MODEL_VERSION =
  "0.1.0";

const ENGINE_PHYSICS_MODEL_NAME =
  "PRATIRUP Baseline Aero-Piston Model";

const ENGINE = {

  cylinders:
    4,

  displacementL:
    5.2,

  compressionRatio:
    8.5,

  ratedPowerKw:
    134.2,

  ratedRpm:
    2700,

  maximumRpm:
    4500,

  volumetricEfficiency:
    0.86,

  mechanicalEfficiency:
    0.88,

  fuelLhvJPerKg:
    43e6,

  stoichiometricAfr:
    14.7,

  seaLevelPressurePa:
    101325,

  seaLevelTemperatureK:
    288.15,

  seaLevelDensityKgM3:
    1.225

};

const AIR = {

  gasConstant:
    287.05,

  gamma:
    1.4,

  gravity:
    9.80665,

  lapseRate:
    0.0065

};

function clamp(
  value,
  minimum,
  maximum
) {

  return Math.min(
    maximum,
    Math.max(
      minimum,
      value
    )
  );

}

function finiteOr(
  value,
  fallback
) {

  const number =
    Number(
      value
    );

  return Number.isFinite(
    number
  )
    ? number
    : fallback;

}

function calculateAtmosphere(
  altitudeM,
  ambientTemperatureC = null
) {

  const altitude =
    clamp(
      finiteOr(
        altitudeM,
        0
      ),
      0,
      11000
    );

  const standardTemperatureK =

    ENGINE
      .seaLevelTemperatureK -

    AIR.lapseRate *
    altitude;

  const pressurePa =

    ENGINE
      .seaLevelPressurePa *

    Math.pow(

      standardTemperatureK /
      ENGINE
        .seaLevelTemperatureK,

      AIR.gravity /
      (
        AIR.gasConstant *
        AIR.lapseRate
      )

    );

  const actualTemperatureK =

    ambientTemperatureC !==
    null

      ? finiteOr(
          ambientTemperatureC,
          15
        ) +
        273.15

      : standardTemperatureK;

  const densityKgM3 =

    pressurePa /
    (
      AIR.gasConstant *
      actualTemperatureK
    );

  return {

    altitudeM:
      altitude,

    temperatureK:
      actualTemperatureK,

    temperatureC:
      actualTemperatureK -
      273.15,

    pressurePa,

    densityKgM3,

    densityRatio:

      densityKgM3 /
      ENGINE
        .seaLevelDensityKgM3

  };

}

function calculateRpmFactor(
  rpm
) {

  return clamp(

    rpm /
    ENGINE.ratedRpm,

    0,

    1.35

  );

}

function calculateVolumetricEfficiency(
  rpm
) {

  const ratio =
    clamp(
      rpm /
      ENGINE.ratedRpm,
      0,
      1.5
    );

  const shape =

    1 -

    0.18 *
    Math.pow(
      ratio -
      0.85,
      2
    );

  return clamp(

    ENGINE
      .volumetricEfficiency *
    shape,

    0.65,

    0.92

  );

}

function calculateManifoldPressure(
  ambientPressurePa,
  throttlePercent
) {

  const throttle =
    clamp(
      throttlePercent /
      100,
      0,
      1
    );

  const manifoldRatio =

    0.28 +
    0.72 *
    throttle;

  return ambientPressurePa *
    manifoldRatio;

}

function calculateAirMassFlow(
  rpm,
  manifoldPressurePa,
  intakeTemperatureK,
  volumetricEfficiency
) {

  const displacementM3 =

    ENGINE.displacementL /
    1000;

  const intakeDensity =

    manifoldPressurePa /
    (
      AIR.gasConstant *
      intakeTemperatureK
    );

  const intakeCyclesPerSecond =

    rpm /
    120;

  const volumetricFlowM3PerSecond =

    displacementM3 *
    intakeCyclesPerSecond *
    volumetricEfficiency;

  const massFlowKgPerSecond =

    volumetricFlowM3PerSecond *
    intakeDensity;

  return {

    intakeDensity,

    volumetricFlowM3PerSecond,

    massFlowKgPerSecond

  };

}

function calculateAfr(
  throttlePercent,
  loadPercent
) {

  const throttle =
    clamp(
      throttlePercent /
      100,
      0,
      1
    );

  const load =
    clamp(
      loadPercent /
      100,
      0,
      1
    );

  const demand =

    clamp(
      throttle *
      0.6 +
      load *
      0.4,
      0,
      1
    );

  return THREELESS_LERP(
    16.5,
    12.8,
    demand
  );

}

function THREELESS_LERP(
  a,
  b,
  t
) {

  return a +
    (
      b -
      a
    ) *
    t;

}

function calculateFuelFlow(
  airMassFlowKgPerSecond,
  afr
) {

  if (
    afr <= 0
  ) {

    return 0;

  }

  return airMassFlowKgPerSecond /
    afr;

}

function calculateAvailablePower(
  rpm,
  throttlePercent,
  loadPercent,
  densityRatio
) {

  const rpmFactor =
    calculateRpmFactor(
      rpm
    );

  const throttle =
    clamp(
      throttlePercent /
      100,
      0,
      1
    );

  const load =
    clamp(
      loadPercent /
      100,
      0,
      1
    );

  const environmentalFactor =

    clamp(
      densityRatio,
      0.35,
      1.05
    );

  const rpmShape =

    clamp(
      1 -
      Math.pow(
        rpmFactor -
        0.90,
        2
      ) *
      0.55,
      0.25,
      1
    );

  const demandFactor =

    throttle *
    (
      0.55 +
      load *
      0.45
    );

  return (

    ENGINE.ratedPowerKw *

    environmentalFactor *

    rpmShape *

    demandFactor

  );

}

function calculateTorque(
  powerKw,
  rpm
) {

  if (
    rpm <= 1
  ) {

    return 0;

  }

  const omega =

    rpm *
    2 *
    Math.PI /
    60;

  return (

    powerKw *
    1000

  ) /
  omega;

}

function calculateBmep(
  torqueNm
) {

  const displacementM3 =

    ENGINE.displacementL /
    1000;

  if (
    displacementM3 <= 0
  ) {

    return 0;

  }

  return (

    4 *
    Math.PI *
    torqueNm

  ) /
  displacementM3;

}

function calculateIntakeTemperature(
  ambientTemperatureK,
  rpm,
  throttlePercent
) {

  const rpmFactor =
    calculateRpmFactor(
      rpm
    );

  const throttle =
    throttlePercent /
    100;

  const heatSoakK =

    4 +
    rpmFactor *
    4 +
    throttle *
    5;

  return ambientTemperatureK +
    heatSoakK;

}

function calculateCht(
  ambientTemperatureC,
  rpm,
  throttlePercent,
  loadPercent,
  densityRatio
) {

  const rpmFactor =
    calculateRpmFactor(
      rpm
    );

  const throttle =
    throttlePercent /
    100;

  const load =
    loadPercent /
    100;

  const altitudeCoolingPenalty =

    (
      1 -
      clamp(
        densityRatio,
        0.4,
        1
      )
    ) *
    28;

  const temperature =

    ambientTemperatureC +

    85 +

    throttle *
    45 +

    load *
    35 +

    rpmFactor *
    18 +

    altitudeCoolingPenalty;

  return clamp(
    temperature,
    ambientTemperatureC,
    260
  );

}

function calculateEgt(
  rpm,
  throttlePercent,
  loadPercent,
  afr
) {

  const rpmFactor =
    calculateRpmFactor(
      rpm
    );

  const throttle =
    throttlePercent /
    100;

  const load =
    loadPercent /
    100;

  const mixtureDistance =

    Math.abs(
      afr -
      ENGINE
        .stoichiometricAfr
    );

  const mixtureEffect =

    clamp(
      1 -
      mixtureDistance /
      8,
      0.45,
      1
    );

  const egt =

    380 +

    throttle *
    230 +

    load *
    120 +

    rpmFactor *
    60 +

    mixtureEffect *
    90;

  return clamp(
    egt,
    250,
    950
  );

}

function calculateOilTemperature(
  ambientTemperatureC,
  rpm,
  loadPercent
) {

  const rpmFactor =
    calculateRpmFactor(
      rpm
    );

  const load =
    loadPercent /
    100;

  return clamp(

    ambientTemperatureC +

    50 +

    load *
    35 +

    rpmFactor *
    12,

    ambientTemperatureC,

    150

  );

}

function calculateOilPressure(
  rpm,
  oilTemperatureC
) {

  if (
    rpm <= 0
  ) {

    return 0;

  }

  const rpmFactor =
    clamp(
      rpm /
      ENGINE.ratedRpm,
      0,
      1.5
    );

  const temperatureCorrection =

    clamp(
      1 -
      Math.max(
        0,
        oilTemperatureC -
        95
      ) *
      0.003,
      0.65,
      1
    );

  const pressureKPa =

    (
      120 +
      rpmFactor *
      330
    ) *
    temperatureCorrection;

  return clamp(
    pressureKPa,
    0,
    550
  );

}

function createCylinderTemperatures(
  baseTemperature,
  spread
) {

  return {

    cylinder1C:
      baseTemperature -
      spread,

    cylinder2C:
      baseTemperature +
      spread *
      0.35,

    cylinder3C:
      baseTemperature +
      spread,

    cylinder4C:
      baseTemperature -
      spread *
      0.25

  };

}

function calculateModelConfidence(
  input
) {

  let confidence =
    0.60;

  if (
    input.engine.rpm !==
    null
  ) {

    confidence +=
      0.05;

  }

  if (
    input.engine.throttlePercent !==
    null
  ) {

    confidence +=
      0.05;

  }

  if (
    input.environment.altitudeM !==
    null
  ) {

    confidence +=
      0.05;

  }

  if (
    input.environment.ambientTemperatureC !==
    null
  ) {

    confidence +=
      0.05;

  }

  return clamp(
    confidence,
    0,
    0.75
  );

}

function enginePhysicsModel(
  input,
  createOutput
) {

  const output =
    createOutput();

  const rpm =
    clamp(
      finiteOr(
        input.engine.rpm,
        0
      ),
      0,
      ENGINE.maximumRpm
    );

  const throttlePercent =
    clamp(
      finiteOr(
        input.engine.throttlePercent,
        rpm > 0
          ? 65
          : 0
      ),
      0,
      100
    );

  const loadPercent =
    clamp(
      finiteOr(
        input.engine.loadPercent,
        throttlePercent
      ),
      0,
      100
    );

  const altitudeM =
    finiteOr(
      input.environment.altitudeM,
      0
    );

  const suppliedAmbientTemperature =

    input.environment
      .ambientTemperatureC;

  const atmosphere =
    calculateAtmosphere(
      altitudeM,
      suppliedAmbientTemperature
    );

  const intakeTemperatureK =
    calculateIntakeTemperature(
      atmosphere.temperatureK,
      rpm,
      throttlePercent
    );

  const manifoldPressurePa =
    calculateManifoldPressure(
      atmosphere.pressurePa,
      throttlePercent
    );

  const volumetricEfficiency =
    calculateVolumetricEfficiency(
      rpm
    );

  const airFlow =
    calculateAirMassFlow(
      rpm,
      manifoldPressurePa,
      intakeTemperatureK,
      volumetricEfficiency
    );

  const afr =
    calculateAfr(
      throttlePercent,
      loadPercent
    );

  const fuelFlowKgPerSecond =
    calculateFuelFlow(
      airFlow.massFlowKgPerSecond,
      afr
    );

  const powerKw =
    calculateAvailablePower(
      rpm,
      throttlePercent,
      loadPercent,
      atmosphere.densityRatio
    );

  const torqueNm =
    calculateTorque(
      powerKw,
      rpm
    );

  const bmepPa =
    calculateBmep(
      torqueNm
    );

  const chtBase =
    calculateCht(
      atmosphere.temperatureC,
      rpm,
      throttlePercent,
      loadPercent,
      atmosphere.densityRatio
    );

  const egtBase =
    calculateEgt(
      rpm,
      throttlePercent,
      loadPercent,
      afr
    );

  const cht =
    createCylinderTemperatures(
      chtBase,
      3.5
    );

  const egt =
    createCylinderTemperatures(
      egtBase,
      7
    );

  const oilTemperatureC =
    calculateOilTemperature(
      atmosphere.temperatureC,
      rpm,
      loadPercent
    );

  const oilPressureKPa =
    calculateOilPressure(
      rpm,
      oilTemperatureC
    );

  output.engine.expectedRpm =
    rpm;

  output.engine.expectedTorqueNm =
    torqueNm;

  output.engine.expectedPowerKw =
    powerKw;

  output.engine.expectedLoadPercent =
    loadPercent;

  output.engine.expectedManifoldPressurePa =
    manifoldPressurePa;

  output.engine.expectedAirFlowKgPerSecond =
    airFlow.massFlowKgPerSecond;

  Object.assign(
    output.cht,
    cht
  );

  Object.assign(
    output.egt,
    egt
  );

  output.oil.temperatureC =
    oilTemperatureC;

  output.oil.pressureKPa =
    oilPressureKPa;

  output.fuel.flowKgPerSecond =
    fuelFlowKgPerSecond;

  output.fuel.airFuelRatio =
    afr;

  output.fuel.pressureKPa =
    null;

  output.combustion.meanEffectivePressurePa =
    bmepPa;

  output.combustion.peakCylinderPressurePa =
    null;

  const fuelEnergyRateKw =

    fuelFlowKgPerSecond *
    ENGINE.fuelLhvJPerKg /
    1000;

  output.combustion.combustionEfficiency =

    fuelEnergyRateKw >
    0

      ? clamp(
          powerKw /
          fuelEnergyRateKw,
          0,
          0.45
        )

      : 0;

  const confidence =
    calculateModelConfidence(
      input
    );

  output.confidence.overall =
    confidence;

  output.confidence.engine =
    confidence;

  output.confidence.thermal =
    confidence *
    0.85;

  output.confidence.lubrication =
    confidence *
    0.75;

  output.confidence.fuel =
    confidence *
    0.75;

  output.environment = {

    altitudeM:
      atmosphere.altitudeM,

    ambientTemperatureC:
      atmosphere.temperatureC,

    ambientPressurePa:
      atmosphere.pressurePa,

    airDensityKgM3:
      atmosphere.densityKgM3,

    densityRatio:
      atmosphere.densityRatio,

    intakeTemperatureC:
      intakeTemperatureK -
      273.15,

    volumetricEfficiency

  };

  return output;

}

function registerEnginePhysicsModel() {

  const physics =
    window.PRATIRUP_PHYSICS;

  if (
    !physics
  ) {

    console.error(
      "[PRATIRUP ENGINE MODEL] Physics interface unavailable."
    );

    return false;

  }

  return physics.register({

    name:
      ENGINE_PHYSICS_MODEL_NAME,

    version:
      ENGINE_PHYSICS_MODEL_VERSION,

    model:
      enginePhysicsModel

  });

}

window.PRATIRUP_ENGINE_MODEL = {

  version:
    ENGINE_PHYSICS_MODEL_VERSION,

  name:
    ENGINE_PHYSICS_MODEL_NAME,

  constants:
    ENGINE,

  calculateAtmosphere,

  calculateAirMassFlow,

  calculateAvailablePower,

  calculateTorque,

  calculateBmep,

  calculateAfr,

  calculateCht,

  calculateEgt,

  calculateOilTemperature,

  calculateOilPressure,

  run:
    enginePhysicsModel

};

registerEnginePhysicsModel();

console.log(
  `[PRATIRUP] Engine Physics Model ${ENGINE_PHYSICS_MODEL_VERSION} loaded.`
);
