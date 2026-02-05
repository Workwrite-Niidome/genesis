/**
 * GENESIS v3 ProceduralStructures
 *
 * Generates beautiful Japanese-themed 3D structures using proper Three.js geometry.
 * Inspired by the ethereal twilight world of super Kaguya-hime.
 *
 * Structures include:
 * - Grand Torii gate at world center
 * - Stone lanterns along cross-shaped paths
 * - Small shrine buildings at three locations
 * - Stone paths forming a cross pattern
 * - Cherry blossom trees and decorative rocks
 *
 * All emissive objects bloom via the existing UnrealBloomPass.
 * Shadows are enabled on all meshes for the existing shadow system.
 */
import * as THREE from 'three';

// ---------------------------------------------------------------------------
// Shared Materials
// ---------------------------------------------------------------------------

function createMaterials() {
  const stone = new THREE.MeshStandardMaterial({
    color: 0x888888,
    roughness: 0.9,
    metalness: 0.0,
  });

  const darkStone = new THREE.MeshStandardMaterial({
    color: 0x666666,
    roughness: 0.9,
    metalness: 0.0,
  });

  const wood = new THREE.MeshStandardMaterial({
    color: 0x3e2723,
    roughness: 0.8,
    metalness: 0.0,
  });

  const redPaint = new THREE.MeshStandardMaterial({
    color: 0x8b0000,
    roughness: 0.3,
    metalness: 0.1,
  });

  const redPaintLight = new THREE.MeshStandardMaterial({
    color: 0xa01010,
    roughness: 0.3,
    metalness: 0.1,
  });

  const emissiveAmber = new THREE.MeshStandardMaterial({
    color: 0xffe082,
    emissive: 0xffe082,
    emissiveIntensity: 2.0,
    transparent: true,
    opacity: 0.85,
    roughness: 0.4,
    metalness: 0.0,
  });

  const emissiveGold = new THREE.MeshStandardMaterial({
    color: 0xffd700,
    emissive: 0xffd700,
    emissiveIntensity: 2.5,
    roughness: 0.2,
    metalness: 0.3,
  });

  const darkTiles = new THREE.MeshStandardMaterial({
    color: 0x1b1b1b,
    roughness: 0.7,
    metalness: 0.1,
  });

  const lightStone = new THREE.MeshStandardMaterial({
    color: 0x999999,
    roughness: 0.85,
    metalness: 0.0,
  });

  const treeBark = new THREE.MeshStandardMaterial({
    color: 0x4a2c0a,
    roughness: 0.9,
    metalness: 0.0,
  });

  const cherryBlossom = new THREE.MeshStandardMaterial({
    color: 0xffb3c7,
    emissive: 0xffb3c7,
    emissiveIntensity: 0.6,
    transparent: true,
    opacity: 0.85,
    roughness: 0.6,
    metalness: 0.0,
  });

  const rockGray = new THREE.MeshStandardMaterial({
    color: 0x707070,
    roughness: 0.95,
    metalness: 0.0,
  });

  return {
    stone,
    darkStone,
    wood,
    redPaint,
    redPaintLight,
    emissiveAmber,
    emissiveGold,
    darkTiles,
    lightStone,
    treeBark,
    cherryBlossom,
    rockGray,
  };
}

type Materials = ReturnType<typeof createMaterials>;

// ---------------------------------------------------------------------------
// Helper: enable shadow on a mesh
// ---------------------------------------------------------------------------

function enableShadow(mesh: THREE.Mesh): void {
  mesh.castShadow = true;
  mesh.receiveShadow = true;
}

function enableShadowGroup(group: THREE.Group): void {
  group.traverse((child) => {
    if ((child as THREE.Mesh).isMesh) {
      enableShadow(child as THREE.Mesh);
    }
  });
}

// ---------------------------------------------------------------------------
// Structure Builders
// ---------------------------------------------------------------------------

/**
 * Grand Torii Gate at the center of the world.
 */
