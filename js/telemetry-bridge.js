"use strict";

const BRIDGE_VERSION =
  "2.2.0";

const BRIDGE_CONFIG = {

  forwardSimulationToBackend:
    true,

  preventBackendLoop:
    true,

  backendMinimumIntervalMs:
    100,

  verboseBackendLogging:
    false,

  retainLatestTelemetry:
    true
};

const defaultState = {

  bridgeVersion:
    BRIDGE_VERSION,

  source:
    "simulation",

  stage:
    "digital-twin",

  simulationReady:
    false,

  backendReady:
    false,

  backendTelemetryActive:
    false,

  realEngineConnected:
    false,

  running:
    false,

  rpm:
    2200,

  exploded:
    false,

  wireframe:
    false,

  labels:
    false,

  cover:
    true,

  details:
    true,

  isolated:
    false,

  selectedComponent:
    null,

  expanded:
    false,

  activeView:
    "simulation",

  timestamp:
    Date.now()

};

const state = {

  ...defaultState

};

let externalTelemetry =
  null;

let lastBackendSendTime =
  0;

let backendSendInProgress =
  false;

const SOURCE_MODE =
  Object.freeze({
    AUTO: "auto",
    SIMULATION: "simulation",
    LIVE: "live",
    REPLAY: "replay"
  });

let sourceMode =
  SOURCE_MODE.AUTO;

let replayActive =
  false;

const telemetryStatistics = {

  received:
    0,

  simulationReceived:
    0,

  backendReceived:
    0,

  canReceived:
    0,

  replayReceived:
    0,

  arbitrationRejected:
    0,

  lastRejectedSource:
    null,

  forwardedToBackend:
    0,

  backendAccepted:
    0,

  backendFailed:
    0,

  backendLoopPrevented:
    0,

  lastTelemetryTimestamp:
    null,

  lastBackendSendTimestamp:
    null,

  lastBackendReceiveTimestamp:
    null,

  lastSource:
    null,

  latestError:
    null

};

const subscribers =
  new Set();

const telemetrySubscribers =
  new Set();

function cloneData(
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

    try {

      return structuredClone(
        value
      );

    }

    catch (_) {
    }

  }

  try {

    return JSON.parse(
      JSON.stringify(
        value
      )
    );

  }

  catch (_) {

    return value;

  }

}

function normalizeSource(
  source
) {

  const value =
    String(
      source ||
      "unknown"
    )
    .toLowerCase();

  switch (value) {

    case "simulation":

      return "simulation";

    case "backend":

      return "backend";

    case "can_fadec":

    case "can":

    case "fadec":

      return "can_fadec";

    case "replay":

      return "replay";

    case "test_rig":

    case "testrig":

      return "test_rig";

    default:

      return "unknown";

  }

}

function getState() {

  return {

    ...state

  };

}

function updateState(
  patch = {}
) {

  if (
    !patch ||
    typeof patch !==
    "object"
  ) {

    return;

  }

  Object.assign(
    state,
    patch
  );

  state.timestamp =
    Date.now();

  publishState();

}

function publishState() {

  const snapshot =
    getState();

  subscribers.forEach(
    listener => {

      try {

        listener(
          snapshot
        );

      }

      catch (
        error
      ) {

        console.error(
          "[PRATIRUP BRIDGE] Subscriber error:",
          error
        );

      }

    }
  );

  window.dispatchEvent(

    new CustomEvent(
      "pratirup:state",
      {

        detail:
          snapshot

      }
    )

  );

}

function subscribe(
  listener
) {

  if (
    typeof listener !==
    "function"
  ) {

    return () => {};

  }

  subscribers.add(
    listener
  );

  listener(
    getState()
  );

  return () => {

    subscribers.delete(
      listener
    );

  };

}

function resetState() {

  Object.assign(
    state,
    defaultState,
    {

      timestamp:
        Date.now()

    }
  );

  publishState();

}

window.addEventListener(

  "pratirup:simulation-ready",

  () => {

    updateState({

      simulationReady:
        true,

      source:
        "simulation"

    });

  }

);

window.addEventListener(

  "pratirup:run",

  event => {

    updateState({

      running:
        Boolean(
          event.detail?.value
        )

    });

  }

);

window.addEventListener(

  "pratirup:rpm",

  event => {

    const value =
      Number(
        event.detail?.value
      );

    if (
      !Number.isFinite(
        value
      )
    ) {

      return;

    }

    updateState({

      rpm:
        Math.max(
          0,
          Math.min(
            4500,
            value
          )
        )

    });

  }

);

window.addEventListener(

  "pratirup:explode",

  event => {

    updateState({

      exploded:
        Boolean(
          event.detail?.value
        )

    });

  }

);

