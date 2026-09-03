import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.164.1/build/three.module.js";
import { OrbitControls } from "https://cdn.jsdelivr.net/npm/three@0.164.1/examples/jsm/controls/OrbitControls.js";
import { CSS2DRenderer, CSS2DObject } from "https://cdn.jsdelivr.net/npm/three@0.164.1/examples/jsm/renderers/CSS2DRenderer.js";



function startPratirupFullDetailSimulation() {


const simulationHost =
  document.getElementById("engineCanvasHost") ||
  document.querySelector("[data-pratirup-canvas]") ||
  document.getElementById("canvasRegion") ||
  document.getElementById("canvas-region");


if (!simulationHost) {

  throw new Error(
    'PRATIRUP: dashboard canvas host not found. ' +
    'Add id="engineCanvasHost" to your dashboard canvas region.'
  );

}


const computedHostStyle =
  getComputedStyle(simulationHost);


if (
  computedHostStyle.position ===
  "static"
) {

  simulationHost.style.position =
    "relative";

}


simulationHost.style.overflow =
  "hidden";


const oldPlaceholder =
  simulationHost.querySelector(
    ".canvas-placeholder"
  );


if (oldPlaceholder) {

  oldPlaceholder.remove();

}


if (
  simulationHost
    .getBoundingClientRect()
    .height < 2
) {

  console.warn(
    "[PRATIRUP] engineCanvasHost has no height. Applying minimum height."
  );

  simulationHost.style.minHeight =
    "520px";

}


function getPratirupHostSize() {

  const rect =
    simulationHost
      .getBoundingClientRect();


  return {

    width:
      Math.max(
        1,
        Math.floor(
          rect.width ||
          simulationHost.clientWidth ||
          800
        )
      ),

    height:
      Math.max(
        1,
        Math.floor(
          rect.height ||
          simulationHost.clientHeight ||
          520
        )
      )

  };

}

if (
  !document.getElementById(
    "pratirupEmbeddedLabelStyle"
  )
) {

  const style =
    document.createElement(
      "style"
    );


  style.id =
    "pratirupEmbeddedLabelStyle";


  style.textContent = `

    #engineCanvasHost .label,
    [data-pratirup-canvas] .label {

      color: #fff;

      font-family:
        Arial,
        sans-serif;

      font-size: 11px;

      white-space: nowrap;

      background:
        rgba(
          5,
          10,
          18,
          .88
        );

      border:
        1px solid
        rgba(
          0,
          217,
          255,
          .55
        );

      border-radius:
        4px;

      padding:
        4px 7px;

      pointer-events:
        none;

    }

  `;


  document.head.appendChild(
    style
  );

}

const pratirupUiAliases = {

  toggleAnimation: [

    "toggleAnimation",

    "runEngineButton",

    "runButton",

    "runBtn",

    "engineRunButton",

    "startStopButton"

  ],


  explodeButton: [

    "explodeButton",

    "explodeBtn",

    "explodedViewButton",

    "explodedButton",

    "btnExplode"

  ],


  wireframeButton: [

    "wireframeButton",

    "wireframeBtn",

    "wireButton",

    "btnWireframe"

  ],


  labelsButton: [

    "labelsButton",

    "labelButton",

    "labelsBtn",

    "componentLabelsButton"

  ],


  resetButton: [

    "resetButton",

    "resetCameraButton",

    "resetCameraBtn",

    "resetBtn"

  ],


  rpmSlider: [

    "rpmSlider",

    "engineRpmSlider",

    "rpmControl"

  ],


  rpmText: [

    "rpmText",

    "engineRpmText",

    "rpmValue"

  ]

};


const compatibilityRoot =
  document.createElement(
    "div"
  );


compatibilityRoot.id =
  "pratirupHiddenCompatibility";


compatibilityRoot.style.display =
  "none";


document.body.appendChild(
  compatibilityRoot
);



const inputDefaults = {

  rpmSlider:
    "2200",

  envAltitude:
    "0",

  envTemp:
    "25",

  envHumidity:
    "45"

};



const buttonIds =
  new Set([

    "toggleAnimation",

    "explodeButton",

    "wireframeButton",

    "labelsButton",

    "resetButton",

    "fuelFlowToggle",

    "toggleEngineControls",

    "togglePhysicsPanel",

    "toggleEnvironmentPanel",

    "toggleFuelPanel",

    "toggleThermoPanel",

    "toggleDetailLayers",

    "hideAllPanels"

  ]);



const inputIds =
  new Set([

    "rpmSlider",

    "envAltitude",

    "envTemp",

    "envHumidity"

  ]);



function createCompatibilityElement(
  id
) {

  let element;


  if (
    inputIds.has(id)
  ) {

    element =
      document.createElement(
        "input"
      );

    element.type =
      "range";

    element.value =
      inputDefaults[id] ||
      "0";

  }

  else if (
    buttonIds.has(id)
  ) {

    element =
      document.createElement(
        "button"
      );

  }

  else {

    element =
      document.createElement(
        "div"
      );

  }


  element.id =
    id;


  element.style.display =
    "none";


  if (
    id ===
    "status"
  ) {

    element.appendChild(

      document.createTextNode(
        " DIGITAL TWIN ENGINE RUNNING"
      )

    );

  }


  compatibilityRoot.appendChild(
    element
  );


  return element;

}



function pratirupElement(
  id
) {

  const aliases =
    pratirupUiAliases[id] ||
    [id];


  for (
    const alias
    of aliases
  ) {

    const existing =
      document.getElementById(
        alias
      );


    if (
      existing
    ) {

      return existing;

    }

  }


  return createCompatibilityElement(
    id
  );

}


window.addEventListener(

  "error",

  event => {

    const box =
      pratirupElement(
        "runtimeErrorBox"
      );


    if (
      box
    ) {

      box.style.display =
        "block";


      box.textContent =

        "Runtime error: "

        +

        (
          event.message ||
          "Unknown rendering error"
        );

    }

  }

);



window.addEventListener(

  "unhandledrejection",

  event => {

    const box =
      pratirupElement(
        "runtimeErrorBox"
      );


    if (
      box
    ) {

      box.style.display =
        "block";


      box.textContent =

        "Promise error: "

        +

        String(
          event.reason ||
          "Unknown error"
        );

    }

  }

);

const scene =
  new THREE.Scene();


scene.background =
  new THREE.Color(
    0x05080d
  );


const initialHostSize =
  getPratirupHostSize();


const camera =
  new THREE.PerspectiveCamera(

    45,

    initialHostSize.width /
    initialHostSize.height,

    0.1,

    1000

  );


camera.position.set(
  11,
  8,
  14
);


const renderer =
  new THREE.WebGLRenderer({

    antialias:
      true

  });


renderer.setSize(

  initialHostSize.width,

  initialHostSize.height,

  false

);


renderer.setPixelRatio(

  Math.min(

    window.devicePixelRatio,

    2

  )

);


renderer.shadowMap.enabled =
  true;


renderer.shadowMap.type =
  THREE.PCFSoftShadowMap;


renderer.outputColorSpace =
  THREE.SRGBColorSpace;



renderer.domElement.style.position =
  "absolute";


renderer.domElement.style.inset =
  "0";


renderer.domElement.style.width =
  "100%";


renderer.domElement.style.height =
  "100%";


renderer.domElement.style.display =
  "block";


renderer.domElement.style.zIndex =
  "0";



simulationHost.insertBefore(

  renderer.domElement,

  simulationHost.firstChild

);


const labelRenderer =
  new CSS2DRenderer();


labelRenderer.setSize(

  initialHostSize.width,

  initialHostSize.height

);


labelRenderer.domElement.style.position =
  "absolute";


labelRenderer.domElement.style.inset =
  "0";


labelRenderer.domElement.style.width =
  "100%";


labelRenderer.domElement.style.height =
  "100%";


labelRenderer.domElement.style.pointerEvents =
  "none";


labelRenderer.domElement.style.zIndex =
  "1";


simulationHost.appendChild(

  labelRenderer.domElement

);

const controls =
  new OrbitControls(

    camera,

    renderer.domElement

  );


controls.enableDamping =
  true;


controls.dampingFactor =
  0.05;


controls.target.set(
  0,
  1.5,
  0
);


controls.minDistance =
  6;


controls.maxDistance =
  30;



const ambientLight =
  new THREE.AmbientLight(

    0xffffff,

    1.4

  );


scene.add(
  ambientLight
);



const keyLight =
  new THREE.DirectionalLight(

    0xffffff,

    4

  );


keyLight.position.set(
  7,
  12,
  8
);


keyLight.castShadow =
  true;


scene.add(
  keyLight
);



const blueLight =
  new THREE.PointLight(

    0x00d9ff,

    35,

    25

  );


blueLight.position.set(
  -7,
  5,
  -5
);


scene.add(
  blueLight
);



const rimLight =
  new THREE.PointLight(

    0x007bff,

    30,

    20

  );


rimLight.position.set(
  6,
  2,
  -8
);


scene.add(
  rimLight
);

const metal =
  new THREE.MeshStandardMaterial({

    color:
      0x8d969f,

    metalness:
      0.85,

    roughness:
      0.28

  });



const darkMetal =
  new THREE.MeshStandardMaterial({

    color:
      0x232b31,

    metalness:
      0.85,

    roughness:
      0.25

  });



const blackMetal =
  new THREE.MeshStandardMaterial({

    color:
      0x090d11,

    metalness:
      0.75,

    roughness:
      0.35

  });



const silver =
  new THREE.MeshStandardMaterial({

    color:
      0xc2c9cf,

    metalness:
      0.95,

    roughness:
      0.18

  });



const steel =
  new THREE.MeshStandardMaterial({

    color:
      0x68727c,

    metalness:
      0.95,

    roughness:
      0.2

  });



const copper =
  new THREE.MeshStandardMaterial({

    color:
      0xa75c32,

    metalness:
      0.65,

    roughness:
      0.3

  });



const blueMaterial =
  new THREE.MeshStandardMaterial({

    color:
      0x007bff,

    emissive:
      0x00152f,

    metalness:
      0.65,

    roughness:
      0.22

  });



const redMaterial =
  new THREE.MeshStandardMaterial({

    color:
      0xd52b2b,

    metalness:
      0.35,

    roughness:
      0.4

  });



const glassMaterial =
  new THREE.MeshPhysicalMaterial({

    color:
      0x00d9ff,

    transparent:
      true,

    opacity:
      0.18,

    roughness:
      0.1,

    metalness:
      0.1,

    transmission:
      0.4

  });



const materials = [

  metal,

  darkMetal,

  blackMetal,

  silver,

  steel,

  copper,

  blueMaterial,

  redMaterial

];



// ========================================================
// ENGINE ROOT
// ========================================================

const engine =
  new THREE.Group();


scene.add(
  engine
);

function box(
  width,
  height,
  depth,
  material
) {

  const geometry =
    new THREE.BoxGeometry(

      width,

      height,

      depth

    );


  const mesh =
    new THREE.Mesh(

      geometry,

      material

    );


  mesh.castShadow =
    true;


  mesh.receiveShadow =
    true;


  return mesh;

}



function cylinder(
  radius,
  height,
  material,
  segments = 32
) {

  const geometry =
    new THREE.CylinderGeometry(

      radius,

      radius,

      height,

      segments

    );


  const mesh =
    new THREE.Mesh(

      geometry,

      material

    );


  mesh.castShadow =
    true;


  mesh.receiveShadow =
    true;


  return mesh;

}



const componentLabels =
  [];


function addLabel(
  object,
  text,
  position
) {

  const div =
    document.createElement(
      "div"
    );


  div.className =
    "label";


  div.textContent =
    text;


  const label =
    new CSS2DObject(
      div
    );


  label.position.copy(
    position
  );


  label.visible =
    false;


  object.add(
    label
  );


  componentLabels.push(
    label
  );


  return label;

}

const lowerCrankcase =
  box(

    6.4,

    1.55,

    3,

    darkMetal

  );


lowerCrankcase.position.y =
  0.45;


engine.add(
  lowerCrankcase
);



const upperCase =
  box(

    5.8,

    1.15,

    2.7,

    metal

  );


upperCase.position.y =
  1.55;


engine.add(
  upperCase
);



addLabel(

  upperCase,

  "Aluminium Crankcase",

  new THREE.Vector3(
    0,
    1.2,
    1.7
  )

);

const sideCoverGeometry =
  new THREE.CylinderGeometry(

    1.15,

    1.15,

    0.2,

    48

  );


const leftCover =
  new THREE.Mesh(

    sideCoverGeometry,

    silver

  );


leftCover.rotation.z =
  Math.PI / 2;


leftCover.position.set(
  -3.3,
  0.7,
  0
);


engine.add(
  leftCover
);



const rightCover =
  leftCover.clone();


rightCover.position.x =
  3.3;


engine.add(
  rightCover
);


const cylinderGroups =
  [];


const cylinderPositions = [

  -2.05,

  -0.7,

  0.7,

  2.05

];



function createCylinderAssembly(
  x
) {

  const group =
    new THREE.Group();


  group.position.x =
    x;



  const barrel =
    cylinder(

      0.58,

      2.25,

      darkMetal

    );


  barrel.position.y =
    2.75;


  group.add(
    barrel
  );



  for (
    let i = 0;
    i < 9;
    i++
  ) {

    const fin =
      cylinder(

        0.81,

        0.09,

        silver,

        40

      );


    fin.position.y =

      1.9 +
      i * 0.23;


    group.add(
      fin
    );

  }



  const head =
    box(

      1.35,

      0.48,

      1.4,

      silver

    );


  head.position.y =
    4;


  group.add(
    head
  );



  const cover =
    box(

      1.15,

      0.23,

      1.15,

      blackMetal

    );


  cover.position.y =
    4.36;


  group.add(
    cover
  );



  const injector =
    cylinder(

      0.09,

      0.48,

      copper,

      20

    );


  injector.position.set(
    0,
    4.67,
    0
  );


  group.add(
    injector
  );



  const connector =
    box(

      0.22,

      0.2,

      0.22,

      blackMetal

    );


  connector.position.y =
    4.95;


  group.add(
    connector
  );



  addLabel(

    group,

    "Cylinder",

    new THREE.Vector3(
      0,
      3,
      1.1
    )

  );


  engine.add(
    group
  );


  cylinderGroups.push(
    group
  );


  return group;

}



cylinderPositions.forEach(

  x =>
    createCylinderAssembly(
      x
    )

);

const pistons =
  [];


const connectingRods =
  [];


cylinderPositions.forEach(

  (
    x,
    index
  ) => {


    const piston =
      cylinder(

        0.46,

        0.58,

        silver

      );


    piston.position.set(
      x,
      2.35,
      0
    );


    engine.add(
      piston
    );


    pistons.push(
      piston
    );



    const rod =
      box(

        0.18,

        1.7,

        0.18,

        steel

      );


    rod.position.set(
      x,
      1.45,
      0
    );


    engine.add(
      rod
    );


    connectingRods.push(
      rod
    );

  }

);

const crankshaftGroup =
  new THREE.Group();


engine.add(
  crankshaftGroup
);



const shaft =
  cylinder(

    0.18,

    7.8,

    steel,

    32

  );


shaft.rotation.z =
  Math.PI / 2;


shaft.position.y =
  0.65;


crankshaftGroup.add(
  shaft
);



cylinderPositions.forEach(

  x => {


    const weight =
      cylinder(

        0.52,

        0.18,

        darkMetal,

        32

      );


    weight.rotation.z =
      Math.PI / 2;


    weight.position.set(
      x,
      0.65,
      0
    );


    crankshaftGroup.add(
      weight
    );

  }

);



addLabel(

  crankshaftGroup,

  "Crankshaft",

  new THREE.Vector3(
    0,
    0.5,
    1.8
  )

);

const outputShaft =
  cylinder(

    0.22,

    3,

    silver

  );


outputShaft.rotation.z =
  Math.PI / 2;


outputShaft.position.set(
  -4.65,
  0.7,
  0
);


engine.add(
  outputShaft
);



const outputHub =
  cylinder(

    0.85,

    0.38,

    darkMetal,

    48

  );


outputHub.rotation.z =
  Math.PI / 2;


outputHub.position.set(
  -3.65,
  0.7,
  0
);


engine.add(
  outputHub
);

const rotorAssembly =
  new THREE.Group();


rotorAssembly.position.set(
  -6.45,
  0.7,
  0
);


engine.add(
  rotorAssembly
);



const rotorCoupling =
  cylinder(

    0.33,

    0.62,

    blueMaterial,

    32

  );


rotorCoupling.rotation.z =
  Math.PI / 2;


rotorCoupling.position.x =
  0.42;


rotorAssembly.add(
  rotorCoupling
);



const rotorHub =
  cylinder(

    0.5,

    0.62,

    darkMetal,

    40

  );


rotorHub.rotation.z =
  Math.PI / 2;


rotorAssembly.add(
  rotorHub
);



const rotorSpinner =
  new THREE.Mesh(

    new THREE.ConeGeometry(

      0.52,

      1.05,

      40

    ),

    silver

  );


rotorSpinner.rotation.z =
  -Math.PI / 2;


rotorSpinner.position.x =
  -0.78;


rotorSpinner.castShadow =
  true;


rotorAssembly.add(
  rotorSpinner
);



const rotorFan =
  new THREE.Group();


rotorAssembly.add(
  rotorFan
);


function createUavPropellerBlade() {

  const bladeRoot =
    new THREE.Group();


  const stations =
    14;


  const rootRadius =
    0.48;


  const bladeLength =
    3.15;



  for (
    let i = 0;
    i < stations;
    i++
  ) {

    const t =
      i /
      (
        stations -
        1
      );


    const radius =

      rootRadius +
      t *
      bladeLength;


    const segmentLength =

      bladeLength /
      stations +
      0.035;


    const chord =
      THREE.MathUtils.lerp(

        0.62,

        0.18,

        Math.pow(
          t,
          0.82
        )

      );


    const thickness =
      THREE.MathUtils.lerp(

        0.14,

        0.055,

        t

      );


    const pitchDeg =
      THREE.MathUtils.lerp(

        31,

        9,

        t

      );


    const sweep =

      0.18 *
      Math.pow(
        t,
        1.6
      );


    const segment =
      new THREE.Mesh(

        new THREE.BoxGeometry(

          thickness,

          segmentLength,

          chord

        ),

        silver

      );


    segment.position.set(

      0,

      radius +
      segmentLength *
      0.5,

      -sweep

    );


    segment.rotation.y =
      THREE.MathUtils.degToRad(
        pitchDeg
      );


    segment.rotation.x =
      THREE.MathUtils.degToRad(
        -2.5 * t
      );


    segment.castShadow =
      true;


    segment.receiveShadow =
      true;


    bladeRoot.add(
      segment
    );

  }



  const tip =
    new THREE.Mesh(

      new THREE.SphereGeometry(
        0.13,
        20,
        12
      ),

      silver

    );


  tip.scale.set(
    0.42,
    1.15,
    0.75
  );


  tip.position.set(

    0,

    rootRadius +
    bladeLength +
    0.05,

    -0.18

  );


  bladeRoot.add(
    tip
  );


  return bladeRoot;

}



for (
  let i = 0;
  i < 3;
  i++
) {

  const bladePivot =
    new THREE.Group();


  bladePivot.rotation.x =

    i *
    (
      Math.PI *
      2 /
      3
    );


  bladePivot.add(

    createUavPropellerBlade()

  );


  rotorFan.add(
    bladePivot
  );

}



const bladeRootFairing =
  cylinder(

    0.61,

    0.24,

    silver,

    48

  );


bladeRootFairing.rotation.z =
  Math.PI / 2;


bladeRootFairing.position.x =
  -0.05;


rotorAssembly.add(
  bladeRootFairing
);


const flywheel =
  cylinder(

    1.05,

    0.32,

    steel,

    48

  );


flywheel.rotation.z =
  Math.PI / 2;


flywheel.position.set(
  3.75,
  0.7,
  0
);


engine.add(
  flywheel
);


const intakeManifold =
  box(

    5.8,

    0.44,

    0.5,

    blueMaterial

  );


intakeManifold.position.set(

  0,

  4.8,

  -1.1

);


engine.add(
  intakeManifold
);



cylinderPositions.forEach(

  x => {

    const runner =
      cylinder(

        0.13,

        1.1,

        blueMaterial

      );


    runner.position.set(

      x,

      4.45,

      -0.6

    );


    runner.rotation.x =
      Math.PI / 2.7;


    engine.add(
      runner
    );

  }

);

const exhaustMain =
  box(

    5.6,

    0.35,

    0.4,

    steel

  );


exhaustMain.position.set(
  0,
  3.85,
  1.35
);


engine.add(
  exhaustMain
);



cylinderPositions.forEach(

  x => {

    const exhaustPipe =
      cylinder(

        0.12,

        1,

        steel

      );


    exhaustPipe.position.set(
      x,
      3.85,
      0.85
    );


    exhaustPipe.rotation.x =
      Math.PI / 2;


    engine.add(
      exhaustPipe
    );

  }

);


const turboGroup =
  new THREE.Group();


turboGroup.position.set(
  3.15,
  4.65,
  1.3
);


engine.add(
  turboGroup
);



const turboOuter =
  new THREE.Mesh(

    new THREE.TorusGeometry(

      0.62,

      0.22,

      18,

      48

    ),

    darkMetal

  );


turboGroup.add(
  turboOuter
);



const turboCenter =
  cylinder(

    0.27,

    0.38,

    silver

  );


turboCenter.rotation.x =
  Math.PI / 2;


turboGroup.add(
  turboCenter
);



const turboBladeGroup =
  new THREE.Group();


turboGroup.add(
  turboBladeGroup
);



for (
  let i = 0;
  i < 8;
  i++
) {

  const blade =
    box(

      0.05,

      0.42,

      0.07,

      silver

    );


  blade.position.y =
    0.2;


  blade.rotation.z =

    (
      i /
      8
    ) *
    Math.PI *
    2;


  turboBladeGroup.add(
    blade
  );

}
// ------------------------------------------------------------FADEC ----------------------------------------
const fadec =
  box(

    1.75,

    0.85,

    1.25,

    blackMetal

  );


fadec.position.set(
  2.2,
  2.15,
  -2
);


engine.add(
  fadec
);



const ecuPanel =
  box(

    1.45,

    0.05,

    0.95,

    blueMaterial

  );


ecuPanel.position.set(
  2.2,
  2.58,
  -2
);


engine.add(
  ecuPanel
);


const starter =
  cylinder(

    0.55,

    1.65,

    darkMetal

  );


starter.rotation.z =
  Math.PI / 2;


starter.position.set(
  -2.3,
  1.55,
  -1.9
);


engine.add(
  starter
);



const starterCap =
  cylinder(

    0.58,

    0.15,

    blueMaterial

  );


starterCap.rotation.z =
  Math.PI / 2;


starterCap.position.set(
  -3.1,
  1.55,
  -1.9
);


engine.add(
  starterCap
);


const oilFilter =
  cylinder(

    0.32,

    1.2,

    blueMaterial

  );


oilFilter.position.set(
  -2.6,
  0.2,
  -1.65
);


engine.add(
  oilFilter
);


const fuelRail =
  cylinder(

    0.08,

    5,

    copper

  );


fuelRail.rotation.z =
  Math.PI / 2;


fuelRail.position.set(
  0,
  4.95,
  0.65
);


engine.add(
  fuelRail
);



cylinderPositions.forEach(

  x => {

    const fuelLine =
      cylinder(

        0.035,

        0.7,

        copper,

        12

      );


    fuelLine.position.set(
      x,
      4.72,
      0.35
    );


    fuelLine.rotation.x =
      Math.PI / 2.5;


    engine.add(
      fuelLine
    );

  }

);


const fuelFlowGroup =
  new THREE.Group();


engine.add(
  fuelFlowGroup
);


let fuelFlowVisible =
  true;



const fuelParticleMaterial =
  new THREE.PointsMaterial({

    color:
      0xffb347,

    size:
      0.075,

    transparent:
      true,

    opacity:
      0.95,

    depthWrite:
      false,

    blending:
      THREE.AdditiveBlending

  });



const combustionMaterial =
  new THREE.MeshBasicMaterial({

    color:
      0xff542e,

    transparent:
      true,

    opacity:
      0,

    depthWrite:
      false,

    blending:
      THREE.AdditiveBlending

  });



const injectorPulseMaterial =
  new THREE.MeshBasicMaterial({

    color:
      0xffd56a,

    transparent:
      true,

    opacity:
      0,

    depthWrite:
      false,

    blending:
      THREE.AdditiveBlending

  });



const fuelJets =
  [];


const combustionGlows =
  [];


const injectorPulses =
  [];



const injectionPhase = [

  0,

  Math.PI,

  Math.PI * 0.5,

  Math.PI * 1.5

];



function createFuelJet(
  x,
  cylinderIndex
) {

  const particleCount =
    44;


  const positions =
    new Float32Array(

      particleCount *
      3

    );


  const phases =
    new Float32Array(
      particleCount
    );



  for (
    let i = 0;
    i < particleCount;
    i++
  ) {

    phases[i] =
      i /
      particleCount;


    positions[
      i * 3
    ] =
      x;


    positions[
      i * 3 + 1
    ] =
      4.62;


    positions[
      i * 3 + 2
    ] =
      0;

  }



  const geometry =
    new THREE.BufferGeometry();


  geometry.setAttribute(

    "position",

    new THREE.BufferAttribute(

      positions,

      3

    )

  );



  const points =
    new THREE.Points(

      geometry,

      fuelParticleMaterial.clone()

    );


  points.frustumCulled =
    false;


  fuelFlowGroup.add(
    points
  );



  const injectorPulse =
    new THREE.Mesh(

      new THREE.RingGeometry(

        0.09,

        0.18,

        24

      ),

      injectorPulseMaterial.clone()

    );


  injectorPulse.rotation.x =
    -Math.PI / 2;


  injectorPulse.position.set(
    x,
    4.42,
    0
  );


  fuelFlowGroup.add(
    injectorPulse
  );



  const glow =
    new THREE.Mesh(

      new THREE.SphereGeometry(

        0.42,

        24,

        16

      ),

      combustionMaterial.clone()

    );


  glow.scale.set(
    1,
    0.38,
    1
  );


  glow.position.set(
    x,
    3.35,
    0
  );


  fuelFlowGroup.add(
    glow
  );



  fuelJets.push({

    points,

    phases,

    cylinderIndex

  });


  injectorPulses.push(
    injectorPulse
  );


  combustionGlows.push(
    glow
  );

}



cylinderPositions.forEach(

  (
    x,
    index
  ) =>

    createFuelJet(
      x,
      index
    )

);


const railPulseGeometry =
  new THREE.SphereGeometry(

    0.085,

    16,

    12

  );


const railPulseMaterial =
  new THREE.MeshBasicMaterial({

    color:
      0xffb347,

    transparent:
      true,

    opacity:
      0.9,

    depthWrite:
      false,

    blending:
      THREE.AdditiveBlending

  });


const railPulses =
  [];


for (
  let i = 0;
  i < 8;
  i++
) {

  const pulse =
    new THREE.Mesh(

      railPulseGeometry,

      railPulseMaterial.clone()

    );


  pulse.position.set(
    -2.5,
    4.95,
    0.65
  );


  fuelFlowGroup.add(
    pulse
  );


  railPulses.push(
    pulse
  );

}

function addSensor(
  x,
  y,
  z
) {

  const sensor =
    box(

      0.22,

      0.22,

      0.22,

      redMaterial

    );


  sensor.position.set(
    x,
    y,
    z
  );


  engine.add(
    sensor
  );


  return sensor;

}


addSensor(
  -1.9,
  4.38,
  -0.65
);


addSensor(
  1.9,
  4.38,
  -0.65
);


addSensor(
  0,
  1.9,
  1.55
);



const airFilter =
  cylinder(

    0.55,

    1.25,

    blackMetal

  );


airFilter.rotation.z =
  Math.PI / 2;


airFilter.position.set(
  -3.55,
  4.75,
  -1.1
);


engine.add(
  airFilter
);



for (
  let i = 0;
  i < 8;
  i++
) {

  const filterFin =
    cylinder(

      0.58,

      0.035,

      silver

    );


  filterFin.rotation.z =
    Math.PI / 2;


  filterFin.position.set(

    -3.15 -
    i * 0.1,

    4.75,

    -1.1

  );


  engine.add(
    filterFin
  );

}

const base =
  box(

    9.5,

    0.25,

    6,

    blackMetal

  );


base.position.y =
  -0.55;


engine.add(
  base
);



const pedestalGroup =
  new THREE.Group();


engine.add(
  pedestalGroup
);



[
  [-3.35, -2.15],
  [-3.35,  2.15],
  [ 3.35, -2.15],
  [ 3.35,  2.15]

]
.forEach(

  (
    [
      x,
      z
    ]
  ) => {


    const riser =
      box(

        0.62,

        4.60,

        0.62,

        darkMetal

      );


    riser.position.set(

      x,

      -2.745,

      z

    );


    pedestalGroup.add(
      riser
    );



    const foot =
      box(

        0.82,

        0.16,

        0.82,

        steel

      );


    foot.position.set(

      x,

      -5.09,

      z

    );


    pedestalGroup.add(
      foot
    );


  }

);

const fidelityGroup =
  new THREE.Group();


engine.add(
  fidelityGroup
);



const crankcaseMat =
  new THREE.MeshStandardMaterial({

    color:
      0x777b7d,

    roughness:
      0.48,

    metalness:
      0.58

  });



const crankcaseCore =
  new THREE.Mesh(

    new THREE.CylinderGeometry(

      1.55,

      1.72,

      1.25,

      12

    ),

    crankcaseMat

  );


crankcaseCore.rotation.z =
  Math.PI / 2;


crankcaseCore.position.set(
  -2.85,
  1.35,
  0
);


crankcaseCore.castShadow =
  true;


fidelityGroup.add(
  crankcaseCore
);


const reductionHousing =
  new THREE.Mesh(

    new THREE.CylinderGeometry(

      1.38,

      1.55,

      0.68,

      32

    ),

    crankcaseMat

  );


reductionHousing.rotation.z =
  Math.PI / 2;


reductionHousing.position.set(
  -4.25,
  1.05,
  0
);


reductionHousing.castShadow =
  true;


fidelityGroup.add(
  reductionHousing
);



const gearboxFace =
  new THREE.Mesh(

    new THREE.CylinderGeometry(

      1.18,

      1.18,

      0.10,

      32

    ),

    silver

  );


gearboxFace.rotation.z =
  Math.PI / 2;


gearboxFace.position.set(
  -4.61,
  1.05,
  0
);


fidelityGroup.add(
  gearboxFace
);



for (
  let i = 0;
  i < 10;
  i++
) {

  const a =

    i *
    Math.PI *
    2 /
    10;


  const bolt =
    cylinder(

      0.07,

      0.10,

      darkMetal,

      12

    );


  bolt.rotation.z =
    Math.PI / 2;


  bolt.position.set(

    -4.69,

    1.05 +
    Math.cos(a) *
    0.92,

    Math.sin(a) *
    0.92

  );


  fidelityGroup.add(
    bolt
  );

}


[
  -1,
  1
]
.forEach(

  side => {


    const bank =
      new THREE.Group();



    const head =
      box(

        3.65,

        0.72,

        1.05,

        crankcaseMat

      );


    head.position.set(

      0.35,

      2.95,

      side *
      1.72

    );


    bank.add(
      head
    );



    for (
      let i = 0;
      i < 9;
      i++
    ) {

      const fin =
        box(

          3.72,

          0.055,

          1.18,

          darkMetal

        );


      fin.position.set(

        0.35,

        2.64 +
        i *
        0.085,

        side *
        1.72

      );


      bank.add(
        fin
      );

    }



    const cover =
      box(

        3.15,

        0.38,

        0.78,

        silver

      );


    cover.position.set(

      0.35,

      3.45,

      side *
      1.72

    );


    bank.add(
      cover
    );


    fidelityGroup.add(
      bank
    );


  }

);

const intakePipeMat =
  new THREE.MeshStandardMaterial({

    color:
      0xb8b9b6,

    roughness:
      0.38,

    metalness:
      0.62

  });



function addTube(
  points,
  radius,
  material
) {

  const curve =
    new THREE.CatmullRomCurve3(
      points
    );


  const tube =
    new THREE.Mesh(

      new THREE.TubeGeometry(

        curve,

        28,

        radius,

        10,

        false

      ),

      material

    );


  tube.castShadow =
    true;


  tube.receiveShadow =
    true;


  // Preserve original hierarchy.
  fidelityGroup.add(
    tube
  );


  return tube;

}

[
  -1,
  1
]
.forEach(

  side => {


    [
      -1.2,
      -0.35,
      0.5,
      1.35
    ]
    .forEach(

      x => {


        addTube(

          [

            new THREE.Vector3(

              x,

              4.0,

              side *
              0.55

            ),


            new THREE.Vector3(

              x,

              4.25,

              side *
              1.05

            ),


            new THREE.Vector3(

              x,

              3.9,

              side *
              1.55

            )

          ],

          0.105,

          intakePipeMat

        );


      }

    );


  }

);



const intakePlenum =
  box(

    3.75,

    0.42,

    0.58,

    silver

  );


intakePlenum.position.set(
  0.15,
  4.22,
  0
);


fidelityGroup.add(
  intakePlenum
);


const exhaustMat =
  new THREE.MeshStandardMaterial({

    color:
      0x8c8177,

    roughness:
      0.60,

    metalness:
      0.45

  });



[
  -1,
  1
]
.forEach(

  side => {


    [
      -1.15,
      -0.25,
      0.65,
      1.55
    ]
    .forEach(

      (
        x,
        idx
      ) => {


        addTube(

          [

            new THREE.Vector3(

              x,

              2.72,

              side *
              2.18

            ),


            new THREE.Vector3(

              x +
              0.15,

              2.30,

              side *
              2.52

            ),


            new THREE.Vector3(

              1.95,

              1.75 +
              idx *
              0.06,

              side *
              2.62

            )

          ],

          0.11,

          exhaustMat

        );


      }

    );


  }

);



[
  -1,
  1
]
.forEach(

  side => {


    addTube(

      [

        new THREE.Vector3(

          1.95,

          1.9,

          side *
          2.62

        ),


        new THREE.Vector3(

          2.55,

          1.7,

          side *
          2.35

        ),


        new THREE.Vector3(

          3.0,

          1.55,

          side *
          1.65

        )

      ],

      0.18,

      exhaustMat

    );


  }

);

const sump =
  new THREE.Mesh(

    new THREE.BoxGeometry(

      3.5,

      0.72,

      2.5

    ),

    crankcaseMat

  );


sump.position.set(
  0,
  -0.05,
  0
);


sump.castShadow =
  true;


fidelityGroup.add(
  sump
);



const sumpPan =
  new THREE.Mesh(

    new THREE.BoxGeometry(

      2.9,

      0.38,

      2.05

    ),

    darkMetal

  );


sumpPan.position.set(
  0.15,
  -0.52,
  0
);


fidelityGroup.add(
  sumpPan
);


const accessory1 =
  cylinder(

    0.52,

    0.72,

    darkMetal,

    24

  );


accessory1.rotation.x =
  Math.PI / 2;


accessory1.position.set(
  2.35,
  0.55,
  -1.7
);


fidelityGroup.add(
  accessory1
);



const accessory2 =
  cylinder(

    0.42,

    0.58,

    silver,

    24

  );


accessory2.rotation.x =
  Math.PI / 2;


accessory2.position.set(
  2.65,
  0.8,
  1.55
);


fidelityGroup.add(
  accessory2
);


const hoseMat =
  new THREE.MeshStandardMaterial({

    color:
      0x22272c,

    roughness:
      0.72,

    metalness:
      0.15

  });



[
  [

    new THREE.Vector3(
      -1.8,
      4.75,
      0.65
    ),

    new THREE.Vector3(
      -2.2,
      4.25,
      1.15
    ),

    new THREE.Vector3(
      -1.65,
      3.6,
      1.65
    )

  ],


  [

    new THREE.Vector3(
      1.8,
      4.75,
      0.65
    ),

    new THREE.Vector3(
      2.25,
      4.05,
      1.05
    ),

    new THREE.Vector3(
      2.6,
      2.9,
      1.55
    )

  ],


  [

    new THREE.Vector3(
      2.3,
      0.65,
      -1.65
    ),

    new THREE.Vector3(
      1.65,
      0.2,
      -1.25
    ),

    new THREE.Vector3(
      0.5,
      -0.25,
      -0.8
    )

  ]

]
.forEach(

  path =>

    addTube(

      path,

      0.055,

      hoseMat

    )

);


[
  [-2.6, -0.45, -1.65],
  [-2.6, -0.45,  1.65],
  [ 2.5, -0.45, -1.65],
  [ 2.5, -0.45,  1.65]

]
.forEach(

  (
    [
      x,
      y,
      z
    ]
  ) => {


    const bracket =
      box(

        0.48,

        0.72,

        0.42,

        steel

      );


    bracket.position.set(
      x,
      y,
      z
    );


    bracket.rotation.z =
      THREE.MathUtils.degToRad(

        x < 0
          ? -18
          : 18

      );


    fidelityGroup.add(
      bracket
    );


  }

);


const highFidelityGroup =
  new THREE.Group();


engine.add(
  highFidelityGroup
);



const castAluminium =
  new THREE.MeshStandardMaterial({

    color:
      0x8b8e8d,

    roughness:
      0.58,

    metalness:
      0.45

  });



const oxidizedMetal =
  new THREE.MeshStandardMaterial({

    color:
      0x6f6962,

    roughness:
      0.72,

    metalness:
      0.34

  });



const hoseBlack =
  new THREE.MeshStandardMaterial({

    color:
      0x16191c,

    roughness:
      0.82,

    metalness:
      0.08

  });



const clampMetal =
  new THREE.MeshStandardMaterial({

    color:
      0xb9bec2,

    roughness:
      0.28,

    metalness:
      0.78

  });

for (
  let i = 0;
  i < 8;
  i++
) {

  const a =

    (
      i /
      8
    ) *
    Math.PI *
    2;


  const rib =
    box(

      0.50,

      0.13,

      0.16,

      darkMetal

    );


  rib.position.set(

    -4.74,

    1.05 +
    Math.cos(a) *
    1.15,

    Math.sin(a) *
    1.15

  );


  rib.rotation.x =
    a;


  highFidelityGroup.add(
    rib
  );

}
const propFlange =
  cylinder(

    0.76,

    0.18,

    castAluminium,

    40

  );


propFlange.rotation.z =
  Math.PI / 2;


propFlange.position.set(
  -5.13,
  0.70,
  0
);


highFidelityGroup.add(
  propFlange
);



for (
  let i = 0;
  i < 6;
  i++
) {

  const a =

    i *
    Math.PI *
    2 /
    6;


  const bolt =
    cylinder(

      0.055,

      0.12,

      darkMetal,

      12

    );


  bolt.rotation.z =
    Math.PI / 2;


  bolt.position.set(

    -5.24,

    0.70 +
    Math.cos(a) *
    0.48,

    Math.sin(a) *
    0.48

  );


  highFidelityGroup.add(
    bolt
  );

}



// ========================================================
// IRREGULAR EXTERNAL CASTINGS
// ========================================================

[
  [-1.75, 1.20, -1.25, 1.05, 1.15, 1.15],
  [-0.45, 1.00, -1.42, 1.25, 1.35, 0.95],
  [ 0.95, 1.10, -1.35, 1.20, 1.25, 1.05],
  [-1.55, 1.30,  1.30, 1.00, 1.10, 1.00],
  [-0.15, 1.05,  1.42, 1.30, 1.25, 0.90],
  [ 1.30, 1.15,  1.30, 1.05, 1.15, 1.00]

]
.forEach(

  (
    [
      x,
      y,
      z,
      sx,
      sy,
      sz
    ]
  ) => {


    const housing =
      new THREE.Mesh(

        new THREE.DodecahedronGeometry(
          0.65,
          0
        ),

        castAluminium

      );


    housing.position.set(
      x,
      y,
      z
    );


    housing.scale.set(
      sx,
      sy,
      sz
    );


    housing.castShadow =
      true;


    highFidelityGroup.add(
      housing
    );


  }

);

cylinderPositions.forEach(

  x => {


    const injectorBody =
      cylinder(

        0.10,

        0.48,

        darkMetal,

        16

      );


    injectorBody.position.set(
      x,
      4.48,
      0.04
    );


    highFidelityGroup.add(
      injectorBody
    );



    const injectorTop =
      cylinder(

        0.14,

        0.16,

        clampMetal,

        16

      );


    injectorTop.position.set(
      x,
      4.79,
      0.04
    );


    highFidelityGroup.add(
      injectorTop
    );


  }

);

const turboInletLip =
  new THREE.Mesh(

    new THREE.TorusGeometry(

      0.58,

      0.08,

      12,

      32

    ),

    clampMetal

  );


turboInletLip.position.set(
  3.20,
  2.10,
  0.02
);


turboInletLip.rotation.y =
  Math.PI / 2;


highFidelityGroup.add(
  turboInletLip
);



const exhaustOutlet =
  cylinder(

    0.31,

    0.78,

    oxidizedMetal,

    24

  );


exhaustOutlet.rotation.z =
  Math.PI / 2;


exhaustOutlet.position.set(
  3.75,
  1.45,
  -1.78
);


highFidelityGroup.add(
  exhaustOutlet
);

const fillerNeck =
  cylinder(

    0.12,

    0.38,

    castAluminium,

    18

  );


fillerNeck.position.set(
  1.55,
  3.95,
  -1.10
);


fillerNeck.rotation.z =
  THREE.MathUtils.degToRad(
    -18
  );


highFidelityGroup.add(
  fillerNeck
);



const fillerCap =
  cylinder(

    0.18,

    0.10,

    darkMetal,

    18

  );


fillerCap.position.set(
  1.62,
  4.15,
  -1.10
);


fillerCap.rotation.z =
  THREE.MathUtils.degToRad(
    -18
  );


highFidelityGroup.add(
  fillerCap
);

addTube(

  [

    new THREE.Vector3(
      -1.9,
      3.85,
      -1.95
    ),

    new THREE.Vector3(
      -0.8,
      4.05,
      -2.05
    ),

    new THREE.Vector3(
      0.6,
      3.95,
      -2
    ),

    new THREE.Vector3(
      1.75,
      3.65,
      -1.82
    )

  ],

  0.075,

  hoseBlack

);



[
  -1.25,
  -0.35,
  0.55,
  1.45
]
.forEach(

  x => {


    addTube(

      [

        new THREE.Vector3(
          x,
          3.90,
          -1.98
        ),

        new THREE.Vector3(
          x,
          3.62,
          -1.70
        ),

        new THREE.Vector3(
          x,
          3.40,
          -1.48
        )

      ],

      0.038,

      hoseBlack

    );


  }

);

[
  [-1.20, 4.05, -1.05],
  [ 0.50, 4.05, -1.05],
  [-1.20, 4.05,  1.05],
  [ 0.50, 4.05,  1.05],
  [ 2.60, 1.70, -2.20],
  [ 2.60, 1.70,  2.20]

]
.forEach(

  (
    [
      x,
      y,
      z
    ]
  ) => {


    const clamp =
      new THREE.Mesh(

        new THREE.TorusGeometry(

          0.15,

          0.025,

          8,

          20

        ),

        clampMetal

      );


    clamp.position.set(
      x,
      y,
      z
    );


    clamp.rotation.x =
      Math.PI / 2;


    highFidelityGroup.add(
      clamp
    );


  }

);


const junctionBox =
  box(

    0.72,

    0.52,

    0.34,

    darkMetal

  );


junctionBox.position.set(
  2.45,
  3.45,
  -1.75
);


highFidelityGroup.add(
  junctionBox
);


const x45Group =
  new THREE.Group();


engine.add(
  x45Group
);



const x45Cast =
  new THREE.MeshStandardMaterial({

    color:
      0x858887,

    roughness:
      0.64,

    metalness:
      0.40

  });



const x45DarkCast =
  new THREE.MeshStandardMaterial({

    color:
      0x505457,

    roughness:
      0.67,

    metalness:
      0.38

  });



const x45Black =
  new THREE.MeshStandardMaterial({

    color:
      0x15181b,

    roughness:
      0.78,

    metalness:
      0.12

  });



const x45Steel =
  new THREE.MeshStandardMaterial({

    color:
      0xb4b8ba,

    roughness:
      0.30,

    metalness:
      0.78

  });



const x45Exhaust =
  new THREE.MeshStandardMaterial({

    color:
      0x766b61,

    roughness:
      0.73,

    metalness:
      0.38

  });



function x45ExtrudedPlate(
  shapePoints,
  depth,
  material
) {

  const shape =
    new THREE.Shape();


  shape.moveTo(

    shapePoints[0][0],

    shapePoints[0][1]

  );


  for (
    let i = 1;
    i < shapePoints.length;
    i++
  ) {

    shape.lineTo(

      shapePoints[i][0],

      shapePoints[i][1]

    );

  }


  shape.closePath();


  const geometry =
    new THREE.ExtrudeGeometry(

      shape,

      {

        depth,

        bevelEnabled:
          true,

        bevelSize:
          0.045,

        bevelThickness:
          0.045,

        bevelSegments:
          2

      }

    );


  geometry.center();


  const mesh =
    new THREE.Mesh(

      geometry,

      material

    );


  mesh.castShadow =
    true;


  return mesh;

}

const frontCase =
  x45ExtrudedPlate(

    [

      [-1.35,-0.70],
      [-1.55, 0.10],
      [-1.25, 0.92],
      [-0.55, 1.38],
      [ 0.50, 1.32],
      [ 1.20, 0.86],
      [ 1.46, 0.05],
      [ 1.18,-0.82],
      [ 0.45,-1.18],
      [-0.55,-1.16]

    ],

    1.45,

    x45Cast

  );


frontCase.rotation.y =
  Math.PI / 2;


frontCase.position.set(
  -3.15,
  1.15,
  0
);


x45Group.add(
  frontCase
);



const rearCase =
  x45ExtrudedPlate(

    [

      [-1.15,-0.78],
      [-1.35, 0.15],
      [-1.05, 1.05],
      [-0.20, 1.38],
      [ 0.72, 1.20],
      [ 1.20, 0.55],
      [ 1.16,-0.62],
      [ 0.45,-1.10],
      [-0.52,-1.12]

    ],

    1.65,

    x45DarkCast

  );


rearCase.rotation.y =
  Math.PI / 2;


rearCase.position.set(
  2.05,
  1.25,
  0
);


x45Group.add(
  rearCase
);

[
  -1,
  1
]
.forEach(

  side => {


    for (
      let i = 0;
      i < 13;
      i++
    ) {

      const fin =
        box(

          3.55,

          0.042,

          1.30,

          x45DarkCast

        );


      fin.position.set(

        0.10,

        2.62 +
        i *
        0.073,

        side *
        1.78

      );


      x45Group.add(
        fin
      );

    }


  }

);

addTube(

  [

    new THREE.Vector3(
      2.95,
      2.35,
      0.15
    ),

    new THREE.Vector3(
      2.65,
      3.15,
      0.15
    ),

    new THREE.Vector3(
      1.85,
      3.82,
      0.10
    ),

    new THREE.Vector3(
      1.25,
      4.18,
      0.05
    )

  ],

  0.24,

  x45Steel

);

const collector =
  new THREE.Mesh(

    new THREE.CylinderGeometry(

      0.36,

      0.40,

      3.65,

      24

    ),

    x45Cast

  );


collector.rotation.z =
  Math.PI / 2;


collector.position.set(
  -0.25,
  4.22,
  0.05
);


collector.castShadow =
  true;


x45Group.add(
  collector
);
const x45TurboOuter =
  new THREE.Mesh(

    new THREE.TorusGeometry(

      0.72,

      0.24,

      16,

      40

    ),

    x45Cast

  );


x45TurboOuter.position.set(
  3.10,
  2.05,
  0
);


x45TurboOuter.rotation.y =
  Math.PI / 2;


x45Group.add(
  x45TurboOuter
);



const x45TurboCenter =
  cylinder(

    0.32,

    0.42,

    x45DarkCast,

    24

  );


x45TurboCenter.rotation.z =
  Math.PI / 2;


x45TurboCenter.position.set(
  3.10,
  2.05,
  0
);


x45Group.add(
  x45TurboCenter
);



addTube(

  [

    new THREE.Vector3(
      3.18,
      2.55,
      0.42
    ),

    new THREE.Vector3(
      3.35,
      3.05,
      0.58
    ),

    new THREE.Vector3(
      2.70,
      3.55,
      0.48
    )

  ],

  0.20,

  x45Steel

);

[
  -1,
  1
]
.forEach(

  side => {


    [
      -1.20,
      -0.30,
      0.60,
      1.50
    ]
    .forEach(

      (
        x,
        idx
      ) => {


        addTube(

          [

            new THREE.Vector3(

              x,

              2.76,

              side *
              2.20

            ),


            new THREE.Vector3(

              x +
              0.10,

              2.42,

              side *
              2.52

            ),


            new THREE.Vector3(

              1.80 +
              idx *
              0.12,

              2.02,

              side *
              2.66

            ),


            new THREE.Vector3(

              2.55,

              1.72,

              side *
              2.20

            )

          ],

          0.095,

          x45Exhaust

        );


      }

    );


  }

);

cylinderPositions.forEach(

  (
    x,
    idx
  ) => {


    addTube(

      [

        new THREE.Vector3(
          x,
          4.93,
          0.64
        ),

        new THREE.Vector3(

          x +
          (
            idx %
            2

            ? 0.10

            : -0.10
          ),

          4.70,

          0.42

        ),

        new THREE.Vector3(
          x,
          4.52,
          0.10
        )

      ],

      0.028,

      x45Steel

    );


  }

);

addTube(

  [

    new THREE.Vector3(
      -2.50,
      4.78,
      0.82
    ),

    new THREE.Vector3(
      -1.20,
      4.68,
      0.92
    ),

    new THREE.Vector3(
      0.20,
      4.70,
      0.90
    ),

    new THREE.Vector3(
      1.65,
      4.58,
      0.80
    ),

    new THREE.Vector3(
      2.55,
      4.28,
      0.72
    )

  ],

  0.035,

  x45Black

);

[
  [

    new THREE.Vector3(
      2.48,
      3.45,
      -2
    ),

    new THREE.Vector3(
      1.65,
      3.80,
      -2.05
    ),

    new THREE.Vector3(
      0.65,
      3.55,
      -1.85
    )

  ],


  [

    new THREE.Vector3(
      -1.65,
      3.62,
      -2
    ),

    new THREE.Vector3(
      -1.25,
      3.30,
      -1.88
    ),

    new THREE.Vector3(
      -1.05,
      2.95,
      -1.70
    )

  ]

]
.forEach(

  path =>
    addTube(

      path,

      0.032,

      x45Black

    )

);

rotorFan.traverse(

  object => {

    if (
      object !== rotorFan &&
      object.isMesh
    ) {

      object.visible =
        false;

    }

  }

);



const jayemPropellerGroup =
  new THREE.Group();


jayemPropellerGroup.name =
  "Jayem VRDE MALE UAV Propeller";


rotorFan.add(
  jayemPropellerGroup
);



const jayemBladeWhite =
  new THREE.MeshStandardMaterial({

    color:
      0xeeeeea,

    roughness:
      0.28,

    metalness:
      0.08

  });



const jayemBladeBlack =
  new THREE.MeshStandardMaterial({

    color:
      0x17191c,

    roughness:
      0.38,

    metalness:
      0.10

  });



const jayemBladeRed =
  new THREE.MeshStandardMaterial({

    color:
      0xd73535,

    roughness:
      0.30,

    metalness:
      0.06

  });



function createJayemBladeSegment(

  radialStart,

  radialEnd,

  chordRoot,

  chordTip,

  thicknessRoot,

  thicknessTip,

  pitchRootDeg,

  pitchTipDeg,

  material

) {

  const geometry =
    new THREE.BufferGeometry();


  const y0 =
    radialStart;


  const y1 =
    radialEnd;



  const vertices =
    new Float32Array([

      -thicknessRoot/2,
      y0,
      -chordRoot/2,

       thicknessRoot/2,
      y0,
      -chordRoot/2,

       thicknessRoot/2,
      y0,
       chordRoot/2,

      -thicknessRoot/2,
      y0,
       chordRoot/2,


      -thicknessTip/2,
      y1,
      -chordTip/2,

       thicknessTip/2,
      y1,
      -chordTip/2,

       thicknessTip/2,
      y1,
       chordTip/2,

      -thicknessTip/2,
      y1,
       chordTip/2

    ]);



  const indices = [

    0,1,2,
    0,2,3,

    4,6,5,
    4,7,6,

    0,4,5,
    0,5,1,

    1,5,6,
    1,6,2,

    2,6,7,
    2,7,3,

    3,7,4,
    3,4,0

  ];



  geometry.setAttribute(

    "position",

    new THREE.BufferAttribute(

      vertices,

      3

    )

  );


  geometry.setIndex(
    indices
  );


  geometry.computeVertexNormals();



  const segment =
    new THREE.Mesh(

      geometry,

      material

    );


  segment.rotation.y =
    THREE.MathUtils.degToRad(

      (
        pitchRootDeg +
        pitchTipDeg
      ) /
      2

    );


  segment.castShadow =
    true;


  segment.receiveShadow =
    true;


  return segment;

}



function createJayemUavBlade() {

  const blade =
    new THREE.Group();



  blade.add(

    createJayemBladeSegment(

      0.48,

      1.15,

      0.58,

      0.54,

      0.16,

      0.14,

      34,

      29,

      jayemBladeBlack

    )

  );



  blade.add(

    createJayemBladeSegment(

      1.15,

      3.22,

      0.54,

      0.25,

      0.14,

      0.07,

      29,

      12,

      jayemBladeWhite

    )

  );



  blade.add(

    createJayemBladeSegment(

      3.22,

      3.66,

      0.25,

      0.15,

      0.07,

      0.045,

      12,

      8,

      jayemBladeRed

    )

  );



  blade.rotation.z =
    THREE.MathUtils.degToRad(
      -2.5
    );


  return blade;

}



for (
  let i = 0;
  i < 3;
  i++
) {

  const pivot =
    new THREE.Group();


  pivot.rotation.x =

    i *
    Math.PI *
    2 /
    3;


  pivot.add(

    createJayemUavBlade()

  );


  jayemPropellerGroup.add(
    pivot
  );

}

const jayemSpinnerMaterial =
  new THREE.MeshStandardMaterial({

    color:
      0xf0f0ec,

    roughness:
      0.23,

    metalness:
      0.08

  });



const jayemSpinner =
  new THREE.Mesh(

    new THREE.ConeGeometry(

      0.68,

      1.48,

      48

    ),

    jayemSpinnerMaterial

  );


jayemSpinner.rotation.z =
  Math.PI / 2;


jayemSpinner.position.x =
  -0.92;


jayemSpinner.castShadow =
  true;


rotorAssembly.add(
  jayemSpinner
);



const jayemSpinnerBackplate =
  cylinder(

    0.73,

    0.18,

    jayemSpinnerMaterial,

    48

  );


jayemSpinnerBackplate.rotation.z =
  Math.PI / 2;


jayemSpinnerBackplate.position.x =
  -0.18;


rotorAssembly.add(
  jayemSpinnerBackplate
);


rotorSpinner.visible =
  false;

const fanNozzleGroup =
  new THREE.Group();


engine.add(
  fanNozzleGroup
);



const fanNozzleMaterial =
  new THREE.MeshStandardMaterial({

    color:
      0x62696e,

    roughness:
      0.42,

    metalness:
      0.58,

    transparent:
      true,

    opacity:
      0.78

  });



const fanNozzle =
  new THREE.Mesh(

    new THREE.CylinderGeometry(

      0.70,

      1.02,

      1.35,

      36,

      1,

      true

    ),

    fanNozzleMaterial

  );


fanNozzle.rotation.z =
  Math.PI / 2;


fanNozzle.position.set(
  4.55,
  0.70,
  0
);


fanNozzleGroup.add(
  fanNozzle
);



const nozzleLip =
  new THREE.Mesh(

    new THREE.TorusGeometry(

      0.70,

      0.055,

      10,

      32

    ),

    x45Steel

  );


nozzleLip.rotation.y =
  Math.PI / 2;


nozzleLip.position.set(
  5.22,
  0.70,
  0
);


fanNozzleGroup.add(
  nozzleLip
);


const nozzleFlowGeometry =
  new THREE.BufferGeometry();


const nozzleFlowCount =
  70;


const nozzleFlowPositions =
  new Float32Array(

    nozzleFlowCount *
    3

  );


const nozzleFlowSeeds =
  [];


for (
  let i = 0;
  i < nozzleFlowCount;
  i++
) {

  const seed = {

    x:
      Math.random(),

    r:
      Math.sqrt(
        Math.random()
      ),

    a:
      Math.random() *
      Math.PI *
      2

  };


  nozzleFlowSeeds.push(
    seed
  );


  nozzleFlowPositions[
    i * 3
  ] =

    5.2 +
    seed.x *
    3.2;


  nozzleFlowPositions[
    i * 3 + 1
  ] =

    0.70 +
    Math.cos(
      seed.a
    ) *
    seed.r *
    0.58;


  nozzleFlowPositions[
    i * 3 + 2
  ] =

    Math.sin(
      seed.a
    ) *
    seed.r *
    0.58;

}



nozzleFlowGeometry.setAttribute(

  "position",

  new THREE.BufferAttribute(

    nozzleFlowPositions,

    3

  )

);



const nozzleFlowMaterial =
  new THREE.PointsMaterial({

    color:
      0x78ddff,

    size:
      0.055,

    transparent:
      true,

    opacity:
      0.48,

    depthWrite:
      false,

    blending:
      THREE.AdditiveBlending

  });



const nozzleFlow =
  new THREE.Points(

    nozzleFlowGeometry,

    nozzleFlowMaterial

  );


fanNozzleGroup.add(
  nozzleFlow
);

const interactiveNodeGroups = [

  {

    name:
      "Cylinder Banks",

    object:
      cylinderGroups,

    type:
      "array"

  },


  {

    name:
      "Crankshaft",

    object:
      crankshaftGroup,

    type:
      "group"

  },


  {

    name:
      "Turbocharger",

    object:
      turboGroup,

    type:
      "group"

  },


  {

    name:
      "Rotor / Propeller",

    object:
      rotorAssembly,

    type:
      "group"

  },


  {

    name:
      "Jayem / VRDE Propeller",

    object:
      jayemPropellerGroup,

    type:
      "group"

  },


  {

    name:
      "Fuel Flow",

    object:
      fuelFlowGroup,

    type:
      "group"

  },


  {

    name:
      "Rear Flow / Nozzle",

    object:
      fanNozzleGroup,

    type:
      "group"

  },


  {

    name:
      "X4.3 Exterior Detail",

    object:
      fidelityGroup,

    type:
      "group"

  },


  {

    name:
      "X4.4 High Fidelity Detail",

    object:
      highFidelityGroup,

    type:
      "group"

  },


  {

    name:
      "X4.5 Maximum Fidelity Detail",

    object:
      x45Group,

    type:
      "group"

  }

];



const nodeBaseTransforms =
  new Map();



function rememberNodeTransform(
  object
) {

  if (
    !object ||
    nodeBaseTransforms.has(
      object
    )
  ) {

    return;

  }


  nodeBaseTransforms.set(

    object,

    {

      position:
        object.position.clone(),

      rotation:
        object.rotation.clone(),

      scale:
        object.scale.clone()

    }

  );

}



interactiveNodeGroups.forEach(

  entry => {

    if (
      entry.type ===
      "array"
    ) {

      entry.object.forEach(

        object =>
          rememberNodeTransform(
            object
          )

      );

    }

    else {

      rememberNodeTransform(
        entry.object
      );

    }

  }

);



[
  lowerCrankcase,
  upperCase,
  leftCover,
  rightCover,
  outputShaft,
  outputHub,
  flywheel,
  intakeManifold,
  exhaustMain,
  fadec,
  ecuPanel,
  starter,
  starterCap,
  oilFilter,
  fuelRail,
  airFilter,
  base,
  pedestalGroup

]
.forEach(
  rememberNodeTransform
);


const floor =
  new THREE.Mesh(

    new THREE.PlaneGeometry(

      100,

      100

    ),

    new THREE.MeshStandardMaterial({

      color:
        0x06090d,

      roughness:
        0.85,

      metalness:
        0.1

    })

  );


floor.rotation.x =
  -Math.PI / 2;


floor.position.y =
  -6.98;


floor.receiveShadow =
  true;


scene.add(
  floor
);



const grid =
  new THREE.GridHelper(

    30,

    30,

    0x1a4754,

    0x111820

  );


grid.position.y =
  -6.96;


scene.add(
  grid
);


let running =
  true;


let rpm =
  2200;


let crankAngle =
  0;


const pistonPhase = [

  0,

  Math.PI,

  Math.PI,

  0

];

const twin = {

  displacementL:
    4.2,

  cylinders:
    4,

  ambientPressureBar:
    1.013,

  ambientTempC:
    25,

  compressionRatio:
    17.5,

  health:
    96,

  rulHours:
    842,

  altitudeM:
    0,

  relativeHumidity:
    45,

  standardDensity:
    1.225,

  standardPressurePa:
    101325

};



function clamp(
  value,
  min,
  max
) {

  return Math.max(

    min,

    Math.min(
      max,
      value
    )

  );

}
function calculateEnvironment() {

  const altitude =
    clamp(

      twin.altitudeM,

      0,

      12000

    );


  const baseTempK =
    288.15;


  const lapseRate =
    0.0065;


  const g =
    9.80665;


  const gasConstant =
    287.05;


  const isaTempK =
    Math.max(

      216.65,

      baseTempK -
      lapseRate *
      altitude

    );


  const pressurePa =

    twin.standardPressurePa *

    Math.pow(

      isaTempK /
      baseTempK,

      g /
      (
        gasConstant *
        lapseRate
      )

    );


  const actualTempK =

    twin.ambientTempC +
    273.15;


  const humidityFactor =

    1 -

    (
      clamp(

        twin.relativeHumidity,

        0,

        100

      ) /
      100
    ) *

    0.012;


  const airDensity =

    (
      pressurePa /
      (
        gasConstant *
        actualTempK
      )
    )

    *

    humidityFactor;


  const densityRatio =

    airDensity /
    twin.standardDensity;


  const ambientPressureBar =

    pressurePa /
    100000;


  const pressureDeficit =

    Math.max(

      0,

      1 -

      ambientPressureBar /
      1.013

    );


  const turboCompensation =

    clamp(

      pressureDeficit *
      1.05,

      0,

      0.72

    );


  const compensatedDensity =

    clamp(

      densityRatio +

      turboCompensation *
      0.52,

      0.38,

      1.05

    );


  return {

    altitude,

    pressurePa,

    ambientPressureBar,

    airDensity,

    densityRatio,

    turboCompensation,

    compensatedDensity

  };

}

function updateDigitalTwin() {

  const normalizedRpm =
    clamp(

      rpm /
      4500,

      0,

      1

    );


  const env =
    calculateEnvironment();


  const load =

    running

    ? clamp(

        0.18 +
        normalizedRpm *
        0.72,

        0,

        1

      )

    : 0;



  const omega =

    rpm *

    2 *

    Math.PI /

    60;



  const baseTorqueNm =

    running

    ? 185 +

      235 *

      Math.sin(

        normalizedRpm *
        Math.PI *
        0.92

      )

      *

      load

    : 0;



  const availablePowerFactor =

    clamp(

      0.42 +

      env.compensatedDensity *
      0.58,

      0.45,

      1.03

    );



  const torqueNm =

    baseTorqueNm *

    availablePowerFactor;



  const powerKw =

    torqueNm *

    omega /

    1000;



  const boostBar =

    clamp(

      running

      ?

      (
        0.25 +

        0.62 *
        normalizedRpm *
        load +

        env.turboCompensation *
        0.75
      )

      :

      0,

      0,

      1.15

    );



  const mapBar =

    env.ambientPressureBar +

    boostBar;



  const intakeTempC =

    twin.ambientTempC +

    7 +

    boostBar *
    24 +

    env.turboCompensation *
    18;



  const volumetricEfficiency =

    0.78 +

    0.12 *

    Math.sin(

      normalizedRpm *
      Math.PI

    );



  const displacementM3 =

    twin.displacementL /
    1000;



  const manifoldDensity =

    env.airDensity *

    (
      mapBar /

      Math.max(

        env.ambientPressureBar,

        0.25

      )
    )

    *

    (
      (
        twin.ambientTempC +
        273.15
      )

      /

      (
        intakeTempC +
        273.15
      )
    );



  const airFlowKgS =

    displacementM3 *

    (
      rpm /
      120
    )

    *

    volumetricEfficiency *

    manifoldDensity;



  const afr =

    clamp(

      31 -
      load *
      11,

      18,

      31

    );



  const fuelKgS =

    afr > 0

    ? airFlowKgS /
      afr

    : 0;



  const fuelKgH =

    fuelKgS *
    3600;



  const chtC =

    running

    ? 105 +

      load *
      78 +

      normalizedRpm *
      20 +

      Math.max(

        0,

        twin.ambientTempC -
        25

      ) *
      0.55 +

      env.turboCompensation *
      10

    : twin.ambientTempC;



  const egtC =

    running

    ? 390 +

      load *
      285 +

      normalizedRpm *
      85 +

      env.turboCompensation *
      24

    : twin.ambientTempC;



  const oilTempC =

    running

    ? 68 +

      load *
      38 +

      normalizedRpm *
      8

    : twin.ambientTempC;



  const health =

    clamp(

      97 -

      Math.max(

        0,

        chtC -
        190

      ) *
      0.08 -

      Math.max(

        0,

        egtC -
        760

      ) *
      0.04,

      40,

      99

    );



  const setText = (
    id,
    value
  ) => {

    const el =
      pratirupElement(
        id
      );


    if (
      el
    ) {

      el.textContent =
        value;

    }

  };



  setText(

    "dtRotorRpm",

    (
      running
      ? Math.round(rpm)
      : 0
    )

    +

    " rpm"

  );


  setText(

    "dtOmega",

    omega.toFixed(1) +
    " rad/s"

  );


  setText(

    "dtTorque",

    torqueNm.toFixed(0) +
    " Nm"

  );


  setText(

    "dtPower",

    powerKw.toFixed(1) +
    " kW"

  );


  setText(

    "dtLoad",

    (
      load *
      100
    )
    .toFixed(0)

    +

    " %"

  );


  setText(

    "dtMap",

    mapBar.toFixed(2) +
    " bar"

  );


  setText(

    "dtBoost",

    boostBar.toFixed(2) +
    " bar"

  );


  setText(

    "dtAir",

    airFlowKgS.toFixed(3) +
    " kg/s"

  );


  setText(

    "dtFuel",

    fuelKgH.toFixed(1) +
    " kg/h"

  );


  setText(

    "dtCht",

    chtC.toFixed(0) +
    " °C"

  );


  setText(

    "dtEgt",

    egtC.toFixed(0) +
    " °C"

  );


  setText(

    "dtOil",

    oilTempC.toFixed(0) +
    " °C"

  );


  setText(

    "dtHealth",

    health.toFixed(0) +
    " %"

  );


  setText(

    "miniRpm",

    running
      ? Math.round(rpm)
      : 0

  );


  setText(

    "miniPower",

    powerKw.toFixed(1) +
    " kW"

  );


  setText(

    "miniCht",

    chtC.toFixed(0) +
    " °C"

  );


  setText(

    "miniEgt",

    egtC.toFixed(0) +
    " °C"

  );


  setText(

    "miniHealth",

    health.toFixed(0) +
    " %"

  );

}

function updateFuelInjectionFlow() {

  if (
    !fuelFlowVisible
  ) {

    fuelFlowGroup.visible =
      false;

    return;

  }


  fuelFlowGroup.visible =
    true;



  const env =
    calculateEnvironment();



  const time =

    performance.now() *
    0.001;



  railPulses.forEach(

    (
      pulse,
      index
    ) => {


      const t =

        (
          time *
          0.35 +

          index /
          railPulses.length

        ) %
        1;


      pulse.position.x =
        THREE.MathUtils.lerp(

          -2.5,

          2.5,

          t

        );


      pulse.material.opacity =

        running &&
        rpm > 0

        ? 0.85

        : 0.15;


    }

  );



  fuelJets.forEach(

    jet => {


      const geometry =
        jet.points.geometry;


      const positionAttr =
        geometry.getAttribute(
          "position"
        );


      const cylinderIndex =
        jet.cylinderIndex;


      const phase =

        crankAngle +

        injectionPhase[
          cylinderIndex
        ];



      const normalizedPulse =

        (
          Math.cos(
            phase
          )

          +

          1
        )

        /

        2;



      const injectionActive =

        running &&

        rpm > 0 &&

        normalizedPulse >
        0.88;



      const intensity =

        injectionActive

        ? THREE.MathUtils.smoothstep(

            normalizedPulse,

            0.88,

            1

          )

        : 0.06;



      const pistonY =

        pistons[
          cylinderIndex
        ]
        .position
        .y;



      const targetY =

        pistonY +
        0.42;



      for (
        let i = 0;
        i < positionAttr.count;
        i++
      ) {

        let localPhase =

          (
            jet.phases[i] +

            time *

            (
              0.7 +

              rpm /
              4500 *
              2
            )

          ) %
          1;



        if (
          !injectionActive
        ) {

          localPhase *=
            0.10;

        }



        const y =

          THREE.MathUtils.lerp(

            4.58,

            targetY,

            localPhase

          );



        const coneRadius =

          localPhase *

          0.34 *

          intensity;



        const angle =

          i *
          2.399963 +

          time *
          4;



        positionAttr.setXYZ(

          i,

          cylinderPositions[
            cylinderIndex
          ]

          +

          Math.cos(
            angle
          )

          *
          coneRadius *
          0.7,

          y,

          Math.sin(
            angle
          )

          *
          coneRadius *
          0.7

        );

      }



      positionAttr.needsUpdate =
        true;


      jet.points.material.opacity =

        injectionActive

        ? 0.95 *
          clamp(

            env.compensatedDensity,

            0.55,

            1

          )

        : 0.08;



      const pulse =

        injectorPulses[
          cylinderIndex
        ];


      pulse.material.opacity =

        injectionActive

        ? 0.9 *
          intensity

        : 0;



      const combustion =

        combustionGlows[
          cylinderIndex
        ];


      combustion.position.y =

        pistonY +
        0.48;



      combustion.material.opacity =

        injectionActive

        ? intensity *
          0.42

        : 0;


    }

  );

}

function animateEngine(
  delta
) {

  if (
    !running ||
    rpm <= 0
  ) {

    return;

  }


  const speed =

    rpm /
    60;


  crankAngle +=

    delta *

    speed *

    Math.PI *

    0.55;



  crankshaftGroup.rotation.x =
    crankAngle;


  outputShaft.rotation.x =
    crankAngle;


  outputHub.rotation.x =
    crankAngle;


  rotorFan.rotation.x =
    crankAngle;


  flywheel.rotation.x =
    crankAngle;



  const envForTurbo =
    calculateEnvironment();


  turboBladeGroup.rotation.z +=

    delta *

    speed *

    (
      1.8 +

      envForTurbo
        .turboCompensation *
      2.2
    );



  pistons.forEach(

    (
      piston,
      i
    ) => {


      const phase =

        crankAngle +

        pistonPhase[i];


      const pistonOffset =

        Math.cos(
          phase
        ) *
        0.38;


      piston.position.y =

        2.35 +
        pistonOffset;



      const rod =

        connectingRods[i];


      rod.position.y =

        1.45 +

        pistonOffset /
        2;


      rod.scale.y =

        1 +

        pistonOffset *
        0.12;


    }

  );

}

let exploded =
  false;


const originalPositions =
  cylinderGroups.map(

    group =>
      group.position.clone()

  );



function toggleExplodedView() {

  exploded =
    !exploded;



  cylinderGroups.forEach(

    (
      group,
      i
    ) => {


      if (
        exploded
      ) {

        group.position.x =

          originalPositions[i]
            .x *
          1.45;


        group.position.y =

          originalPositions[i]
            .y +
          1.2;

      }

      else {

        group.position.copy(

          originalPositions[i]

        );

      }


    }

  );



  const setExplodedPosition =

    (
      object,
      offset
    ) => {


      if (
        !object
      ) {

        return;

      }


      const baseTransform =

        nodeBaseTransforms.get(
          object
        );


      if (
        !baseTransform
      ) {

        return;

      }



      if (
        exploded
      ) {

        object.position.copy(

          baseTransform.position

        );


        object.position.add(
          offset
        );

      }

      else {

        object.position.copy(

          baseTransform.position

        );


        object.rotation.copy(

          baseTransform.rotation

        );


        object.scale.copy(

          baseTransform.scale

        );

      }


    };



  setExplodedPosition(

    crankshaftGroup,

    new THREE.Vector3(
      0,
      -1.6,
      0
    )

  );


  setExplodedPosition(

    turboGroup,

    new THREE.Vector3(
      2.2,
      1.2,
      1.8
    )

  );


  setExplodedPosition(

    rotorAssembly,

    new THREE.Vector3(
      -2.2,
      0,
      0
    )

  );


  setExplodedPosition(

    fuelFlowGroup,

    new THREE.Vector3(
      0,
      1.8,
      0
    )

  );


  setExplodedPosition(

    fanNozzleGroup,

    new THREE.Vector3(
      1.8,
      0.6,
      0
    )

  );


  setExplodedPosition(

    intakeManifold,

    new THREE.Vector3(
      0,
      1.8,
      -1.2
    )

  );


  setExplodedPosition(

    exhaustMain,

    new THREE.Vector3(
      0,
      1,
      1.6
    )

  );


  setExplodedPosition(

    fuelRail,

    new THREE.Vector3(
      0,
      2.2,
      0.5
    )

  );


  setExplodedPosition(

    fadec,

    new THREE.Vector3(
      2,
      0.8,
      -1.8
    )

  );


  setExplodedPosition(

    ecuPanel,

    new THREE.Vector3(
      2,
      0.8,
      -1.8
    )

  );


  setExplodedPosition(

    starter,

    new THREE.Vector3(
      -1.4,
      -0.3,
      -1.8
    )

  );


  setExplodedPosition(

    starterCap,

    new THREE.Vector3(
      -1.4,
      -0.3,
      -1.8
    )

  );


  setExplodedPosition(

    oilFilter,

    new THREE.Vector3(
      -1,
      -0.8,
      -1.5
    )

  );


  setExplodedPosition(

    airFilter,

    new THREE.Vector3(
      -2,
      1,
      -1.6
    )

  );

  setExplodedPosition(

    fidelityGroup,

    new THREE.Vector3(
      0,
      0.8,
      2.8
    )

  );


  setExplodedPosition(

    highFidelityGroup,

    new THREE.Vector3(
      0,
      1.4,
      -2.8
    )

  );


  setExplodedPosition(

    x45Group,

    new THREE.Vector3(
      2.2,
      0.5,
      0
    )

  );



  setExplodedPosition(

    lowerCrankcase,

    new THREE.Vector3(
      0,
      -0.7,
      0
    )

  );


  setExplodedPosition(

    upperCase,

    new THREE.Vector3(
      0,
      0.4,
      0
    )

  );


  setExplodedPosition(

    leftCover,

    new THREE.Vector3(
      -1.3,
      0,
      0
    )

  );


  setExplodedPosition(

    rightCover,

    new THREE.Vector3(
      1.3,
      0,
      0
    )

  );


  setExplodedPosition(

    outputShaft,

    new THREE.Vector3(
      -1.5,
      0,
      0
    )

  );


  setExplodedPosition(

    outputHub,

    new THREE.Vector3(
      -1,
      0,
      0
    )

  );


  setExplodedPosition(

    flywheel,

    new THREE.Vector3(
      1.5,
      0,
      0
    )

  );



  const button =
    pratirupElement(
      "explodeButton"
    );


  if (
    button
  ) {

    button.textContent =

      exploded

      ? "Assemble Engine"

      : "Exploded View";

  }

}

let wireframe =
  false;



function toggleWireframe() {

  wireframe =
    !wireframe;


  // IMPORTANT:
  // Traverse ENTIRE engine.
  // Includes X4.3 / X4.4 / X4.5 and every pipe/hose.
  engine.traverse(

    object => {


      if (
        !object.isMesh ||
        !object.material
      ) {

        return;

      }


      const mats =

        Array.isArray(
          object.material
        )

        ? object.material

        : [
            object.material
          ];



      mats.forEach(

        material => {


          if (
            "wireframe"
            in material
          ) {

            material.wireframe =
              wireframe;


            material.needsUpdate =
              true;

          }


        }

      );


    }

  );

}

let labelsVisible =
  false;



function toggleLabels() {

  labelsVisible =
    !labelsVisible;


  componentLabels.forEach(

    label => {

      label.visible =
        labelsVisible;

    }

  );

}

const rpmSlider =
  pratirupElement(
    "rpmSlider"
  );


const rpmText =
  pratirupElement(
    "rpmText"
  );



rpmSlider.addEventListener(

  "input",

  () => {


    rpm =
      Number(
        rpmSlider.value
      );


    rpmText.textContent =
      rpm;


  }

);



const dashboardRunButton =
  pratirupElement(
    "toggleAnimation"
  );


const dashboardExplodeButton =
  pratirupElement(
    "explodeButton"
  );


const dashboardWireframeButton =
  pratirupElement(
    "wireframeButton"
  );


const dashboardLabelsButton =
  pratirupElement(
    "labelsButton"
  );


const dashboardResetButton =
  pratirupElement(
    "resetButton"
  );


if (
  dashboardRunButton
) {

  dashboardRunButton.onclick =
    event => {


      event.preventDefault();


      running =
        !running;


      event.currentTarget
        .textContent =

        running

        ? "Stop Engine"

        : "Start Engine";


    };

}

if (
  dashboardExplodeButton
) {

  dashboardExplodeButton.onclick =
    event => {


      event.preventDefault();


      toggleExplodedView();


    };

}

if (
  dashboardWireframeButton
) {

  dashboardWireframeButton.onclick =
    event => {


      event.preventDefault();


      toggleWireframe();


      event.currentTarget
        .textContent =

        wireframe

        ? "Solid View"

        : "Wireframe";


    };

}

if (
  dashboardLabelsButton
) {

  dashboardLabelsButton.onclick =
    event => {


      event.preventDefault();


      toggleLabels();


      event.currentTarget
        .textContent =

        labelsVisible

        ? "Hide Labels"

        : "Component Labels";


    };

}

function resetPratirupCamera() {

  camera.position.set(
    11,
    8,
    14
  );


  controls.target.set(
    0,
    1.5,
    0
  );


  controls.update();

}



if (
  dashboardResetButton
) {

  dashboardResetButton.onclick =
    event => {


      event.preventDefault();


      resetPratirupCamera();


    };

}

fidelityGroup.name =
  "X4.3 Exterior Detail";


highFidelityGroup.name =
  "X4.4 High Fidelity Detail";


x45Group.name =
  "X4.5 Maximum Fidelity Detail";


fuelFlowGroup.name =
  "Fuel Injection Flow";


fanNozzleGroup.name =
  "Rear Flow / Nozzle";


rotorAssembly.name =
  "Rotor / Propeller Assembly";


crankshaftGroup.name =
  "Crankshaft Assembly";


turboGroup.name =
  "Turbocharger";



const pratirupSelection = {

  clickedMesh:
    null,

  selectedObject:
    null,

  helper:
    null,

  isolated:
    false,

  visibility:
    new Map(),

  pointerStart:
    new THREE.Vector2(),

  dragged:
    false

};



const selectionRaycaster =
  new THREE.Raycaster();


const selectionPointer =
  new THREE.Vector2();

function findExistingDashboardElement(
  ids
) {

  for (
    const id
    of ids
  ) {

    const element =
      document.getElementById(
        id
      );


    if (
      element
    ) {

      return element;

    }

  }


  return null;

}

const zoomSelectedDashboardButton =
  findExistingDashboardElement([

    "zoomSelectedButton",

    "zoomSelected",

    "selectedPartZoomButton",

    "zoomPartButton",

    "zoomSelectedBtn"

  ]);



const isolateDashboardButton =
  findExistingDashboardElement([

    "isolateButton",

    "isolateSelectedButton",

    "isolationButton",

    "isolatePartButton",

    "isolateBtn"

  ]);



const restoreIsolationDashboardButton =
  findExistingDashboardElement([

    "restoreIsolationButton",

    "restoreAllButton",

    "restorePartsButton"

  ]);



const selectedPartNameOutput =
  findExistingDashboardElement([

    "selectedPartName",

    "selectedComponentName",

    "selectedPartText"

  ]);



if (
  zoomSelectedDashboardButton
) {

  zoomSelectedDashboardButton.disabled =
    true;

}


if (
  isolateDashboardButton
) {

  isolateDashboardButton.disabled =
    true;

}

function getSelectionDisplayName(
  object
) {

  if (
    !object
  ) {

    return "Engine Component";

  }


  let current =
    object;



  while (
    current &&
    current !== engine
  ) {

    if (
      current.name &&
      current.name.trim()
    ) {

      return current.name.trim();

    }


    current =
      current.parent;

  }



  current =
    object.parent;



  while (
    current &&
    current !== engine
  ) {

    if (
      current ===
      fidelityGroup
    ) {

      return "X4.3 Detail Component";

    }


    if (
      current ===
      highFidelityGroup
    ) {

      return "X4.4 Detail Component";

    }


    if (
      current ===
      x45Group
    ) {

      return "X4.5 Detail Component";

    }


    current =
      current.parent;

  }


  return "Engine Component";

}
function clearPartSelectionHelper() {

  if (
    !pratirupSelection.helper
  ) {

    return;

  }


  scene.remove(
    pratirupSelection.helper
  );


  pratirupSelection
    .helper
    .geometry
    ?.dispose();


  pratirupSelection
    .helper
    .material
    ?.dispose();


  pratirupSelection.helper =
    null;

}
function selectPratirupPart(
  mesh
) {

  if (
    !mesh ||
    !mesh.isMesh
  ) {

    return;

  }


  pratirupSelection.clickedMesh =
    mesh;

  pratirupSelection.selectedObject =
    mesh;


  clearPartSelectionHelper();



  const helper =
    new THREE.BoxHelper(

      mesh,

      0x00d9ff

    );


  helper.material.depthTest =
    false;


  helper.material.transparent =
    true;


  helper.material.opacity =
    0.95;


  helper.renderOrder =
    1000;


  pratirupSelection.helper =
    helper;


  scene.add(
    helper
  );



  if (
    selectedPartNameOutput
  ) {

    selectedPartNameOutput.textContent =
      getSelectionDisplayName(
        mesh
      );

  }



  if (
    zoomSelectedDashboardButton
  ) {

    zoomSelectedDashboardButton.disabled =
      false;

  }



  if (
    isolateDashboardButton
  ) {

    isolateDashboardButton.disabled =
      false;

  }



  window.dispatchEvent(

    new CustomEvent(

      "pratirup:part-selected",

      {

        detail: {

          name:
            getSelectionDisplayName(
              mesh
            ),

          object:
            mesh

        }

      }

    )

  );

}

renderer.domElement.addEventListener(

  "pointerdown",

  event => {


    pratirupSelection
      .pointerStart
      .set(

        event.clientX,

        event.clientY

      );


    pratirupSelection.dragged =
      false;


  }

);



renderer.domElement.addEventListener(

  "pointermove",

  event => {


    const dx =

      event.clientX -

      pratirupSelection
        .pointerStart
        .x;


    const dy =

      event.clientY -

      pratirupSelection
        .pointerStart
        .y;


    if (
      Math.hypot(
        dx,
        dy
      ) > 5
    ) {

      pratirupSelection.dragged =
        true;

    }


  }

);



renderer.domElement.addEventListener(

  "pointerup",

  event => {


    if (
      pratirupSelection.dragged
    ) {

      return;

    }



    const rect =

      renderer.domElement
        .getBoundingClientRect();



    selectionPointer.x =

      (
        (
          event.clientX -
          rect.left
        )

        /

        rect.width

      )

      *

      2

      -

      1;



    selectionPointer.y =

      -(

        (
          event.clientY -
          rect.top
        )

        /

        rect.height

      )

      *

      2

      +

      1;



    selectionRaycaster.setFromCamera(

      selectionPointer,

      camera

    );



    const hit =

      selectionRaycaster
        .intersectObject(

          engine,

          true

        )
        .find(

          result =>

            result.object &&

            result.object.isMesh &&

            result.object.visible

        );



    if (
      hit
    ) {

      selectPratirupPart(
        hit.object
      );

    }


  }

);

function zoomToSelectedPratirupPart() {

  const selected =

    pratirupSelection
      .selectedObject;


  if (
    !selected
  ) {

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

    bounds.getCenter(

      new THREE.Vector3()

    );



  const size =

    bounds.getSize(

      new THREE.Vector3()

    );



  const maxSize =

    Math.max(

      size.x,

      size.y,

      size.z,

      0.28

    );



  const fov =

    THREE.MathUtils.degToRad(
      camera.fov
    );



  let distance =

    maxSize

    /

    (
      2 *

      Math.tan(
        fov /
        2
      )
    );


  distance *=
    3;



  let direction =

    new THREE.Vector3()
      .subVectors(

        camera.position,

        controls.target

      )
      .normalize();



  if (
    direction.lengthSq() <
    0.001
  ) {

    direction.set(
      1,
      0.55,
      1
    )
    .normalize();

  }



  camera.position
    .copy(
      center
    )
    .addScaledVector(

      direction,

      distance

    );


  controls.target.copy(
    center
  );


  controls.update();

}

function isolateSelectedPratirupPart() {

  const selected =

    pratirupSelection
      .selectedObject;


  if (
    !selected
  ) {

    return;

  }



  if (
    pratirupSelection.isolated
  ) {

    restorePratirupIsolation();

    return;

  }



  pratirupSelection
    .visibility
    .clear();



  // Save EVERY descendant visibility state.
  engine.traverse(

    object => {


      pratirupSelection
        .visibility
        .set(

          object,

          object.visible

        );


    }

  );



  engine.traverse(

    object => {


      if (
        object !== engine
      ) {

        object.visible =
          false;

      }


    }

  );



  // Show selected object/subtree.
  selected.traverse(

    object => {

      object.visible =
        true;

    }

  );



  // Keep every ancestor visible.
  let ancestor =
    selected.parent;


  while (
    ancestor
  ) {

    ancestor.visible =
      true;


    if (
      ancestor === engine
    ) {

      break;

    }


    ancestor =
      ancestor.parent;

  }



  pratirupSelection.isolated =
    true;



  if (
    isolateDashboardButton
  ) {

    isolateDashboardButton
      .textContent =
      "Restore All";

  }


  zoomToSelectedPratirupPart();

}

function restorePratirupIsolation() {

  pratirupSelection
    .visibility
    .forEach(

      (
        visible,
        object
      ) => {


        object.visible =
          visible;


      }

    );


  pratirupSelection
    .visibility
    .clear();


  pratirupSelection.isolated =
    false;



  if (
    isolateDashboardButton
  ) {

    isolateDashboardButton
      .textContent =
      "Isolate Part";

  }

}
if (
  zoomSelectedDashboardButton
) {

  zoomSelectedDashboardButton.onclick =
    event => {


      event.preventDefault();


      event.stopPropagation();


      zoomToSelectedPratirupPart();


    };

}

if (
  isolateDashboardButton
) {

  isolateDashboardButton.onclick =
    event => {


      event.preventDefault();


      event.stopPropagation();


      isolateSelectedPratirupPart();


    };

}

if (
  restoreIsolationDashboardButton
) {

  restoreIsolationDashboardButton.onclick =
    event => {


      event.preventDefault();


      event.stopPropagation();


      restorePratirupIsolation();


    };

}


function updatePratirupSelectionHelper() {

  if (
    !pratirupSelection.helper ||
    !pratirupSelection.selectedObject
  ) {

    return;

  }


  pratirupSelection.helper.visible =

    pratirupSelection
      .selectedObject
      .visible;



  if (
    pratirupSelection
      .selectedObject
      .visible
  ) {

    pratirupSelection
      .helper
      .update();

  }

}


function resizePratirupSimulation() {

  const hostSize =
    getPratirupHostSize();


  camera.aspect =

    hostSize.width /
    hostSize.height;


  camera.updateProjectionMatrix();



  renderer.setSize(

    hostSize.width,

    hostSize.height,

    false

  );


  labelRenderer.setSize(

    hostSize.width,

    hostSize.height

  );

}



window.addEventListener(

  "resize",

  resizePratirupSimulation

);



window.addEventListener(

  "pratirup:resize",

  resizePratirupSimulation

);



if (
  "ResizeObserver"
  in window
) {

  const pratirupResizeObserver =
    new ResizeObserver(

      resizePratirupSimulation

    );


  pratirupResizeObserver.observe(
    simulationHost
  );

}



resizePratirupSimulation();

const clock =
  new THREE.Clock();



function animate() {

  requestAnimationFrame(
    animate
  );


  const delta =

    Math.min(

      clock.getDelta(),

      0.05

    );



  animateEngine(
    delta
  );



  try {

    updateDigitalTwin();

    updateFuelInjectionFlow();

  }

  catch (
    error
  ) {

    const box =
      pratirupElement(
        "runtimeErrorBox"
      );


    if (
      box
    ) {

      box.style.display =
        "block";


      box.textContent =

        "Simulation warning: "

        +

        (
          error &&
          error.message

          ? error.message

          : String(error)
        );

    }

  }



  controls.update();


  updatePratirupSelectionHelper();



  renderer.render(

    scene,

    camera

  );


  labelRenderer.render(

    scene,

    camera

  );

}

window.PRATIRUP_SIMULATION = {

  scene,

  camera,

  renderer,

  labelRenderer,

  controls,

  engine,


  groups: {

    cylinders:
      cylinderGroups,

    crankshaft:
      crankshaftGroup,

    turbo:
      turboGroup,

    propeller:
      rotorAssembly,

    jayemPropeller:
      jayemPropellerGroup,

    fuelFlow:
      fuelFlowGroup,

    rearNozzle:
      fanNozzleGroup,

    fidelityX43:
      fidelityGroup,

    fidelityX44:
      highFidelityGroup,

    fidelityX45:
      x45Group

  },


  toggleExploded() {

    toggleExplodedView();

  },


  toggleWireframe() {

    toggleWireframe();

  },


  toggleLabels() {

    toggleLabels();

  },


  resetCamera() {

    resetPratirupCamera();

  },


  zoomSelected() {

    zoomToSelectedPratirupPart();

  },


  isolateSelected() {

    isolateSelectedPratirupPart();

  },


  restoreIsolation() {

    restorePratirupIsolation();

  },


  getSelectedPart() {

    return pratirupSelection
      .selectedObject;

  },


  setRPM(
    value
  ) {

    rpm =
      THREE.MathUtils.clamp(

        Number(value) ||
        0,

        0,

        4500

      );


    rpmSlider.value =
      rpm;


    rpmText.textContent =
      rpm;

  },


  run() {

    running =
      true;

  },


  stop() {

    running =
      false;

  },


  resize() {

    resizePratirupSimulation();

  }

};

window.dispatchEvent(

  new CustomEvent(

    "pratirup:simulation-ready"

  )

);
animate();



const runtimeBox =
  pratirupElement(
    "runtimeErrorBox"
  );


if (
  runtimeBox
) {

  runtimeBox.style.display =
    "none";

}


} 
if (
  document.readyState ===
  "loading"
) {

  document.addEventListener(

    "DOMContentLoaded",

    startPratirupFullDetailSimulation,

    {
      once:
        true
    }

  );

}

else {

  startPratirupFullDetailSimulation();

}