function createToriiGate(mats: Materials): THREE.Group {
  const group = new THREE.Group();
  group.name = 'ToriiGate';

  const pillarHeight = 12;
  const pillarRadius = 0.5;
  const segments = 20;

  // Two main pillars
  const pillarGeo = new THREE.CylinderGeometry(
    pillarRadius, pillarRadius * 1.05, pillarHeight, segments
  );

  const leftPillar = new THREE.Mesh(pillarGeo, mats.redPaint);
  leftPillar.position.set(-5, pillarHeight / 2, 0);
  group.add(leftPillar);

  const rightPillar = new THREE.Mesh(pillarGeo, mats.redPaint);
  rightPillar.position.set(5, pillarHeight / 2, 0);
  group.add(rightPillar);

  // Top beam (kasagi) - wide box with slight overhang and upward curve at ends
  const kasagiWidth = 14;
  const kasagiHeight = 0.6;
  const kasagiDepth = 1.0;

  // Main kasagi beam
  const kasagiGeo = new THREE.BoxGeometry(kasagiWidth, kasagiHeight, kasagiDepth);
  const kasagi = new THREE.Mesh(kasagiGeo, mats.redPaint);
  kasagi.position.set(0, pillarHeight + kasagiHeight / 2, 0);
  group.add(kasagi);

  // Curved end caps (slight upward tilt) - left
  const endCapGeo = new THREE.BoxGeometry(1.5, 0.4, kasagiDepth * 0.9);
  const leftEndCap = new THREE.Mesh(endCapGeo, mats.redPaintLight);
  leftEndCap.position.set(-7.5, pillarHeight + kasagiHeight + 0.3, 0);
  leftEndCap.rotation.z = 0.15;
  group.add(leftEndCap);

  // Curved end caps - right
  const rightEndCap = new THREE.Mesh(endCapGeo, mats.redPaintLight);
  rightEndCap.position.set(7.5, pillarHeight + kasagiHeight + 0.3, 0);
  rightEndCap.rotation.z = -0.15;
  group.add(rightEndCap);

  // Sub-beam below kasagi (shimagi)
  const shimagiGeo = new THREE.BoxGeometry(12, 0.35, 0.7);
  const shimagi = new THREE.Mesh(shimagiGeo, mats.redPaint);
  shimagi.position.set(0, pillarHeight - 0.3, 0);
  group.add(shimagi);

  // Secondary crossbeam (nuki) - between the pillars, lower
  const nukiGeo = new THREE.BoxGeometry(10.5, 0.35, 0.5);
  const nuki = new THREE.Mesh(nukiGeo, mats.redPaint);
  nuki.position.set(0, pillarHeight * 0.7, 0);
  group.add(nuki);

  // Golden ornament at center top
  const ornamentGeo = new THREE.SphereGeometry(0.35, 16, 16);
  const ornament = new THREE.Mesh(ornamentGeo, mats.emissiveGold);
  ornament.position.set(0, pillarHeight + kasagiHeight + 0.5, 0);
  group.add(ornament);

  // Small decorative cylindrical caps atop the pillars
  const capGeo = new THREE.CylinderGeometry(0.65, 0.55, 0.3, segments);
  const leftCap = new THREE.Mesh(capGeo, mats.redPaintLight);
  leftCap.position.set(-5, pillarHeight + 0.15, 0);
  group.add(leftCap);

  const rightCap = new THREE.Mesh(capGeo, mats.redPaintLight);
  rightCap.position.set(5, pillarHeight + 0.15, 0);
  group.add(rightCap);

  // PointLight at the golden ornament
  const ornamentLight = new THREE.PointLight(0xffbf40, 2, 20);
  ornamentLight.position.copy(ornament.position);
  ornamentLight.castShadow = true;
  ornamentLight.shadow.mapSize.width = 512;
  ornamentLight.shadow.mapSize.height = 512;
  group.add(ornamentLight);

  enableShadowGroup(group);
  return group;
}

/**
 * Stone Lantern (toro).
 */