window.addEventListener(

  "pratirup:wireframe",

  event => {

    updateState({

      wireframe:
        Boolean(
          event.detail?.value
        )

    });

  }

);

window.addEventListener(

  "pratirup:labels",

  event => {

    updateState({

      labels:
        Boolean(
          event.detail?.value
        )

    });

  }

);

window.addEventListener(

  "pratirup:cover",

  event => {

    updateState({

      cover:
        Boolean(
          event.detail?.value
        )

    });

  }

);

window.addEventListener(

  "pratirup:details",

  event => {

    updateState({

      details:
        Boolean(
          event.detail?.value
        )

    });

  }

);

window.addEventListener(

  "pratirup:navigation",

  event => {

    const view =
      String(
        event.detail?.value ||
        "simulation"
      );

    updateState({

      activeView:
        view

    });

  }

);

window.addEventListener(

  "pratirup:component-selected",

  event => {

    const name =
      event.detail?.name ||
      null;

    updateState({

      selectedComponent:
        name

    });

  }

);

window.addEventListener(

  "pratirup:component-cleared",

  () => {

    updateState({

      selectedComponent:
        null

    });

  }

);

window.addEventListener(

  "pratirup:isolation-change",

  event => {

    updateState({

      isolated:
        Boolean(
          event.detail?.value
        )

    });

  }

);

window.addEventListener(

  "pratirup:expanded",

  event => {

    updateState({

      expanded:
        Boolean(
          event.detail?.value
        )

    });

  }

);

function subscribeTelemetry(
  listener
) {

  if (
    typeof listener !==
    "function"
  ) {

    return () => {};

  }

  telemetrySubscribers.add(
    listener
  );

  if (
    externalTelemetry
  ) {

    try {

      listener(
        cloneData(
          externalTelemetry
        )
      );

    }

    catch (
      error
    ) {

      console.error(
        "[PRATIRUP BRIDGE] Telemetry subscriber error:",
        error
      );

    }

  }

  return () => {

    telemetrySubscribers.delete(
      listener
    );

  };

}

function publishTelemetrySubscribers(
  telemetry
) {

  telemetrySubscribers.forEach(
    listener => {

      try {

        listener(
          cloneData(
            telemetry
          )
        );

      }

      catch (
        error
      ) {

        console.error(
          "[PRATIRUP BRIDGE] Telemetry subscriber error:",
          error
        );

      }

    }
  );

}

function registerTelemetrySource(
  source
) {

  telemetryStatistics.received++;

  telemetryStatistics.lastSource =
    source;

  telemetryStatistics.lastTelemetryTimestamp =
    Date.now();

  switch (
    source
  ) {

    case "simulation":

      telemetryStatistics.simulationReceived++;

      break;

    case "backend":

      telemetryStatistics.backendReceived++;

      telemetryStatistics.lastBackendReceiveTimestamp =
        Date.now();

      break;

    case "can_fadec":

      telemetryStatistics.canReceived++;

      break;

    case "replay":

      telemetryStatistics.replayReceived++;

      break;

  }

}

function normalizeSourceMode(
  mode
) {

  const value =
    String(mode || "auto")
      .toLowerCase();

  if (
    value === SOURCE_MODE.SIMULATION ||
    value === SOURCE_MODE.LIVE ||
    value === SOURCE_MODE.REPLAY
  ) {

    return value;

  }

  return SOURCE_MODE.AUTO;

}

function isSourceAllowed(
  source,
  telemetry = null
) {

  const normalized =
    normalizeSource(source);

  if (
    sourceMode === SOURCE_MODE.AUTO
  ) {

    return true;

  }

  if (
    sourceMode === SOURCE_MODE.REPLAY
  ) {

    return normalized === "replay";

  }

  if (
    sourceMode === SOURCE_MODE.LIVE
  ) {

    return (
      normalized === "can_fadec" ||
      normalized === "backend"
    );

  }

  if (
    sourceMode === SOURCE_MODE.SIMULATION
  ) {

    if (
      normalized === "simulation"
    ) {

      return true;

    }

    if (
      normalized === "backend"
    ) {

      const original =
        String(
          telemetry?.meta?.original_source ||
          telemetry?.meta?.upstream_source ||
          ""
        )
        .toLowerCase();

      return (
        original === "simulation" ||
        original === "sim"
      );

    }

  }

  return false;

}

function setSourceMode(
  mode
) {

  sourceMode =
    normalizeSourceMode(mode);

  replayActive =
    sourceMode ===
    SOURCE_MODE.REPLAY;

  window.dispatchEvent(

    new CustomEvent(
      "pratirup:telemetry-source-mode",
      {

        detail: {

          mode:
            sourceMode,

          replayActive,

          bridgeVersion:
            BRIDGE_VERSION,

          timestamp:
            new Date()
              .toISOString()

        }

      }
    )

  );

  return sourceMode;

}

