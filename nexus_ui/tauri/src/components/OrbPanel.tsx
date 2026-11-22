import { useEffect, useRef } from "react";
import { useOrbSettings, type OrbStyle, type OrbState } from "../stores/orbSettings";
import * as B from "@babylonjs/core";



const stateConfig: Record<OrbState, { speed: number; pulse: number }> = {
  SLEEP: { speed: 0.35, pulse: 0.025 },
  WAKE_UP: { speed: 1.7, pulse: 0.09 },
  LISTENING: { speed: 0.85, pulse: 0.05 },
  THINKING: { speed: 2.3, pulse: 0.075 },
  EXECUTING: { speed: 2.9, pulse: 0.11 }
};


function drawPlasma(
  ctx: CanvasRenderingContext2D,
  time: number,
  primary: string,
  secondary: string,
  intensity: number
) {
  const w = 512;
  const h = 256;
  const t = time;

  const rgb = (hex: string) => {
    const value = hex.replace("#", "");
    return {
      r: parseInt(value.slice(0, 2), 16),
      g: parseInt(value.slice(2, 4), 16),
      b: parseInt(value.slice(4, 6), 16)
    };
  };

  const a = rgb(primary);
  const b = rgb(secondary);

  const colorA = `rgb(${a.r},${a.g},${a.b})`;
  const colorB = `rgb(${b.r},${b.g},${b.b})`;

  ctx.clearRect(0, 0, w, h);

  const background = ctx.createRadialGradient(
    w * 0.5, h * 0.5, 8,
    w * 0.5, h * 0.5, 190
  );
  background.addColorStop(0, "#100d20");
  background.addColorStop(0.45, colorA);
  background.addColorStop(1, "#080610");

  ctx.fillStyle = background;
  ctx.fillRect(0, 0, w, h);

  ctx.globalCompositeOperation = "screen";

  // Вращающиеся энергетические вихри.
  for (let i = 0; i < 7; i++) {
    const angle = t * (0.22 + i * 0.035) + i * 1.7;
    const x = w * 0.5 + Math.cos(angle) * (45 + i * 12);
    const y = h * 0.5 + Math.sin(angle * 1.3) * (25 + i * 8);

    const radius = 35 + Math.sin(t * 1.8 + i) * 13;

    const gradient = ctx.createRadialGradient(
      x, y, 0, x, y, radius
    );

    gradient.addColorStop(0, "#ffffff");
    gradient.addColorStop(0.12, colorB);
    gradient.addColorStop(0.48, colorA);
    gradient.addColorStop(1, "transparent");

    ctx.globalAlpha = 0.35 + intensity * 0.25;
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fill();
  }

  // Органические плазменные потоки.
  for (let i = 0; i < 32; i++) {
    const phase = i * 0.61;
    const y = (i / 32) * h;

    ctx.beginPath();

    for (let x = 0; x <= w; x += 8) {
      const wave =
        Math.sin(x * 0.018 + t * 1.8 + phase) * 15 +
        Math.sin(x * 0.041 - t * 1.2 + phase * 2) * 8 +
        Math.sin(t + phase) * 10;

      const yy = y + wave;

      if (x === 0) ctx.moveTo(x, yy);
      else ctx.lineTo(x, yy);
    }

    ctx.strokeStyle = i % 4 === 0 ? "#ffffff" : colorB;
    ctx.lineWidth = i % 4 === 0 ? 1.8 : 0.7 + intensity;
    ctx.globalAlpha = 0.09 + Math.sin(t * 2 + phase) * 0.055;
    ctx.shadowColor = colorB;
    ctx.shadowBlur = 12 + intensity * 8;
    ctx.stroke();
  }

  // Горячие энергетические прожилки.
  for (let i = 0; i < 13; i++) {
    const x = (i * 47 + t * (18 + i * 2)) % (w + 100) - 50;
    const y = 25 + ((i * 71) % 205);
    const length = 30 + (i % 4) * 20;

    ctx.beginPath();
    ctx.moveTo(x, y);

    ctx.bezierCurveTo(
      x + Math.sin(t * 2 + i) * 18,
      y - length * 0.4,
      x + Math.cos(t + i) * 24,
      y + length * 0.5,
      x + Math.sin(t * 1.4 + i) * 12,
      y + length
    );

    ctx.strokeStyle = i % 3 === 0 ? "#ffffff" : colorB;
    ctx.lineWidth = i % 3 === 0 ? 2.2 : 1.1;
    ctx.globalAlpha = 0.25 + intensity * 0.25;
    ctx.shadowColor = colorB;
    ctx.shadowBlur = 16;
    ctx.stroke();
  }

  // Центральное раскалённое ядро.
  const core = ctx.createRadialGradient(
    w * 0.5, h * 0.5, 2,
    w * 0.5, h * 0.5, 105
  );

  core.addColorStop(0, "rgba(255,255,255,0.95)");
  core.addColorStop(0.12, colorB);
  core.addColorStop(0.42, colorA);
  core.addColorStop(1, "transparent");

  ctx.globalAlpha = 0.28 + intensity * 0.18;
  ctx.fillStyle = core;
  ctx.fillRect(0, 0, w, h);

  ctx.globalAlpha = 1;
  ctx.globalCompositeOperation = "source-over";
  ctx.shadowBlur = 0;
}