function createStoneLantern(mats: Materials): THREE.Group {
  const group = new THREE.Group();
  group.name = 'StoneLantern';

  const seg = 16;

  // Base (wide short cylinder)
  const baseGeo = new THREE.CylinderGeometry(0.5, 0.55, 0.3, seg);
  const base = new THREE.Mesh(baseGeo, mats.stone);
  base.position.set(0, 0.15, 0);
  group.add(base);

  // Lower platform
  const platGeo = new THREE.CylinderGeometry(0.35, 0.4, 0.15, seg);
  const plat = new THREE.Mesh(platGeo, mats.stone);
  plat.position.set(0, 0.375, 0);
  group.add(plat);

  // Pillar (thin tall cylinder)
  const pillarGeo = new THREE.CylinderGeometry(0.15, 0.18, 1.5, seg);
  const pillar = new THREE.Mesh(pillarGeo, mats.stone);
  pillar.position.set(0, 1.2, 0);
  group.add(pillar);

  // Upper platform
  const upperPlatGeo = new THREE.CylinderGeometry(0.4, 0.35, 0.15, seg);
  const upperPlat = new THREE.Mesh(upperPlatGeo, mats.stone);
  upperPlat.position.set(0, 2.0, 0);
  group.add(upperPlat);

  // Light box (emissive amber)
  const lightBoxGeo = new THREE.BoxGeometry(0.55, 0.6, 0.55);
  const lightBox = new THREE.Mesh(lightBoxGeo, mats.emissiveAmber);
  lightBox.position.set(0, 2.4, 0);
  group.add(lightBox);

  // Roof platform
  const roofPlatGeo = new THREE.CylinderGeometry(0.45, 0.5, 0.1, seg);
  const roofPlat = new THREE.Mesh(roofPlatGeo, mats.darkStone);
  roofPlat.position.set(0, 2.75, 0);
  group.add(roofPlat);

  // Cap (cone on top)
  const capGeo = new THREE.ConeGeometry(0.45, 0.7, seg);
  const cap = new THREE.Mesh(capGeo, mats.darkStone);
  cap.position.set(0, 3.2, 0);
  group.add(cap);

  // Finial (small sphere at top)
  const finialGeo = new THREE.SphereGeometry(0.08, 8, 8);
  const finial = new THREE.Mesh(finialGeo, mats.stone);
  finial.position.set(0, 3.6, 0);
  group.add(finial);

  // PointLight inside the light box
  const light = new THREE.PointLight(0xffe082, 1.5, 15);
  light.position.set(0, 2.4, 0);
  light.castShadow = true;
  light.shadow.mapSize.width = 256;
  light.shadow.mapSize.height = 256;
  group.add(light);

  enableShadowGroup(group);
  return group;
}

/**
 * Small Shrine Building.
 */
