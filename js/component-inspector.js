import * as THREE
from "three";

"use strict";

const inspectionState = {

  initialized:
    false,

  selectedMesh:
    null,

  selectedRoot:
    null,

  isolated:
    false,

  highlightCache:
    new Map(),

  visibilityCache:
    new Map()

};

let simulation =
  null;

let raycaster =
  null;

let pointer =
  null;

if (
  window.PRATIRUP_SIMULATION
) {

  initializeComponentInspector();

}

else {

  window.addEventListener(
    "pratirup:simulation-ready",
    initializeComponentInspector,
    {
      once: true
    }
  );

}

function initializeComponentInspector() {

  if (
    inspectionState.initialized
  ) {

    return;

  }

  simulation =
    window.PRATIRUP_SIMULATION;

  if (
    !simulation
  ) {

    console.error(
      "[PRATIRUP INSPECTOR] Simulation API unavailable."
    );

    return;

  }

  if (
    !simulation.renderer ||
    !simulation.camera ||
    !simulation.engine
  ) {

    console.error(
      "[PRATIRUP INSPECTOR] Required Three.js references missing."
    );

    return;

  }

  raycaster =
    new THREE.Raycaster();

  pointer =
    new THREE.Vector2();

  simulation
    .renderer
    .domElement
    .addEventListener(
      "pointerdown",
      handlePointerDown
    );

  inspectionState.initialized =
    true;

  console.log(
    "[PRATIRUP] Component inspector initialized."
  );

}

function handlePointerDown(
  event
) {

  if (
    event.button !== 0
  ) {

    return;

  }

  if (
    event.target.closest(
      "button, input, a"
    )
  ) {

    return;

  }

  const canvas =
    simulation.renderer.domElement;

  const rect =
    canvas.getBoundingClientRect();

  if (
    rect.width <= 0 ||
    rect.height <= 0
  ) {

    return;

  }

  pointer.x =

    (
      (
        event.clientX -
        rect.left
      ) /
      rect.width
    ) *
    2 -
    1;

  pointer.y =

    -(
      (
        event.clientY -
        rect.top
      ) /
      rect.height
    ) *
    2 +
    1;

  raycaster.setFromCamera(
    pointer,
    simulation.camera
  );

  const intersections =
    raycaster.intersectObject(
      simulation.engine,
      true
    );

  const validHits =
    intersections.filter(
      hit =>
        isSelectableObject(
          hit.object
        )
    );

  if (
    validHits.length === 0
  ) {

    clearSelection();

    return;

  }

  selectObject(
    validHits[0].object
  );

}

function isSelectableObject(
  object
) {

  if (
    !object
  ) {

    return false;

  }

  if (
    object.isPoints
  ) {

    return false;

  }

  if (
    object.isLine ||
    object.isLineSegments
  ) {

    return false;

  }

  if (
    !object.isMesh
  ) {

    return false;

  }

  if (
    !isObjectHierarchyVisible(
      object
    )
  ) {

    return false;

  }

  if (
    isInsideNamedParent(
      object,
      "TRANSPARENT ENGINE COVER"
    )
  ) {

    return false;

  }

  if (
    isInsideNamedParent(
      object,
      "Transparent Engine Cover"
    )
  ) {

    return false;

  }

  if (
    object.name ===
    "Transparent Engine Cover"
  ) {

    return false;

  }

  if (
    isInsideNamedParent(
      object,
      "Fuel Flow Visualization"
    )
  ) {

    return false;

  }

  return true;

}

function isObjectHierarchyVisible(
  object
) {

  let current =
    object;

  while (
    current
  ) {

    if (
      current.visible === false
    ) {

      return false;

    }

    current =
      current.parent;

  }

  return true;

}

function isInsideNamedParent(
  object,
  name
) {

  let current =
    object;

  while (
    current
  ) {

    if (
      current.name ===
      name
    ) {

      return true;

    }

    current =
      current.parent;

  }

  return false;

}

function findComponentRoot(
  mesh
) {

  let current =
    mesh;

  while (
    current &&
    current !==
    simulation.engine
  ) {

    if (
      current.userData
        ?.componentRoot ===
      true
    ) {

      return current;

    }

    current =
      current.parent;

  }

  current =
    mesh;

  while (
    current &&
    current !==
    simulation.engine
  ) {

    if (
      current.isGroup &&
      current.name &&
      current.name.trim()
    ) {

      return current;

    }

    current =
      current.parent;

  }

  current =
    mesh;

  while (
    current &&
    current !==
    simulation.engine
  ) {

    if (
      current.name &&
      current.name.trim()
    ) {

      return current;

    }

    current =
      current.parent;

  }

  return mesh;

}