function OrbScene({
  style, state, primary, secondary, glow, speed, particleCount, scale
}: {
  style: OrbStyle;
  state: OrbState;
  primary: string;
  secondary: string;
  glow: number;
  speed: number;
  particleCount: number;
  scale: number;
}) {
  const mountRef = useRef<HTMLDivElement>(null);
  const propsRef = useRef({ style, state, primary, secondary, glow, speed, particleCount, scale });

  propsRef.current = { style, state, primary, secondary, glow, speed, particleCount, scale };

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    let disposed = false;
    let engine: B.AbstractEngine | null = null;
    let scene: B.Scene | null = null;
    let resizeObserver: ResizeObserver | null = null;

    const start = async () => {
      const canvas = document.createElement("canvas");
      canvas.className = "nexus-babylon-canvas";
      canvas.style.width = "100%";
      canvas.style.height = "100%";
      canvas.style.display = "block";
      mount.appendChild(canvas);

      try {
        if (await B.WebGPUEngine.IsSupportedAsync) {
          const webgpu = new B.WebGPUEngine(canvas, {
            antialias: true,
            adaptToDeviceRatio: true
          });
          await webgpu.initAsync();
          if (disposed) {
            webgpu.dispose();
            return;
          }
          engine = webgpu;
        } else {
          throw new Error("WebGPU unavailable");
        }
      } catch {
        if (disposed) return;
        try {
          engine = new B.Engine(canvas, true, {
            preserveDrawingBuffer: false,
            stencil: true,
            powerPreference: "high-performance"
          }, true);
        } catch {
          mount.innerHTML = '<div class="orb-webgl-error">WebGPU и WebGL2 недоступны</div>';
          return;
        }
      }

      if (disposed || !engine) {
        engine?.dispose();
        return;
      }

      engine.setHardwareScalingLevel(Math.max(1, window.devicePixelRatio || 1) > 1.5 ? 1.25 : 1);

      scene = new B.Scene(engine);
      scene.clearColor = new B.Color4(0, 0, 0, 0);

      const camera = new B.ArcRotateCamera(
        "orb-camera",
        -Math.PI / 2,
        Math.PI / 2,
        4.1,
        B.Vector3.Zero(),
        scene
      );
      camera.fov = 0.72;
      camera.minZ = 0.1;
      camera.maxZ = 100;
      camera.lowerRadiusLimit = 4.1;
      camera.upperRadiusLimit = 4.1;
      camera.inputs.clear();
      scene.activeCamera = camera;

      const glowLayer = new B.GlowLayer("orb-glow", scene, {
        blurKernelSize: 48
      });
      glowLayer.intensity = 0.8;

      const ambient = new B.HemisphericLight(
        "orb-ambient",
        new B.Vector3(0, 1, 0),
        scene
      );
      ambient.intensity = 0.65;

      const keyLight = new B.PointLight(
        "orb-key-light",
        new B.Vector3(-2, 2.5, 3),
        scene
      );
      keyLight.intensity = 2.2;

      const rimLight = new B.PointLight(
        "orb-rim-light",
        new B.Vector3(2, -1.5, -2),
        scene
      );
      rimLight.intensity = 2.5;

      const root = new B.TransformNode("orb-root", scene);

      const bodyMaterial = new B.PBRMaterial("orb-body-material", scene);
      bodyMaterial.albedoColor = B.Color3.FromHexString(
        style === "VERITY" ? "#FFE51D" : primary
      );
      bodyMaterial.metallic = 0.28;
      bodyMaterial.roughness = 0.3;
      bodyMaterial.emissiveColor = B.Color3.FromHexString(
        style === "VERITY" ? "#8F6500" : primary
      ).scale(0.45);
      bodyMaterial.clearCoat.isEnabled = true;
      bodyMaterial.clearCoat.intensity = 0.8;

      const body = B.MeshBuilder.CreateSphere("orb-core", {
        diameter: 2,
        segments: 96
      }, scene);
      body.parent = root;
      body.material = bodyMaterial;
      // Процедурная текстура энергетической плазмы.
      const plasmaTexture = new B.DynamicTexture(
        "orb-plasma-texture",
        { width: 512, height: 256 },
        scene,
        false,
        B.Texture.TRILINEAR_SAMPLINGMODE
      );

      plasmaTexture.wrapU = B.Texture.WRAP_ADDRESSMODE;
      plasmaTexture.wrapV = B.Texture.CLAMP_ADDRESSMODE;

      const plasmaContext = plasmaTexture.getContext() as unknown as CanvasRenderingContext2D;

      bodyMaterial.emissiveTexture = plasmaTexture;
      bodyMaterial.emissiveColor = B.Color3.White().scale(0.9);

      let lastPlasmaUpdate = 0;

      const shellMaterial = new B.StandardMaterial("orb-shell-material", scene);
      shellMaterial.diffuseColor = B.Color3.FromHexString(primary);
      shellMaterial.emissiveColor = B.Color3.FromHexString(secondary).scale(0.65);
      shellMaterial.alpha = style === "HOLOGRAM" ? 0.18 : 0.12;
      shellMaterial.wireframe = style === "HOLOGRAM";
      shellMaterial.disableLighting = true;

      const shell = B.MeshBuilder.CreateSphere("orb-shell", {
        diameter: 2.045,
        segments: 64
      }, scene);
      shell.parent = root;
      shell.material = shellMaterial;
            // Независимая геометрия визуальных режимов.
      const energyGroup = new B.TransformNode("energy-lightning-group", scene);
      energyGroup.parent = root;

      const energyMaterials: B.StandardMaterial[] = [];
      const energyArcs: B.Mesh[] = [];

      const energyMaterial = new B.StandardMaterial("energy-bolt-material", scene);
      energyMaterial.diffuseColor = B.Color3.White();
      energyMaterial.emissiveColor = B.Color3.FromHexString(primary).scale(2.8);
      energyMaterial.disableLighting = true;
      energyMaterials.push(energyMaterial);

      const random = (seed: number) => {
        const x = Math.sin(seed * 127.1 + 311.7) * 43758.5453;
        return x - Math.floor(x);
      };

      const spherePoint = (u: number, v: number, radius: number) => {
        const theta = u * Math.PI * 2;
        const phi = v * Math.PI;
        return new B.Vector3(
          radius * Math.sin(phi) * Math.cos(theta),
          radius * Math.cos(phi),
          radius * Math.sin(phi) * Math.sin(theta)
        );
      };

      // Главные молнии и их ответвления.
      for (let arc = 0; arc < 22; arc++) {
        const u = random(arc + 1);
        const v = 0.18 + random(arc + 50) * 0.64;
        const points: B.Vector3[] = [];
        const count = 15;
        const start = spherePoint(u, v, 1.025);
        const end = spherePoint(u + 0.12 + random(arc + 90) * 0.24,
          Math.max(0.08, Math.min(0.92, v + (random(arc + 120) - 0.5) * 0.48)), 1.025);

        for (let j = 0; j <= count; j++) {
          const p = j / count;
          const base = B.Vector3.Lerp(start, end, p);
          const offset = new B.Vector3(
            (random(arc * 100 + j) - 0.5) * 0.13,
            (random(arc * 200 + j) - 0.5) * 0.13,
            (random(arc * 300 + j) - 0.5) * 0.13
          );
          points.push(base.add(offset));
        }

        const bolt = B.MeshBuilder.CreateTube("energy-bolt-" + arc, {
          path: points,
          radius: arc % 4 === 0 ? 0.009 : 0.004,
          tessellation: 5
        }, scene);
        bolt.parent = energyGroup;
        bolt.material = energyMaterial;
        bolt.isPickable = false;
        energyArcs.push(bolt);

        if (arc % 2 === 0) {
          const branchStart = points[5 + (arc % 5)];
          const branch: B.Vector3[] = [branchStart];
          for (let j = 1; j <= 6; j++) {
            const p = branchStart.add(new B.Vector3(
              (random(arc * 500 + j) - 0.5) * j * 0.055,
              (random(arc * 600 + j) - 0.5) * j * 0.07,
              (random(arc * 700 + j) - 0.5) * j * 0.055
            ));
            branch.push(p.normalize().scale(1.035));
          }
          const fork = B.MeshBuilder.CreateTube("energy-fork-" + arc, {
            path: branch,
            radius: 0.003,
            tessellation: 4
          }, scene);
          fork.parent = energyGroup;
          fork.material = energyMaterial;
          fork.isPickable = false;
          energyArcs.push(fork);
        }
      }

      // Голографические сканирующие кольца.
      const hologramGroup = new B.TransformNode("hologram-projection", scene);
      hologramGroup.parent = root;
      const hologramRings: B.Mesh[] = [];

      for (let i = 0; i < 7; i++) {
        const ring = B.MeshBuilder.CreateTorus("hologram-scan-" + i, {
          diameter: 2.02 + i * 0.012,
          thickness: 0.0035,
          tessellation: 128
        }, scene);
        ring.parent = hologramGroup;
        ring.position.y = -0.78 + i * 0.26;
        ring.material = shellMaterial;
        ring.isPickable = false;
        hologramRings.push(ring);
      }

      // NEXUS ORB SYSTEMS — independent procedural visual modes
      // ============================================================

      type DynamicSurface = {
        mesh: B.Mesh;
        base: number[];
        mode: OrbStyle;
        phase: number;
        amplitude: number;
      };

      const dynamicSurfaces: DynamicSurface[] = [];

      const registerSurface = (
        mesh: B.Mesh,
        mode: OrbStyle,
        phase: number,
        amplitude: number
      ) => {
        const data = mesh.getVerticesData(B.VertexBuffer.PositionKind);
        if (data && mesh.getIndices()) {
          dynamicSurfaces.push({
            mesh,
            base: Array.from(data),
            mode,
            phase,
            amplitude
          });
        }
      };

      // HOLOGRAM: цифровые меридианы и горизонтальная проекционная сетка.
      const hologramGrid = new B.TransformNode("hologram-digital-grid", scene);
      hologramGrid.parent = root;

      const hologramLines: B.LinesMesh[] = [];

      for (let i = 0; i < 16; i++) {
        const points: B.Vector3[] = [];
        const angle = (i / 16) * Math.PI * 2;

        for (let j = 0; j <= 64; j++) {
          const phi = 0.08 + (j / 64) * (Math.PI - 0.16);
          points.push(new B.Vector3(
            1.012 * Math.sin(phi) * Math.cos(angle),
            1.012 * Math.cos(phi),
            1.012 * Math.sin(phi) * Math.sin(angle)
          ));
        }

        const line = B.MeshBuilder.CreateLines("holo-meridian-" + i, {
          points,
          updatable: false
        }, scene);

        line.color = B.Color3.FromHexString(i % 3 === 0 ? "#FFFFFF" : secondary);
        line.alpha = 0.24;
        line.parent = hologramGrid;
        line.isPickable = false;
        hologramLines.push(line);
      }
      // FLUID: деформируемая плазменная поверхность и текучие слои.
      const fluidGroup = new B.TransformNode("fluid-plasma-system", scene);
      fluidGroup.parent = root;

      registerSurface(body, "FLUID", 0, 0.065);

      const fluidLayers: B.Mesh[] = [];

      for (let i = 0; i < 3; i++) {
        const layer = B.MeshBuilder.CreateSphere("fluid-shell-" + i, {
          diameter: 2.035 + i * 0.105,
          segments: 56
        }, scene);

        const material = new B.StandardMaterial("fluid-shell-material-" + i, scene);
        material.diffuseColor = B.Color3.FromHexString(i % 2 ? secondary : primary);
        material.emissiveColor = B.Color3.FromHexString(i % 2 ? primary : secondary).scale(1.3);
        material.alpha = 0.045 + i * 0.018;
        material.disableLighting = true;
        material.backFaceCulling = false;

        layer.material = material;
        layer.parent = fluidGroup;
        layer.isPickable = false;
        fluidLayers.push(layer);
        registerSurface(layer, "FLUID", i * 1.8, 0.075 + i * 0.018);
      }

      const fluidVortices: B.Mesh[] = [];

      for (let i = 0; i < 5; i++) {
        const vortex = B.MeshBuilder.CreateTorus("fluid-current-" + i, {
          diameter: 1.55 + i * 0.14,
          thickness: 0.009 + (i % 2) * 0.006,
          tessellation: 128
        }, scene);

        const material = new B.StandardMaterial("fluid-current-material-" + i, scene);
        material.emissiveColor = B.Color3.FromHexString(i % 2 ? primary : secondary).scale(1.7);
        material.disableLighting = true;
        material.alpha = 0.18 + random(i + 15000) * 0.17;

        vortex.material = material;
        vortex.parent = fluidGroup;
        vortex.rotation.x = 0.5 + i * 0.48;
        vortex.rotation.z = i * 0.37;
        vortex.isPickable = false;
        fluidVortices.push(vortex);
      }

      // Динамика деформации поверхностей и энергетических потоков.
      let lastSurfaceUpdate = 0;

      const updateDynamicSurfaces = (time: number, mode: OrbStyle, intensity: number) => {
        for (const item of dynamicSurfaces) {
          if (item.mode !== mode) continue;

          const positions = item.base.slice();
          const normals: number[] = [];
          const indices = item.mesh.getIndices();
          if (!indices) continue;

          for (let i = 0; i < positions.length; i += 3) {
            const x = item.base[i];
            const y = item.base[i + 1];
            const z = item.base[i + 2];
            const length = Math.sqrt(x * x + y * y + z * z) || 1;

            const nx = x / length;
            const ny = y / length;
            const nz = z / length;

            const wave1 = Math.sin(nx * 8 + ny * 6 - time * 1.7 + item.phase);
            const wave2 = Math.sin(ny * 11 - nz * 7 + time * 1.2 + item.phase * 1.8);
            const wave3 = Math.cos(nz * 13 + nx * 8 - time * 0.9 + item.phase);
            const turbulence = Math.sin((nx + ny + nz) * 19 + time * 2.3);

            const displacement = item.amplitude * intensity *
              (wave1 * 0.34 + wave2 * 0.29 + wave3 * 0.24 + turbulence * 0.13);

            positions[i] = x + nx * displacement;
            positions[i + 1] = y + ny * displacement;
            positions[i + 2] = z + nz * displacement;
          }

          B.VertexData.ComputeNormals(positions, indices, normals);
          item.mesh.updateVerticesData(B.VertexBuffer.PositionKind, positions, false, false);
          item.mesh.updateVerticesData(B.VertexBuffer.NormalKind, normals, false, false);
        }
      };

      shell.isPickable = false;

      const rings: B.Mesh[] = [];
      if (style === "ENERGY" || style === "HOLOGRAM") {
        for (let i = 0; i < 4; i++) {
          const ring = B.MeshBuilder.CreateTorus("orb-ring-" + i, {
            diameter: 2.25 + i * 0.2,
            thickness: style === "HOLOGRAM" ? 0.008 : 0.014,
            tessellation: 160
          }, scene);
          ring.parent = root;
          ring.rotation.x = 0.65 + i * 0.31;
          ring.rotation.y = 0.3 + i * 0.42;

          const ringMaterial = new B.StandardMaterial("orb-ring-material-" + i, scene);
          ringMaterial.diffuseColor = B.Color3.FromHexString(i % 2 ? secondary : primary);
          ringMaterial.emissiveColor = ringMaterial.diffuseColor.scale(1.8);
          ringMaterial.disableLighting = true;
          ringMaterial.alpha = 0.55 - i * 0.09;
          ring.material = ringMaterial;
          rings.push(ring);
        }
      }

      const particles = new B.ParticleSystem("orb-particles", 600, scene);
      particles.particleTexture = new B.Texture(
        "https://assets.babylonjs.com/textures/flare.png",
        scene
      );
      particles.emitter = root.position;
      particles.minEmitBox = new B.Vector3(-1.15, -1.15, -1.15);
      particles.maxEmitBox = new B.Vector3(1.15, 1.15, 1.15);
      particles.color1 = B.Color4.FromHexString("#" + secondary.replace("#", "") + "FF");
      particles.color2 = B.Color4.FromHexString("#" + primary.replace("#", "") + "FF");
      particles.colorDead = new B.Color4(0.2, 0.2, 0.2, 0);
      particles.minSize = 0.012;
      particles.maxSize = 0.045;
      particles.minLifeTime = 0.5;
      particles.maxLifeTime = 2.2;
      particles.emitRate = style === "PARTICLES" ? particleCount * 2 : 90;
      particles.blendMode = B.ParticleSystem.BLENDMODE_ADD;
      particles.minEmitPower = 0.08;
      particles.maxEmitPower = 0.35;
      particles.updateSpeed = 0.012;
      particles.gravity = B.Vector3.Zero();
      particles.start();

      // Самостоятельная объёмная система PARTICLES.
      const particlePointSystem = new B.PointsCloudSystem(
        "nexus-particle-sphere",
        3.2,
        scene,
        { updatable: true }
      );

      const particleCloudCount = 1200;
      const goldenAngle = Math.PI * (3 - Math.sqrt(5));

      particlePointSystem.addPoints(particleCloudCount, (particle: B.CloudPoint, index: number) => {
        const y = 1 - (index / (particleCloudCount - 1)) * 2;
        const radius = Math.sqrt(Math.max(0, 1 - y * y));
        const angle = goldenAngle * index;
        const depth = 0.34 + random(index + 800) * 0.66;

        particle.position.set(
          Math.cos(angle) * radius * depth,
          y * depth,
          Math.sin(angle) * radius * depth
        );

        const colorMix = random(index + 1200);
        const c1 = B.Color3.FromHexString(primary);
        const c2 = B.Color3.FromHexString(secondary);
        const color = B.Color3.Lerp(c1, c2, colorMix);

        particle.color = new B.Color4(
          color.r,
          color.g,
          color.b,
          0.75 + random(index + 1500) * 0.25
        );
      });

      const particlePointMesh = await particlePointSystem.buildMeshAsync();

      if (disposed) return;

      particlePointMesh.parent = root;
      particlePointMesh.isPickable = false;

      const particleCloudMaterial = new B.StandardMaterial(
        "nexus-particle-material",
        scene
      );
      particleCloudMaterial.pointsCloud = true;
      particleCloudMaterial.pointSize = 3.2;
      particleCloudMaterial.disableLighting = true;
      particleCloudMaterial.emissiveColor = B.Color3.White();
      particleCloudMaterial.diffuseColor = B.Color3.White();
      particleCloudMaterial.alpha = 1;

      particlePointMesh.material = particleCloudMaterial;
      particlePointMesh.setEnabled(false);

      let lastParticleCloudUpdate = 0;

      const verityFace = new B.TransformNode("verity-face", scene);
      verityFace.parent = root;
      verityFace.setEnabled(style === "VERITY");

      const darkMaterial = new B.StandardMaterial("verity-dark", scene);
      darkMaterial.diffuseColor = B.Color3.FromHexString("#100D05");
      darkMaterial.emissiveColor = B.Color3.FromHexString("#100D05");
      darkMaterial.disableLighting = true;
      darkMaterial.backFaceCulling = false;

      const eyeGroup = new B.TransformNode("verity-eyes", scene);
      eyeGroup.parent = verityFace;

      const verityEyes: B.Mesh[] = [];
      const verityHighlights: B.Mesh[] = [];

      for (const x of [-0.34, 0.34]) {
        const eye = B.MeshBuilder.CreateSphere("verity-eye", {
          diameter: 1,
          segments: 32
        }, scene);
        eye.parent = eyeGroup;
        eye.scaling.set(0.105, 0.205, 0.052);
        eye.position.set(x, 0.19, -0.94);
        eye.material = darkMaterial;
        verityEyes.push(eye);

        const highlight = B.MeshBuilder.CreateSphere("verity-eye-highlight", {
          diameter: 1,
          segments: 16
        }, scene);
        highlight.parent = eyeGroup;
        highlight.scaling.set(0.027, 0.042, 0.018);
        highlight.position.set(x - 0.025, 0.245, -1.005);
        const highlightMaterial = new B.StandardMaterial("verity-eye-highlight-material", scene);
        highlightMaterial.emissiveColor = B.Color3.White();
        highlightMaterial.disableLighting = true;
        highlight.material = highlightMaterial;
        verityHighlights.push(highlight);
      }

      const smilePath = [];
      for (let i = 0; i <= 32; i++) {
        const t = i / 32;
        smilePath.push(new B.Vector3(
          -0.45 + t * 0.9,
          -0.2 - Math.sin(t * Math.PI) * 0.27,
          -0.93 + Math.abs(t - 0.5) * 0.08
        ));
      }

      const normalSmile = B.MeshBuilder.CreateTube("verity-normal-smile", {
        path: smilePath,
        radius: 0.018,
        tessellation: 8
      }, scene);
      normalSmile.parent = verityFace;
      normalSmile.material = darkMaterial;

      const creepyMouth = new B.TransformNode("verity-creepy-mouth", scene);
      creepyMouth.parent = verityFace;
      creepyMouth.position.z = -0.94;
      creepyMouth.scaling.y = 0.001;

      const mouth = B.MeshBuilder.CreateDisc("verity-mouth", {
        radius: 1,
        tessellation: 48
      }, scene);
      mouth.parent = creepyMouth;
      mouth.rotation.y = Math.PI;
      mouth.scaling.set(0.53, 0.23, 1);
      mouth.position.y = -0.31;
      mouth.material = darkMaterial;

      const toothMaterial = new B.StandardMaterial("verity-teeth", scene);
      toothMaterial.diffuseColor = B.Color3.FromHexString("#FFF9E8");
      toothMaterial.emissiveColor = B.Color3.FromHexString("#FFF9E8").scale(0.15);
      toothMaterial.disableLighting = true;

      for (let i = 0; i < 7; i++) {
        const tooth = B.MeshBuilder.CreateBox("verity-tooth-" + i, {
          width: 0.105,
          height: 0.075,
          depth: 0.018
        }, scene);
        tooth.parent = creepyMouth;
        tooth.position.set(-0.36 + i * 0.12, -0.22 - Math.sin(i / 6 * Math.PI) * 0.055, -0.055);
        tooth.material = toothMaterial;
      }

      const bottomTeeth = B.MeshBuilder.CreateBox("verity-bottom-teeth", {
        width: 0.72,
        height: 0.055,
        depth: 0.018
      }, scene);
      bottomTeeth.parent = creepyMouth;
      bottomTeeth.position.set(0, -0.4, -0.055);
      bottomTeeth.material = toothMaterial;

      let elapsed = 0;
      let eyeOffset = 0;
      let creepySmile = 0;

      let lastTime = performance.now();

      resizeObserver = new ResizeObserver(() => {
        engine?.resize();
      });
      resizeObserver.observe(mount);

      engine.runRenderLoop(() => {
        if (disposed || !scene) return;

        const now = performance.now();
        const dt = Math.min((now - lastTime) / 1000, 0.05);
        lastTime = now;
        elapsed += dt;
        if (now - lastPlasmaUpdate >= 1000 / 30) {
          const currentPlasma = propsRef.current;

          drawPlasma(
            plasmaContext,
            elapsed,
            currentPlasma.style === "VERITY" ? "#FFE51D" : currentPlasma.primary,
            currentPlasma.secondary,
            currentPlasma.glow
          );

          plasmaTexture.update(false);
          lastPlasmaUpdate = now;
        }

        const current = propsRef.current;
        const config = stateConfig[current.state];
        const motion = config.speed * current.speed;
        const pulse = 1 + Math.sin(elapsed * motion * 1.5) * config.pulse;

        root.scaling.setAll(current.scale * pulse);
        root.rotation.y = Math.sin(elapsed * 0.22) * 0.13;
        root.rotation.x = Math.sin(elapsed * 0.17) * 0.07;

        body.isVisible = !["ENERGY", "PARTICLES", "HOLOGRAM"].includes(current.style);
        shell.isVisible = ["HOLOGRAM", "VERITY"].includes(current.style);
        energyGroup.setEnabled(current.style === "ENERGY");
        hologramGroup.setEnabled(current.style === "HOLOGRAM");

        fluidGroup.setEnabled(current.style === "FLUID");
        particlePointMesh.setEnabled(current.style === "PARTICLES");
        hologramGrid.setEnabled(current.style === "HOLOGRAM");

        energyMaterials[0].emissiveColor = B.Color3.Lerp(B.Color3.FromHexString(current.primary), B.Color3.FromHexString(current.secondary), 0.48).scale(2.2 * current.glow);
        energyGroup.rotation.y = elapsed * 0.16 * motion;
        energyGroup.rotation.x = Math.sin(elapsed * 0.7) * 0.12;
        energyMaterials[0].alpha = 0.65 + Math.sin(elapsed * 13 * motion) * 0.3;

        hologramGroup.rotation.y = elapsed * 0.12 * motion;
        hologramRings.forEach((ring, index) => {
          ring.position.y = -0.78 + index * 0.26 + Math.sin(elapsed * 2 + index) * 0.012;
        });


        // HOLOGRAM: сканирование и нестабильность проекции.
        hologramGrid.rotation.y = -elapsed * 0.08 * motion;
        hologramGrid.rotation.x = Math.sin(elapsed * 0.5) * 0.035;
        hologramLines.forEach((line, index) => {
          line.color = index % 3 === 0
            ? B.Color3.Lerp(B.Color3.White(), B.Color3.FromHexString(current.secondary), 0.35)
            : B.Color3.FromHexString(current.secondary);
          line.alpha = 0.12 + (0.5 + 0.5 * Math.sin(elapsed * 3.2 + index * 1.7)) * 0.28;
        });

        // FLUID: деформируемая геометрия.
        if (now - lastSurfaceUpdate >= 1000 / 30) {
          if (current.style === "FLUID") {
            updateDynamicSurfaces(
              elapsed * motion,
              current.style,
              0.7 + current.glow * 0.3
            );
          } else if (current.style === "ENERGY") {
            updateDynamicSurfaces(elapsed * motion, "ENERGY", current.glow);
          }

          lastSurfaceUpdate = now;
        }
        fluidLayers.forEach((layer, index) => {
          const material = layer.material as B.StandardMaterial;
          material.diffuseColor = B.Color3.FromHexString(index % 2 === 0 ? current.primary : current.secondary);
          material.emissiveColor = B.Color3.FromHexString(index % 2 === 0 ? current.secondary : current.primary).scale(1.3 * current.glow);
        });

        fluidVortices.forEach((vortex, index) => {
          const material = vortex.material as B.StandardMaterial;
          material.emissiveColor = B.Color3.FromHexString(index % 2 === 0 ? current.secondary : current.primary).scale(1.7 * current.glow);
        });

        fluidLayers.forEach((layer, index) => {
          const material = layer.material as B.StandardMaterial;
          material.diffuseColor = B.Color3.FromHexString(index % 2 === 0 ? current.primary : current.secondary);
          material.emissiveColor = B.Color3.FromHexString(index % 2 === 0 ? current.secondary : current.primary).scale(1.3 * current.glow);
        });

        fluidVortices.forEach((vortex, index) => {
          const material = vortex.material as B.StandardMaterial;
          material.emissiveColor = B.Color3.FromHexString(index % 2 === 0 ? current.secondary : current.primary).scale(1.7 * current.glow);
        });

        fluidGroup.rotation.x = Math.sin(elapsed * 0.33) * 0.1;

        fluidVortices.forEach((vortex, index) => {
          vortex.rotation.y += dt * motion * (index % 2 === 0 ? 0.18 : -0.13);
          vortex.rotation.x += dt * motion * (index % 2 === 0 ? 0.09 : -0.07);
          const wave = Math.sin(elapsed * 1.5 + index * 1.4);
          vortex.scaling.setAll(1 + wave * 0.045);
        });

        bodyMaterial.emissiveTexture =
          current.style === "FLUID" ? plasmaTexture : null;

        bodyMaterial.albedoColor = B.Color3.FromHexString(
          current.style === "VERITY" ? "#FFE51D" : current.primary
        );
        bodyMaterial.emissiveColor = B.Color3.FromHexString(
          current.style === "VERITY" ? "#8F6500" : current.primary
        ).scale(0.35 * current.glow);

        shellMaterial.diffuseColor = B.Color3.FromHexString(current.primary);
        shellMaterial.emissiveColor = B.Color3.FromHexString(current.secondary).scale(0.65 * current.glow);

        rings.forEach((ring, index) => {
          const material = ring.material as B.StandardMaterial;
          const ringColor = B.Color3.Lerp(
            B.Color3.FromHexString(current.primary),
            B.Color3.FromHexString(current.secondary),
            index % 2 === 0 ? 0.25 : 0.8
          );
          material.diffuseColor = ringColor;
          material.emissiveColor = ringColor.scale(1.8 * current.glow);
          ring.isVisible = current.style === "ENERGY";
          ring.rotation.y += dt * motion * (index % 2 === 0 ? 0.12 : -0.09);
          ring.rotation.x += dt * motion * (index % 2 === 0 ? 0.08 : 0.13);
        });

        particles.emitRate =

          current.style === "ENERGY" ? 85 :
          current.style === "FLUID" ? 45 : 0;
        particles.color1 = B.Color4.FromHexString(current.secondary + "FF");
        particles.color2 = B.Color4.FromHexString(current.primary + "FF");
        particles.targetStopDuration = 0;

        if (current.style === "PARTICLES" && now - lastParticleCloudUpdate >= 1000 / 30) {
          const activeCount = Math.min(
            particleCloudCount,
            Math.max(100, current.particleCount * 5)
          );

          for (let i = 0; i < particleCloudCount; i++) {
            const particle = particlePointSystem.particles[i];
            const y = 1 - (i / (particleCloudCount - 1)) * 2;
            const ringRadius = Math.sqrt(Math.max(0, 1 - y * y));
            const angle = goldenAngle * i;

            const orbitSpeed = (0.12 + random(i + 2000) * 0.35) * motion;
            const orbit = angle + elapsed * orbitSpeed;
            const pulse = Math.sin(elapsed * 1.7 + i * 0.13) * 0.035;
            const depth = 0.34 + random(i + 800) * 0.66 + pulse;

            particle.position.set(
              Math.cos(orbit) * ringRadius * depth,
              y * depth + Math.sin(elapsed * 0.8 + i) * 0.018,
              Math.sin(orbit) * ringRadius * depth
            );

            const colorMix = random(i + 1200);
            const particleColor = B.Color3.Lerp(
              B.Color3.FromHexString(current.primary),
              B.Color3.FromHexString(current.secondary),
              colorMix
            );
            particle.color = new B.Color4(
              particleColor.r,
              particleColor.g,
              particleColor.b,
              i < activeCount ? 0.9 : 0
            );
            particlePointSystem.updateParticle(particle);
          }

          particlePointSystem.setParticles();
          particleCloudMaterial.emissiveColor =
            B.Color3.FromHexString(current.primary).scale(current.glow);
          particleCloudMaterial.pointSize = 2.2 + current.glow * 1.2;

          lastParticleCloudUpdate = now;
        }

        glowLayer.intensity = current.glow * (
          current.state === "EXECUTING" ? 1.5 :
          current.state === "THINKING" ? 1.15 : 0.8
        );

        verityFace.setEnabled(current.style === "VERITY");

        if (current.style === "VERITY") {
          // Только реакции на состояние. В SLEEP лицо неподвижно.
          const targetEye = current.state === "THINKING" ? 0.12 :
            current.state === "LISTENING" ? -0.045 :
            current.state === "EXECUTING" ? 0.07 : 0;

          const targetSmile = current.state === "EXECUTING" ? 0.72 :
            current.state === "THINKING" ? 0.18 :
            current.state === "WAKE_UP" ? 0.38 : 0;

          eyeOffset += (targetEye - eyeOffset) * Math.min(1, dt * 2.8);
          creepySmile += (targetSmile - creepySmile) * Math.min(1, dt * 2.0);

          eyeGroup.position.x = eyeOffset;
          creepyMouth.scaling.y = Math.max(0.001, creepySmile);
          normalSmile.setEnabled(creepySmile < 0.02);
          creepyMouth.setEnabled(creepySmile >= 0.02);
        } else {
          verityFace.setEnabled(false);
        }
        scene.render();
      });

      document.addEventListener("visibilitychange", () => {
        if (document.hidden) engine?.stopRenderLoop();
        else if (!disposed) engine?.runRenderLoop(() => scene?.render());
      });
    };

    void start();

    return () => {
      disposed = true;
      resizeObserver?.disconnect();
      engine?.stopRenderLoop();
      scene?.dispose();
      engine?.dispose();
      mount.replaceChildren();
    };
  }, []);

  return (
    <div
      ref={mountRef}
      className="nexus-orb-canvas"
      aria-label={`NEXUS Babylon Orb: ${style}, ${state}`}
    />
  );
}

export default function OrbPanel() {
  const style = useOrbSettings((s) => s.style);
  const state = useOrbSettings((s) => s.state);
  const primary = useOrbSettings((s) => s.primary);
  const secondary = useOrbSettings((s) => s.secondary);
  const glow = useOrbSettings((s) => s.glow);
  const speed = useOrbSettings((s) => s.speed);
  const particleCount = useOrbSettings((s) => s.particleCount);
  const scale = useOrbSettings((s) => s.scale);

  return (
    <section className="orb-workspace orb-home-centered">
      <div className="orb-main-card orb-home-transparent">
        <div className="orb-stage">
          <OrbScene
            style={style}
            state={state}
            primary={primary}
            secondary={secondary}
            glow={glow}
            speed={speed}
            particleCount={particleCount}
            scale={scale}
          />
        </div>
      </div>
    </section>
  );
}