function getSourceMode() {

  return sourceMode;

}

function getSourceArbitrationStatus() {

  return {

    mode:
      sourceMode,

    replayActive,

    rejected:
      telemetryStatistics
        .arbitrationRejected,

    lastRejectedSource:
      telemetryStatistics
        .lastRejectedSource

  };

}

function prepareTelemetry(
  telemetry,
  options = {}
) {

  if (
    !telemetry ||
    typeof telemetry !==
    "object"
  ) {

    return null;

  }

  const output =
    cloneData(
      telemetry
    );

  output.meta =
    output.meta ||
    {};

  const source =
    normalizeSource(

      options.source ||

      output.meta.source ||

      state.source ||

      "unknown"

    );

  output.meta.source =
    source;

  if (
    !output.meta.timestamp
  ) {

    output.meta.timestamp =
      new Date()
        .toISOString();

  }

  output.meta.bridgeVersion =
    BRIDGE_VERSION;

  output.meta.bridgeReceivedAt =
    new Date()
      .toISOString();

  return output;

}

function shouldForwardToBackend(
  telemetry,
  options = {}
) {

  if (
    options.forwardToBackend ===
    false
  ) {

    return false;

  }

  if (
    BRIDGE_CONFIG
      .forwardSimulationToBackend !==
    true
  ) {

    return false;

  }

  const source =
    normalizeSource(
      telemetry
        ?.meta
        ?.source
    );

  if (
    BRIDGE_CONFIG.preventBackendLoop &&
    (
      source === "backend" ||
      source === "can_fadec"
    )
  ) {

    telemetryStatistics
      .backendLoopPrevented++;

    return false;

  }

  if (
    source === "replay"
  ) {

    return false;

  }

  return (
    source === "simulation" ||
    source === "test_rig" ||
    source === "unknown"
  );

}

async function forwardTelemetryToBackend(
  telemetry
) {

  if (
    !window.PratirupBackend ||
    typeof window.PratirupBackend
      .sendTelemetry !==
    "function"
  ) {

    return false;

  }

  const now =
    performance.now();

  if (
    now -
    lastBackendSendTime <
    BRIDGE_CONFIG
      .backendMinimumIntervalMs
  ) {

    return false;

  }

  if (
    backendSendInProgress
  ) {

    return false;

  }

  lastBackendSendTime =
    now;

  backendSendInProgress =
    true;

  telemetryStatistics
    .forwardedToBackend++;

  telemetryStatistics
    .lastBackendSendTimestamp =
    Date.now();

  try {

    const result =

      await window
        .PratirupBackend
        .sendTelemetry(
          cloneData(
            telemetry
          )
        );

    if (
      result?.ok
    ) {

      telemetryStatistics
        .backendAccepted++;

      telemetryStatistics
        .latestError =
        null;

      if (
        BRIDGE_CONFIG
          .verboseBackendLogging
      ) {

        console.info(
          "[PRATIRUP BRIDGE] Telemetry accepted by backend."
        );

      }

      return true;

    }

    telemetryStatistics
      .backendFailed++;

    telemetryStatistics
      .latestError =

      result?.error ||
      "Backend telemetry request failed.";

    return false;

  }

  catch (
    error
  ) {

    telemetryStatistics
      .backendFailed++;

    telemetryStatistics
      .latestError =
      error?.message ||
      String(error);

    return false;

  }

  finally {

    backendSendInProgress =
      false;

  }

}

function updateTelemetry(
  telemetry,
  options = {}
) {

  const prepared =
    prepareTelemetry(
      telemetry,
      options
    );

  if (
    !prepared
  ) {

    return false;

  }

  const source =
    normalizeSource(
      prepared
        .meta
        .source
    );

  registerTelemetrySource(
    source
  );

  if (
    !isSourceAllowed(
      source,
      prepared
    )
  ) {

    telemetryStatistics
      .arbitrationRejected++;

    telemetryStatistics
      .lastRejectedSource =
      source;

    window.dispatchEvent(

      new CustomEvent(
        "pratirup:telemetry-arbitration-rejected",
        {

          detail: {

            source,

            mode:
              sourceMode,

            sequence:
              prepared?.meta?.sequence ??
              null,

            timestamp:
              new Date()
                .toISOString()

          }

        }
      )

    );

    return false;

  }

  if (
    BRIDGE_CONFIG
      .retainLatestTelemetry
  ) {

    externalTelemetry =
      prepared;

  }

  state.source =
    source;

  state.backendTelemetryActive =
    source === "backend";

  state.realEngineConnected =
    source === "can_fadec";

  state.timestamp =
    Date.now();

  publishTelemetrySubscribers(
    prepared
  );

  window.dispatchEvent(

    new CustomEvent(
      "pratirup:telemetry",
      {

        detail:
          cloneData(
            prepared
          )

      }
    )

  );

  window.dispatchEvent(

    new CustomEvent(
      `pratirup:telemetry:${source}`,
      {

        detail:
          cloneData(
            prepared
          )

      }
    )

  );

  if (
    shouldForwardToBackend(
      prepared,
      options
    )
  ) {

    forwardTelemetryToBackend(
      prepared
    );

  }

  publishState();

  return true;

}

