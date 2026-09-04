"use strict";

const runEngineButton =
  document.getElementById("runEngineButton");

const explodeButton =
  document.getElementById("explodeButton");

const wireframeButton =
  document.getElementById("wireframeButton");

const labelsButton =
  document.getElementById("labelsButton");

const coverButton =
  document.getElementById("coverButton");

const detailsButton =
  document.getElementById("detailsButton");

const resetViewButton =
  document.getElementById("resetViewButton");

const expandViewButton =
  document.getElementById("expandViewButton");

const rpmSlider =
  document.getElementById("rpmSlider");

const rpmDisplay =
  document.getElementById("rpmDisplay");

const engineStateText =
  document.getElementById("engineStateText");

const animationStateText =
  document.getElementById("animationStateText");

const coverStateText =
  document.getElementById("coverStateText");

const detailStateText =
  document.getElementById("detailStateText");

const inspectionModeText =
  document.getElementById("inspectionModeText");

const explodedStateText =
  document.getElementById("explodedStateText");

const wireframeStateText =
  document.getElementById("wireframeStateText");

const labelStateText =
  document.getElementById("labelStateText");

const currentViewText =
  document.getElementById("currentViewText");

const dashboardState = {

  running: false,

  rpm: 2200,

  exploded: false,

  wireframe: false,

  labels: false,

  cover: true,

  details: true,

  expanded: false

};

function sendSimulationCommand(
  command,
  value = null
) {

  window.dispatchEvent(

    new CustomEvent(
      `pratirup:${command}`,
      {
        detail: {
          value
        }
      }
    )

  );

}

function setButtonActive(
  button,
  active
) {

  if (!button) {
    return;
  }

  button.classList.toggle(
    "active",
    active
  );

}

function updateInspectionMode() {

  const inspectionActive =
    dashboardState.exploded ||
    dashboardState.wireframe ||
    dashboardState.labels;

  if (inspectionModeText) {

    inspectionModeText.textContent =
      inspectionActive
        ? "ENGINEERING"
        : "STANDARD";

  }

}

function updateCurrentView() {

  if (!currentViewText) {
    return;
  }

  if (dashboardState.exploded) {

    currentViewText.textContent =
      "EXPLODED";

    return;

  }

  if (dashboardState.wireframe) {

    currentViewText.textContent =
      "WIREFRAME";

    return;

  }

  currentViewText.textContent =
    "ASSEMBLED";

}

function toggleEngine() {

  dashboardState.running =
    !dashboardState.running;

  if (dashboardState.running) {

    runEngineButton.innerHTML =
      `
        <span class="button-icon">
          ■
        </span>
        STOP
      `;

    engineStateText.textContent =
      "RUNNING";

    animationStateText.textContent =
      "ACTIVE";

  }

  else {

    runEngineButton.innerHTML =
      `
        <span class="button-icon">
          ▶
        </span>
        RUN
      `;

    engineStateText.textContent =
      "READY";

    animationStateText.textContent =
      "STOPPED";

  }

  sendSimulationCommand(
    "run",
    dashboardState.running
  );

}

function updateRPM() {

  dashboardState.rpm =
    Number(
      rpmSlider.value
    );

  rpmDisplay.textContent =
    dashboardState.rpm;

  sendSimulationCommand(
    "rpm",
    dashboardState.rpm
  );

}

function toggleExplodedView() {

  dashboardState.exploded =
    !dashboardState.exploded;

  setButtonActive(
    explodeButton,
    dashboardState.exploded
  );

  explodedStateText.textContent =
    dashboardState.exploded
      ? "ON"
      : "OFF";

  updateInspectionMode();

  updateCurrentView();

  sendSimulationCommand(
    "explode",
    dashboardState.exploded
  );

}

function toggleWireframe() {

  dashboardState.wireframe =
    !dashboardState.wireframe;

  setButtonActive(
    wireframeButton,
    dashboardState.wireframe
  );

  wireframeStateText.textContent =
    dashboardState.wireframe
      ? "ON"
      : "OFF";

  updateInspectionMode();

  updateCurrentView();

  sendSimulationCommand(
    "wireframe",
    dashboardState.wireframe
  );

}

function toggleLabels() {

  dashboardState.labels =
    !dashboardState.labels;

  setButtonActive(
    labelsButton,
    dashboardState.labels
  );

  labelStateText.textContent =
    dashboardState.labels
      ? "ON"
      : "OFF";

  updateInspectionMode();

  sendSimulationCommand(
    "labels",
    dashboardState.labels
  );

}

function toggleCover() {

  dashboardState.cover =
    !dashboardState.cover;

  setButtonActive(
    coverButton,
    dashboardState.cover
  );

  coverStateText.textContent =
    dashboardState.cover
      ? "VISIBLE"
      : "HIDDEN";

  sendSimulationCommand(
    "cover",
    dashboardState.cover
  );

}

function toggleDetails() {

  dashboardState.details =
    !dashboardState.details;

  setButtonActive(
    detailsButton,
    dashboardState.details
  );

  detailStateText.textContent =
    dashboardState.details
      ? "VISIBLE"
      : "HIDDEN";

  sendSimulationCommand(
    "details",
    dashboardState.details
  );

}

function resetCamera() {

  sendSimulationCommand(
    "reset-camera"
  );

  if (resetViewButton) {

    resetViewButton.classList.add(
      "active"
    );

    setTimeout(
      () => {

        resetViewButton.classList.remove(
          "active"
        );

      },
      250
    );

  }

}