function getComponentName(
  object
) {

  if (
    object?.userData
      ?.componentName
  ) {

    return String(
      object.userData
        .componentName
    );

  }

  if (
    object?.name &&
    object.name.trim()
  ) {

    return object.name.trim();

  }

  if (
    object?.geometry
      ?.type
  ) {

    return object.geometry.type
      .replace(
        "Geometry",
        ""
      )
      .toUpperCase();

  }

  return "ENGINE COMPONENT";

}

function selectObject(
  mesh
) {

  if (
    inspectionState.isolated
  ) {

    restoreIsolation();

  }

  clearHighlight();

  inspectionState.selectedMesh =
    mesh;

  inspectionState.selectedRoot =
    findComponentRoot(
      mesh
    );

  highlightComponent(
    inspectionState.selectedRoot
  );

  const name =
    getComponentName(
      inspectionState.selectedRoot
    );

  updateInspectionUI(
    name
  );

  window.dispatchEvent(

    new CustomEvent(
      "pratirup:component-selected",
      {

        detail: {

          name,

          object:
            inspectionState
              .selectedRoot

        }

      }
    )

  );

  console.log(
    "[PRATIRUP] Selected component:",
    name
  );

}

function highlightComponent(
  root
) {

  if (
    !root
  ) {

    return;

  }

  root.traverse(
    object => {

      if (
        !object.isMesh ||
        !object.material
      ) {

        return;

      }

      inspectionState
        .highlightCache
        .set(
          object,
          object.material
        );

      if (
        Array.isArray(
          object.material
        )
      ) {

        object.material =
          object.material.map(
            material => {

              const clone =
                material.clone();

              applyHighlightMaterial(
                clone
              );

              return clone;

            }
          );

      }

      else {

        const clone =
          object.material.clone();

        applyHighlightMaterial(
          clone
        );

        object.material =
          clone;

      }

    }
  );

}

function applyHighlightMaterial(
  material
) {

  if (
    material.emissive
  ) {

    material.emissive.set(
      0x00b7e8
    );

    material.emissiveIntensity =
      1.45;

  }

  if (
    material.color
  ) {

    material.color.offsetHSL(
      0,
      0,
      0.10
    );

  }

  if (
    typeof
    material.roughness ===
    "number"
  ) {

    material.roughness =
      Math.max(
        0.12,
        material.roughness *
        0.82
      );

  }

}

function clearHighlight() {

  inspectionState
    .highlightCache
    .forEach(
      (
        originalMaterial,
        object
      ) => {

        if (
          Array.isArray(
            object.material
          )
        ) {

          object.material.forEach(
            material => {

              material.dispose?.();

            }
          );

        }

        else {

          object.material
            ?.dispose?.();

        }

        object.material =
          originalMaterial;

      }
    );

  inspectionState
    .highlightCache
    .clear();

}

function clearSelection() {

  clearHighlight();

  inspectionState.selectedMesh =
    null;

  inspectionState.selectedRoot =
    null;

  updateInspectionUI(
    "NONE"
  );

  window.dispatchEvent(

    new CustomEvent(
      "pratirup:component-cleared"
    )

  );

}

function updateInspectionUI(
  name
) {

  const inspectionMode =
    document.getElementById(
      "inspectionModeText"
    );

  const currentView =
    document.getElementById(
      "currentViewText"
    );

  const selectedComponent =
    document.getElementById(
      "selectedComponentName"
    );

  if (
    inspectionMode
  ) {

    inspectionMode.textContent =
      name === "NONE"
        ? "STANDARD"
        : "COMPONENT";

  }

  if (
    currentView
  ) {

    currentView.textContent =
      name === "NONE"
        ? "ASSEMBLED"
        : name.toUpperCase();

  }

  if (
    selectedComponent
  ) {

    selectedComponent.textContent =
      name;

  }

}

function focusSelectedComponent() {

  const selected =
    inspectionState.selectedRoot;

  if (
    !selected ||
    !simulation
  ) {

    console.warn(
      "[PRATIRUP] Select an engine component first."
    );

    return;

  }

  const bounds =
    new THREE.Box3()
      .setFromObject(
        selected
      );

  if (
    bounds.isEmpty()
  ) {

    return;

  }

  const center =
    new THREE.Vector3();

  const size =
    new THREE.Vector3();

  bounds.getCenter(
    center
  );

  bounds.getSize(
    size
  );

  const largestDimension =
    Math.max(
      size.x,
      size.y,
      size.z,
      0.8
    );

  const distance =
    THREE.MathUtils.clamp(
      largestDimension *
      2.7,
      2.7,
      14
    );

  simulation
    .controls
    .target
    .copy(
      center
    );

  simulation
    .camera
    .position
    .set(

      center.x +
      distance,

      center.y +
      distance *
      0.52,

      center.z +
      distance *
      0.82

    );

  simulation
    .controls
    .update();

  console.log(
    "[PRATIRUP] Focused:",
    getComponentName(
      selected
    )
  );

}