function getTelemetry() {

  return externalTelemetry
    ? cloneData(
        externalTelemetry
      )
    : null;

}

function clearTelemetry() {

  externalTelemetry =
    null;

  state.backendTelemetryActive =
    false;

  state.realEngineConnected =
    false;

  window.dispatchEvent(

    new CustomEvent(
      "pratirup:telemetry-cleared"
    )

  );

}

function getTelemetryStatistics() {

  return {

    ...telemetryStatistics

  };

}

function resetTelemetryStatistics() {

  telemetryStatistics.received =
    0;

  telemetryStatistics.simulationReceived =
    0;

  telemetryStatistics.backendReceived =
    0;

  telemetryStatistics.canReceived =
    0;

  telemetryStatistics.replayReceived =
    0;

  telemetryStatistics.arbitrationRejected =
    0;

  telemetryStatistics.lastRejectedSource =
    null;

  telemetryStatistics.forwardedToBackend =
    0;

  telemetryStatistics.backendAccepted =
    0;

  telemetryStatistics.backendFailed =
    0;

  telemetryStatistics.backendLoopPrevented =
    0;

  telemetryStatistics.lastTelemetryTimestamp =
    null;

  telemetryStatistics.lastBackendSendTimestamp =
    null;

  telemetryStatistics.lastBackendReceiveTimestamp =
    null;

  telemetryStatistics.lastSource =
    null;

  telemetryStatistics.latestError =
    null;

}

window.addEventListener(

  "pratirup:backend-state",

  event => {

    const backendState =
      event.detail ||
      {};

    const online =
      backendState.backend ===
      "ONLINE";

    updateState({

      backendReady:
        online

    });

  }

);

window.addEventListener(

  "pratirup:backend-telemetry",

  event => {

    if (
      !event.detail
    ) {

      return;

    }

    updateTelemetry(

      event.detail,

      {

        source:
          "backend",

        forwardToBackend:
          false

      }

    );

  }

);

window.addEventListener(

  "pratirup:can-telemetry",

  event => {

    if (
      !event.detail
    ) {

      return;

    }

    updateTelemetry(

      event.detail,

      {

        source:
          "can_fadec",

        forwardToBackend:
          false

      }

    );

  }

);

window.addEventListener(

  "pratirup:replay-telemetry",

  event => {

    if (
      !event.detail
    ) {

      return;

    }

    updateTelemetry(

      event.detail,

      {

        source:
          "replay",

        forwardToBackend:
          false

      }

    );

    window.dispatchEvent(

      new CustomEvent(
        "pratirup:telemetry-replay-frame",
        {

          detail:
            prepareTelemetry(
              event.detail,
              {

                source:
                  "replay"

              }
            )

        }
      )

    );

  }

);

function setSource(
  source
) {

  const normalized =
    normalizeSource(
      source
    );

  updateState({

    source:
      normalized,

    backendTelemetryActive:
      normalized ===
      "backend",

    realEngineConnected:
      normalized ===
      "can_fadec"

  });

  return normalized;

}

function configure(
  options = {}
) {

  if (
    !options ||
    typeof options !==
    "object"
  ) {

    return {

      ...BRIDGE_CONFIG

    };

  }

  Object.keys(
    BRIDGE_CONFIG
  )
  .forEach(
    key => {

      if (
        options[key] !==
        undefined
      ) {

        BRIDGE_CONFIG[key] =
          options[key];

      }

    }
  );

  return {

    ...BRIDGE_CONFIG

  };

}

window.PRATIRUP_BRIDGE = {

  version:
    BRIDGE_VERSION,

  getState,

  updateState,

  resetState,

  subscribe,

  updateTelemetry,

  getTelemetry,

  clearTelemetry,

  subscribeTelemetry,

  forwardTelemetryToBackend,

  setSource,

  setSourceMode,

  getSourceMode,

  getSourceArbitrationStatus,

  SOURCE_MODE,

  getTelemetryStatistics,

  resetTelemetryStatistics,

  configure,

  config:
    BRIDGE_CONFIG

};

publishState();

console.log(
  `[PRATIRUP] Unified telemetry bridge ${BRIDGE_VERSION} ready.`
);

console.log(
  "[PRATIRUP] Visual state + Digital Twin telemetry routing enabled."
);