function createShrine(mats: Materials): THREE.Group {
  const group = new THREE.Group();
  group.name = 'Shrine';

  // -- Stone platform base --
  const platformGeo = new THREE.BoxGeometry(8, 0.6, 6);
  const platform = new THREE.Mesh(platformGeo, mats.stone);
  platform.position.set(0, 0.3, 0);
  group.add(platform);

  // -- Steps at the front --
  const stepGeo = new THREE.BoxGeometry(3, 0.2, 0.6);
  for (let i = 0; i < 3; i++) {
    const step = new THREE.Mesh(stepGeo, mats.stone);
    step.position.set(0, 0.1 + i * 0.2, 3.3 + (2 - i) * 0.6);
    group.add(step);
  }

  const wallHeight = 3.0;
  const wallY = 0.6 + wallHeight / 2;

  // -- Back wall --
  const backWallGeo = new THREE.BoxGeometry(7.5, wallHeight, 0.2);
  const backWall = new THREE.Mesh(backWallGeo, mats.wood);
  backWall.position.set(0, wallY, -2.7);
  group.add(backWall);

  // -- Left wall --
  const sideWallGeo = new THREE.BoxGeometry(0.2, wallHeight, 5.2);
  const leftWall = new THREE.Mesh(sideWallGeo, mats.wood);
  leftWall.position.set(-3.65, wallY, 0);
  group.add(leftWall);

  // -- Right wall --
  const rightWall = new THREE.Mesh(sideWallGeo, mats.wood);
  rightWall.position.set(3.65, wallY, 0);
  group.add(rightWall);

  // -- Front wall (with sliding door gap) --
  // Two side panels leaving a gap in center
  const frontPanelGeo = new THREE.BoxGeometry(2.5, wallHeight, 0.2);
  const frontLeft = new THREE.Mesh(frontPanelGeo, mats.wood);
  frontLeft.position.set(-2.4, wallY, 2.7);
  group.add(frontLeft);

  const frontRight = new THREE.Mesh(frontPanelGeo, mats.wood);
  frontRight.position.set(2.4, wallY, 2.7);
  group.add(frontRight);

  // Lintel above the door
  const lintelGeo = new THREE.BoxGeometry(2.8, 0.4, 0.25);
  const lintel = new THREE.Mesh(lintelGeo, mats.wood);
  lintel.position.set(0, 0.6 + wallHeight - 0.2, 2.7);
  group.add(lintel);

  // -- Floor inside --
  const floorGeo = new THREE.BoxGeometry(7.2, 0.05, 5.2);
  const floorMat = new THREE.MeshStandardMaterial({
    color: 0x4a3520,
    roughness: 0.85,
    metalness: 0.0,
  });
  const floor = new THREE.Mesh(floorGeo, floorMat);
  floor.position.set(0, 0.625, 0);
  group.add(floor);

  // -- Roof (traditional hip roof using a custom shape) --
  // We approximate a hip roof with a wider base cone/pyramid
  const roofHeight = 2.5;
  const roofOverhang = 1.5;
  const roofBaseWidth = 7.5 + roofOverhang * 2;
  const roofBaseDepth = 5.2 + roofOverhang * 2;
  const roofY = 0.6 + wallHeight;

  // Build hip roof from BufferGeometry
  const roofGroup = new THREE.Group();
  roofGroup.name = 'ShrineRoof';

  // Create a proper hip roof shape using vertices
  const hw = roofBaseWidth / 2;
  const hd = roofBaseDepth / 2;
  const rh = roofHeight;
  const ridgeHalfLen = hw * 0.4; // Ridge line at top

  // Vertices for hip roof
  const roofVertices = new Float32Array([
    // Front face (triangle)
    -hw, 0, hd,
    hw, 0, hd,
    ridgeHalfLen, rh, hd * 0.15,

    hw, 0, hd,
    -hw, 0, hd,
    -ridgeHalfLen, rh, hd * 0.15,

    -ridgeHalfLen, rh, hd * 0.15,
    ridgeHalfLen, rh, hd * 0.15,
    hw, 0, hd,

    // Back face (triangle)
    hw, 0, -hd,
    -hw, 0, -hd,
    -ridgeHalfLen, rh, -hd * 0.15,

    -hw, 0, -hd,
    hw, 0, -hd,
    ridgeHalfLen, rh, -hd * 0.15,

    ridgeHalfLen, rh, -hd * 0.15,
    -ridgeHalfLen, rh, -hd * 0.15,
    hw, 0, -hd,

    // Right face (trapezoid as two triangles)
    hw, 0, hd,
    hw, 0, -hd,
    ridgeHalfLen, rh, hd * 0.15,

    hw, 0, -hd,
    ridgeHalfLen, rh, -hd * 0.15,
    ridgeHalfLen, rh, hd * 0.15,

    // Left face (trapezoid as two triangles)
    -hw, 0, -hd,
    -hw, 0, hd,
    -ridgeHalfLen, rh, hd * 0.15,

    -hw, 0, hd,
    -ridgeHalfLen, rh, hd * 0.15,
    -ridgeHalfLen, rh, -hd * 0.15,

    -hw, 0, -hd,
    -ridgeHalfLen, rh, hd * 0.15,
    -ridgeHalfLen, rh, -hd * 0.15,

    // Top ridge face (connects front ridge to back ridge)
    -ridgeHalfLen, rh, hd * 0.15,
    ridgeHalfLen, rh, hd * 0.15,
    ridgeHalfLen, rh, -hd * 0.15,

    -ridgeHalfLen, rh, hd * 0.15,
    ridgeHalfLen, rh, -hd * 0.15,
    -ridgeHalfLen, rh, -hd * 0.15,
  ]);

  const roofGeo = new THREE.BufferGeometry();
  roofGeo.setAttribute('position', new THREE.BufferAttribute(roofVertices, 3));
  roofGeo.computeVertexNormals();

  const roof = new THREE.Mesh(roofGeo, mats.darkTiles);
  roof.position.set(0, roofY, 0);
  roofGroup.add(roof);

  // Underside of roof overhang (flat bottom)
  const roofBottomGeo = new THREE.BoxGeometry(roofBaseWidth, 0.1, roofBaseDepth);
  const roofBottom = new THREE.Mesh(roofBottomGeo, mats.wood);
  roofBottom.position.set(0, roofY + 0.05, 0);
  roofGroup.add(roofBottom);

  group.add(roofGroup);

  // -- Interior glow (warm amber PointLight) --
  const interiorLight = new THREE.PointLight(0xffe082, 0.8, 12);
  interiorLight.position.set(0, 2.0, 0.5);
  interiorLight.castShadow = false; // interior light, no shadow needed
  group.add(interiorLight);

  // -- Small altar inside (a simple box with emissive) --
  const altarGeo = new THREE.BoxGeometry(1.0, 0.6, 0.5);
  const altar = new THREE.Mesh(altarGeo, mats.wood);
  altar.position.set(0, 0.95, -1.8);
  group.add(altar);

  // Altar offering (small emissive sphere)
  const offeringGeo = new THREE.SphereGeometry(0.15, 12, 12);
  const offering = new THREE.Mesh(offeringGeo, mats.emissiveGold);
  offering.position.set(0, 1.35, -1.8);
  group.add(offering);

  enableShadowGroup(group);

  // Floor only receives shadows
  floor.castShadow = false;
  platform.castShadow = false;
  platform.receiveShadow = true;

  return group;
}