function toggleExpandedView() {

  dashboardState.expanded =
    !dashboardState.expanded;

  document.body.classList.toggle(
    "simulation-expanded",
    dashboardState.expanded
  );

  expandViewButton.textContent =
    dashboardState.expanded
      ? "EXIT FULL VIEW"
      : "EXPAND";

  setButtonActive(
    expandViewButton,
    dashboardState.expanded
  );

  requestAnimationFrame(
    () => {

      requestAnimationFrame(
        () => {

          sendSimulationCommand(
            "resize"
          );

        }
      );

    }
  );

}

function initializeNavigation() {

  const navItems =
    document.querySelectorAll(
      ".nav-item"
    );

  navItems.forEach(
    button => {

      button.addEventListener(
        "click",
        () => {

          navItems.forEach(
            item => {

              item.classList.remove(
                "active"
              );

            }
          );

          button.classList.add(
            "active"
          );

          const view =
            button.dataset.view;

          sendSimulationCommand(
            "navigation",
            view
          );

        }
      );

    }
  );

}

function initializeKeyboardControls() {

  window.addEventListener(
    "keydown",
    event => {

      const tag =
        document.activeElement
          ?.tagName
          ?.toLowerCase();

      if (
        tag === "input" ||
        tag === "textarea"
      ) {

        return;

      }

      switch (
        event.key.toLowerCase()
      ) {

        case " ":

          event.preventDefault();

          toggleEngine();

          break;

        case "e":

          toggleExplodedView();

          break;

        case "w":

          toggleWireframe();

          break;

        case "l":

          toggleLabels();

          break;

        case "c":

          toggleCover();

          break;

        case "d":

          toggleDetails();

          break;

        case "r":

          resetCamera();

          break;

        case "f":

          toggleExpandedView();

          break;

        case "escape":

          if (
            dashboardState.expanded
          ) {

            toggleExpandedView();

          }

          break;

      }

    }
  );

}

function initializeButtons() {

  runEngineButton?.addEventListener(
    "click",
    toggleEngine
  );

  explodeButton?.addEventListener(
    "click",
    toggleExplodedView
  );

  wireframeButton?.addEventListener(
    "click",
    toggleWireframe
  );

  labelsButton?.addEventListener(
    "click",
    toggleLabels
  );

  coverButton?.addEventListener(
    "click",
    toggleCover
  );

  detailsButton?.addEventListener(
    "click",
    toggleDetails
  );

  resetViewButton?.addEventListener(
    "click",
    resetCamera
  );

  expandViewButton?.addEventListener(
    "click",
    toggleExpandedView
  );

  rpmSlider?.addEventListener(
    "input",
    updateRPM
  );

}

function initializeResizeHandler() {

  let resizeTimer = null;

  window.addEventListener(
    "resize",
    () => {

      clearTimeout(
        resizeTimer
      );

      resizeTimer =
        setTimeout(
          () => {

            sendSimulationCommand(
              "resize"
            );

          },
          100
        );

    }
  );

}

function initializeDashboardState() {

  if (rpmSlider) {

    rpmSlider.value =
      dashboardState.rpm;

  }

  if (rpmDisplay) {

    rpmDisplay.textContent =
      dashboardState.rpm;

  }

  if (engineStateText) {

    engineStateText.textContent =
      "READY";

  }

  if (animationStateText) {

    animationStateText.textContent =
      "STOPPED";

  }

  if (coverStateText) {

    coverStateText.textContent =
      "VISIBLE";

  }

  setButtonActive(
    coverButton,
    true
  );

  if (detailStateText) {

    detailStateText.textContent =
      "VISIBLE";

  }

  setButtonActive(
    detailsButton,
    true
  );

  if (explodedStateText) {

    explodedStateText.textContent =
      "OFF";

  }

  if (wireframeStateText) {

    wireframeStateText.textContent =
      "OFF";

  }

  if (labelStateText) {

    labelStateText.textContent =
      "OFF";

  }

  if (inspectionModeText) {

    inspectionModeText.textContent =
      "STANDARD";

  }

  if (currentViewText) {

    currentViewText.textContent =
      "ASSEMBLED";

  }

}

window.addEventListener(
  "pratirup:simulation-ready",
  () => {

    console.log(
      "[PRATIRUP] Three.js simulation ready."
    );

    sendSimulationCommand(
      "rpm",
      dashboardState.rpm
    );

    sendSimulationCommand(
      "run",
      dashboardState.running
    );

    sendSimulationCommand(
      "cover",
      dashboardState.cover
    );

    sendSimulationCommand(
      "details",
      dashboardState.details
    );

    sendSimulationCommand(
      "explode",
      dashboardState.exploded
    );

    sendSimulationCommand(
      "wireframe",
      dashboardState.wireframe
    );

    sendSimulationCommand(
      "labels",
      dashboardState.labels
    );

  }
);

window.addEventListener(
  "pratirup:simulation-error",
  event => {

    console.error(
      "[PRATIRUP] Simulation error:",
      event.detail
    );

    if (engineStateText) {

      engineStateText.textContent =
        "MODEL ERROR";

    }

  }
);

function initializeDashboard() {

  initializeDashboardState();

  initializeButtons();

  initializeNavigation();

  initializeKeyboardControls();

  initializeResizeHandler();

  console.log(
    "[PRATIRUP] Dashboard initialized."
  );

}

if (
  document.readyState ===
  "loading"
) {

  document.addEventListener(
    "DOMContentLoaded",
    initializeDashboard
  );

}

else {

  initializeDashboard();

}