function findTopLevelEngineChild(
  object
) {

  let current =
    object;

  while (
    current.parent &&
    current.parent !==
    simulation.engine
  ) {

    current =
      current.parent;

  }

  return current;

}

function isolateSelectedComponent() {

  if (
    !inspectionState.selectedRoot ||
    !simulation
  ) {

    console.warn(
      "[PRATIRUP] Select an engine component first."
    );

    return;

  }

  if (
    inspectionState.isolated
  ) {

    restoreIsolation();

    return;

  }

  const selectedTopLevel =
    findTopLevelEngineChild(
      inspectionState.selectedRoot
    );

  if (
    !selectedTopLevel
  ) {

    return;

  }

  inspectionState
    .visibilityCache
    .clear();

  simulation.engine.children
    .forEach(
      child => {

        inspectionState
          .visibilityCache
          .set(
            child,
            child.visible
          );

        child.visible =
          child ===
          selectedTopLevel;

      }
    );

  const cover =
    simulation.groups
      ?.cover;

  if (
    cover
  ) {

    cover.visible =
      false;

  }

  inspectionState.isolated =
    true;

  updateIsolationButton(
    true
  );

  window.dispatchEvent(

    new CustomEvent(
      "pratirup:isolation-change",
      {

        detail: {

          value:
            true,

          component:
            getComponentName(
              inspectionState
                .selectedRoot
            )

        }

      }
    )

  );

  focusSelectedComponent();

  console.log(
    "[PRATIRUP] Component isolated."
  );

}

function restoreIsolation() {

  if (
    !inspectionState.isolated
  ) {

    return;

  }

  inspectionState
    .visibilityCache
    .forEach(
      (
        visible,
        object
      ) => {

        object.visible =
          visible;

      }
    );

  inspectionState
    .visibilityCache
    .clear();

  const cover =
    simulation.groups
      ?.cover;

  if (
    cover
  ) {

    const bridgeState =
      window.PRATIRUP_BRIDGE
        ?.getState?.();

    if (
      bridgeState &&
      typeof
      bridgeState.cover ===
      "boolean"
    ) {

      cover.visible =
        bridgeState.cover;

    }

    else {

      cover.visible =
        true;

    }

  }

  inspectionState.isolated =
    false;

  updateIsolationButton(
    false
  );

  window.dispatchEvent(

    new CustomEvent(
      "pratirup:isolation-change",
      {

        detail: {

          value:
            false

        }

      }
    )

  );

  console.log(
    "[PRATIRUP] Full engine restored."
  );

}

function updateIsolationButton(
  isolated
) {

  const button =
    document.getElementById(
      "isolateComponentButton"
    );

  if (
    !button
  ) {

    return;

  }

  button.textContent =
    isolated
      ? "RESTORE"
      : "ISOLATE";

  button.classList.toggle(
    "active",
    isolated
  );

}

function resetInspection() {

  if (
    inspectionState.isolated
  ) {

    restoreIsolation();

  }

  clearSelection();

  if (
    simulation
  ) {

    simulation
      .resetCamera?.();

  }

  console.log(
    "[PRATIRUP] Inspection cleared."
  );

}

document
  .getElementById(
    "focusComponentButton"
  )
  ?.addEventListener(
    "click",
    focusSelectedComponent
  );

document
  .getElementById(
    "isolateComponentButton"
  )
  ?.addEventListener(
    "click",
    isolateSelectedComponent
  );

document
  .getElementById(
    "clearComponentButton"
  )
  ?.addEventListener(
    "click",
    resetInspection
  );

window.addEventListener(
  "keydown",
  event => {

    if (
      event.key !==
      "Escape"
    ) {

      return;

    }

    if (
      inspectionState.isolated
    ) {

      restoreIsolation();

    }

    else {

      clearSelection();

    }

  }
);

window.PRATIRUP_INSPECTOR = {

  get selected() {

    return inspectionState
      .selectedRoot;

  },

  get isolated() {

    return inspectionState
      .isolated;

  },

  focus() {

    focusSelectedComponent();

  },

  isolate() {

    isolateSelectedComponent();

  },

  restore() {

    restoreIsolation();

  },

  clear() {

    resetInspection();

  }

};

console.log(
  "[PRATIRUP] Component Inspector module loaded."
);