/**
 * Create stone path slabs forming a cross from the torii gate.
 */
function createStonePaths(mats: Materials): THREE.Group {
  const group = new THREE.Group();
  group.name = 'StonePaths';

  const slabWidth = 1.8;
  const slabHeight = 0.08;
  const slabDepth = 1.0;
  const gap = 0.15;
  const pathLength = 40;

  const slabGeo = new THREE.BoxGeometry(slabWidth, slabHeight, slabDepth);
  const slabGeoSmall = new THREE.BoxGeometry(slabWidth * 0.85, slabHeight, slabDepth * 0.85);

  // Path along X axis (positive and negative)
  for (let x = -pathLength; x <= pathLength; x += slabDepth + gap) {
    // Skip the very center (torii gate sits there)
    if (Math.abs(x) < 2 && Math.abs(x) < 2) continue;

    const isAlternate = Math.floor(Math.abs(x) / (slabDepth + gap)) % 2 === 0;
    const geo = isAlternate ? slabGeo : slabGeoSmall;
    const mat = isAlternate ? mats.stone : mats.lightStone;

    const slab = new THREE.Mesh(geo, mat);
    slab.position.set(x, 0.01 + slabHeight / 2, 0);
    slab.receiveShadow = true;
    slab.castShadow = false;
    group.add(slab);
  }

  // Path along Z axis (positive and negative)
  for (let z = -pathLength; z <= pathLength; z += slabDepth + gap) {
    // Skip center and the X-path overlap area
    if (Math.abs(z) < 2) continue;

    const isAlternate = Math.floor(Math.abs(z) / (slabDepth + gap)) % 2 === 0;
    const geo = isAlternate ? slabGeo : slabGeoSmall;
    const mat = isAlternate ? mats.stone : mats.lightStone;

    const slab = new THREE.Mesh(geo, mat);
    // Rotate for the Z-direction path
    slab.position.set(0, 0.01 + slabHeight / 2, z);
    slab.rotation.y = Math.PI / 2;
    slab.receiveShadow = true;
    slab.castShadow = false;
    group.add(slab);
  }

  // Center intersection - a larger decorative slab
  const centerGeo = new THREE.CylinderGeometry(1.5, 1.5, 0.1, 24);
  const center = new THREE.Mesh(centerGeo, mats.lightStone);
  center.position.set(0, 0.06, 0);
  center.receiveShadow = true;
  group.add(center);

  return group;
}

/**
 * Cherry blossom tree.
 */
function createCherryTree(mats: Materials, height?: number): THREE.Group {
  const group = new THREE.Group();
  group.name = 'CherryTree';

  const treeHeight = height ?? (4 + Math.random() * 2);
  const trunkRadius = 0.2 + Math.random() * 0.1;

  // Trunk
  const trunkGeo = new THREE.CylinderGeometry(
    trunkRadius * 0.7, trunkRadius, treeHeight, 12
  );
  const trunk = new THREE.Mesh(trunkGeo, mats.treeBark);
  trunk.position.set(0, treeHeight / 2, 0);
  group.add(trunk);

  // Main canopy (large sphere)
  const canopyRadius = 2.0 + Math.random() * 0.8;
  const canopyGeo = new THREE.SphereGeometry(canopyRadius, 16, 12);
  const canopy = new THREE.Mesh(canopyGeo, mats.cherryBlossom);
  canopy.position.set(0, treeHeight + canopyRadius * 0.5, 0);
  // Slightly flatten the canopy
  canopy.scale.set(1, 0.7, 1);
  group.add(canopy);

  // Secondary canopy cluster (offset)
  const subCanopyRadius = canopyRadius * 0.6;
  const subCanopyGeo = new THREE.SphereGeometry(subCanopyRadius, 12, 10);

  const subCanopy1 = new THREE.Mesh(subCanopyGeo, mats.cherryBlossom);
  subCanopy1.position.set(1.2, treeHeight + canopyRadius * 0.3, 0.8);
  subCanopy1.scale.set(1, 0.75, 1);
  group.add(subCanopy1);

  const subCanopy2 = new THREE.Mesh(subCanopyGeo, mats.cherryBlossom);
  subCanopy2.position.set(-1.0, treeHeight + canopyRadius * 0.2, -0.6);
  subCanopy2.scale.set(1, 0.75, 1);
  group.add(subCanopy2);

  // A branch or two extending outward
  const branchGeo = new THREE.CylinderGeometry(0.04, 0.08, 2.0, 8);
  const branch1 = new THREE.Mesh(branchGeo, mats.treeBark);
  branch1.position.set(0.8, treeHeight * 0.8, 0.4);
  branch1.rotation.z = -Math.PI / 4;
  group.add(branch1);

  const branch2 = new THREE.Mesh(branchGeo, mats.treeBark);
  branch2.position.set(-0.6, treeHeight * 0.75, -0.3);
  branch2.rotation.z = Math.PI / 5;
  branch2.rotation.x = Math.PI / 6;
  group.add(branch2);

  enableShadowGroup(group);
  return group;
}

/**
 * Decorative rock.
 */
function createRock(mats: Materials, scale?: number): THREE.Group {
  const group = new THREE.Group();
  group.name = 'Rock';

  const s = scale ?? (0.5 + Math.random() * 1.5);
  const rockGeo = new THREE.DodecahedronGeometry(s, 1);
  const rock = new THREE.Mesh(rockGeo, mats.rockGray);
  rock.position.set(0, s * 0.4, 0);
  // Random squash/stretch for organic feel
  rock.scale.set(
    0.8 + Math.random() * 0.4,
    0.6 + Math.random() * 0.4,
    0.8 + Math.random() * 0.4
  );
  rock.rotation.set(
    Math.random() * 0.3,
    Math.random() * Math.PI * 2,
    Math.random() * 0.3
  );
  group.add(rock);

  enableShadowGroup(group);
  return group;
}

// ---------------------------------------------------------------------------
// Main Class
// ---------------------------------------------------------------------------

export class ProceduralStructures {
  private scene: THREE.Scene;
  private rootGroup: THREE.Group;
  private materials: Materials;
  private lights: THREE.PointLight[] = [];

  constructor(scene: THREE.Scene) {
    this.scene = scene;
    this.rootGroup = new THREE.Group();
    this.rootGroup.name = 'ProceduralStructures';
    this.materials = createMaterials();

    this.generate();

    this.scene.add(this.rootGroup);
  }

  private generate(): void {
    this.buildToriiGate();
    this.buildStoneLanterns();
    this.buildShrines();
    this.buildStonePaths();
    this.buildCherryTrees();
    this.buildRocks();
  }

  // -- Torii Gate --

  private buildToriiGate(): void {
    const torii = createToriiGate(this.materials);
    torii.position.set(0, 0, 0);
    this.rootGroup.add(torii);
  }

  // -- Stone Lanterns --

  private buildStoneLanterns(): void {
    // Along X-axis path
    const xPositions = [-30, -20, -10, 10, 20, 30];
    for (const x of xPositions) {
      // Lantern on positive-Z side of path
      const lantern1 = createStoneLantern(this.materials);
      lantern1.position.set(x, 0, 2.5);
      this.rootGroup.add(lantern1);

      // Lantern on negative-Z side of path
      const lantern2 = createStoneLantern(this.materials);
      lantern2.position.set(x, 0, -2.5);
      this.rootGroup.add(lantern2);
    }

    // Along Z-axis path
    const zPositions = [-30, -20, -10, 10, 20, 30];
    for (const z of zPositions) {
      // Lantern on positive-X side of path
      const lantern1 = createStoneLantern(this.materials);
      lantern1.position.set(2.5, 0, z);
      this.rootGroup.add(lantern1);

      // Lantern on negative-X side of path
      const lantern2 = createStoneLantern(this.materials);
      lantern2.position.set(-2.5, 0, z);
      this.rootGroup.add(lantern2);
    }
  }

  // -- Shrines --

  private buildShrines(): void {
    const locations: [number, number, number][] = [
      [25, 0, 25],
      [-25, 0, -20],
      [-20, 0, 30],
    ];

    const rotations = [
      Math.PI,       // Facing toward origin (south)
      0,             // Facing toward origin (north)
      Math.PI * 0.5, // Facing toward origin (west)
    ];

    for (let i = 0; i < locations.length; i++) {
      const shrine = createShrine(this.materials);
      shrine.position.set(locations[i][0], locations[i][1], locations[i][2]);
      shrine.rotation.y = rotations[i];
      this.rootGroup.add(shrine);
    }
  }

  // -- Stone Paths --

  private buildStonePaths(): void {
    const paths = createStonePaths(this.materials);
    this.rootGroup.add(paths);
  }

  // -- Cherry Blossom Trees --

  private buildCherryTrees(): void {
    // Place trees near shrines and along paths
    const treePositions: [number, number][] = [
      [22, 20],   // Near shrine 1
      [28, 28],   // Near shrine 1
      [-28, -17], // Near shrine 2
      [-23, -24], // Near shrine 2
      [-17, 33],  // Near shrine 3
      [-24, 27],  // Near shrine 3
      [15, -8],   // Along path
      [-12, 7],   // Along path
    ];

    for (const [x, z] of treePositions) {
      const tree = createCherryTree(this.materials);
      tree.position.set(x, 0, z);
      // Random rotation for variety
      tree.rotation.y = Math.random() * Math.PI * 2;
      this.rootGroup.add(tree);
    }
  }

  // -- Decorative Rocks --

  private buildRocks(): void {
    // Scatter rocks near paths and structures
    const rockPositions: [number, number, number][] = [
      [4, 0, 5],
      [-3, 0, -4],
      [8, 0, 2],
      [-7, 0, -3],
      [15, 0, 3],
      [-14, 0, -2],
      [3, 0, -15],
      [-2, 0, 12],
      [27, 0, 22],
      [-27, 0, -22],
      [-22, 0, 28],
      [30, 0, -5],
      [-30, 0, 8],
      [5, 0, 30],
      [-4, 0, -28],
    ];

    for (const [x, y, z] of rockPositions) {
      const scale = 0.3 + Math.random() * 1.2;
      const rock = createRock(this.materials, scale);
      rock.position.set(x, y, z);
      this.rootGroup.add(rock);
    }

    // Larger feature rocks near the torii gate
    const featureRock1 = createRock(this.materials, 1.8);
    featureRock1.position.set(-8, 0, 3);
    this.rootGroup.add(featureRock1);

    const featureRock2 = createRock(this.materials, 1.5);
    featureRock2.position.set(9, 0, -2);
    this.rootGroup.add(featureRock2);
  }

  // -- Cleanup --

  dispose(): void {
    // Traverse and dispose all geometries and materials
    this.rootGroup.traverse((child) => {
      if ((child as THREE.Mesh).isMesh) {
        const mesh = child as THREE.Mesh;
        mesh.geometry.dispose();
        if (Array.isArray(mesh.material)) {
          for (const mat of mesh.material) {
            mat.dispose();
          }
        } else {
          mesh.material.dispose();
        }
      }
    });

    // Remove from scene
    this.scene.remove(this.rootGroup);

    // Dispose shared materials
    for (const mat of Object.values(this.materials)) {
      (mat as THREE.Material).dispose();
    }
  }
}
