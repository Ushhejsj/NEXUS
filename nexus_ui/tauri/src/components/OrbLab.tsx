import { useEffect, useRef, useState } from "react";
import * as THREE from "three/webgpu";
import { color, positionLocal, sin, time } from "three/tsl";
import { bloom } from "three/addons/tsl/display/BloomNode.js";

export default function OrbLab() {
  const hostRef = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState("Подготовка плазменного ядра...");
  const [fps, setFps] = useState(0);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;

    let renderer: THREE.WebGPURenderer | null = null;
    let pipeline: THREE.RenderPipeline | null = null;
    let scenePass: THREE.PassNode | null = null;
    let resizeObserver: ResizeObserver | null = null;
    let disposed = false;
    let frameCount = 0;
    let lastFpsTime = performance.now();

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
    camera.position.set(0, 0, 6.1);

    const root = new THREE.Group();
    scene.add(root);

    const ambient = new THREE.AmbientLight(0x8299ff, 1.0);
    scene.add(ambient);

    const blueLight = new THREE.PointLight(0x277cff, 100, 12);
    blueLight.position.set(-2.5, 2.2, 3);
    scene.add(blueLight);

    const cyanLight = new THREE.PointLight(0x21dfff, 65, 10);
    cyanLight.position.set(2.5, -1.5, 2);
    scene.add(cyanLight);

    const violetLight = new THREE.PointLight(0x923cff, 75, 10);
    violetLight.position.set(0, 2.5, -2);
    scene.add(violetLight);

    // Процедурная поверхность: несколько независимых энергетических волн.
    const coreGeometry = new THREE.IcosahedronGeometry(1.22, 128);
    const coreMaterial = new THREE.MeshStandardNodeMaterial();

    const p = positionLocal;

    const waveA = sin(p.x.mul(8.5).add(p.y.mul(3.2)).add(time.mul(1.7)));
    const waveB = sin(p.y.mul(10.0).sub(p.z.mul(4.5)).sub(time.mul(1.35)));
    const waveC = sin(p.z.mul(9.0).add(p.x.mul(5.0)).add(time.mul(1.05)));
    const waveD = sin(p.x.mul(17.0).sub(p.y.mul(12.0)).add(time.mul(2.4)));

    const field = waveA.mul(waveB).add(waveC.mul(0.42)).add(waveD.mul(0.18));
    const displacement = field.mul(0.038);

    coreMaterial.positionNode = p.add(p.mul(displacement));

    const surfaceLight = field.mul(0.13).add(0.83);
    coreMaterial.colorNode = color(0x1747b9).mul(surfaceLight);

    const pulse = sin(time.mul(1.8)).mul(0.5).add(0.5);
    coreMaterial.emissiveNode = color(0x126dff).mul(
      pulse.mul(0.48).add(0.72).add(field.mul(0.16))
    );

    coreMaterial.roughness = 0.2;
    coreMaterial.metalness = 0.34;

    const core = new THREE.Mesh(coreGeometry, coreMaterial);
    root.add(core);

    // Светящееся внутреннее ядро.
    const innerGeometry = new THREE.SphereGeometry(0.76, 64, 64);
    const innerMaterial = new THREE.MeshBasicMaterial({
      color: 0x167bff,
      transparent: true,
      opacity: 0.19,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });

    const innerCore = new THREE.Mesh(innerGeometry, innerMaterial);
    root.add(innerCore);

    const heartGeometry = new THREE.SphereGeometry(0.43, 48, 48);
    const heartMaterial = new THREE.MeshBasicMaterial({
      color: 0x75eaff,
      transparent: true,
      opacity: 0.15,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });

    const heart = new THREE.Mesh(heartGeometry, heartMaterial);
    root.add(heart);

    // Внешние слои мягкой энергетической ауры.
    const auraGroup = new THREE.Group();
    root.add(auraGroup);

    const auraLayers = [
      { radius: 1.35, scale: 1.0, opacity: 0.09, tint: 0x2678ff },
      { radius: 1.48, scale: 1.0, opacity: 0.055, tint: 0x397aff },
      { radius: 1.64, scale: 1.0, opacity: 0.025, tint: 0x24cfff }
    ];

    auraLayers.forEach((layer) => {
      const geometry = new THREE.SphereGeometry(layer.radius, 64, 64);
      const material = new THREE.MeshBasicMaterial({
        color: layer.tint,
        transparent: true,
        opacity: layer.opacity,
        side: THREE.BackSide,
        blending: THREE.AdditiveBlending,
        depthWrite: false
      });

      const mesh = new THREE.Mesh(geometry, material);
      mesh.scale.setScalar(layer.scale);
      auraGroup.add(mesh);
    });

    // ДИНАМИЧЕСКОЕ ЭЛЕКТРИЧЕСТВО: ветвящиеся молнии на поверхности ядра.
    const arcGroup = new THREE.Group();
    root.add(arcGroup);

    const arcGeometry = new THREE.BufferGeometry();
    const arcMaterial = new THREE.LineBasicMaterial({
      color: 0xb9f8ff,
      transparent: true,
      opacity: 1,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });

    const arcLines = new THREE.LineSegments(arcGeometry, arcMaterial);
    arcGroup.add(arcLines);

    const randomDirection = () => new THREE.Vector3(
      Math.random() * 2 - 1,
      Math.random() * 2 - 1,
      Math.random() * 2 - 1
    ).normalize();

    const buildBolt = (
      start: THREE.Vector3,
      end: THREE.Vector3,
      steps: number,
      spread: number
    ): THREE.Vector3[] => {
      const points: THREE.Vector3[] = [];

      for (let i = 0; i <= steps; i++) {
        const t = i / steps;
        const point = start.clone().lerp(end, t);

        if (i !== 0 && i !== steps) {
          point.add(new THREE.Vector3(
            (Math.random() - 0.5) * spread,
            (Math.random() - 0.5) * spread,
            (Math.random() - 0.5) * spread
          ));
        }

        point.normalize().multiplyScalar(1.245);
        points.push(point);
      }

      return points;
    };

    let lightningTimer = 0;

    const updateLightning = (elapsed: number) => {
      const vertices: number[] = [];

      const addPath = (points: THREE.Vector3[]) => {
        for (let i = 0; i < points.length - 1; i++) {
          const a = points[i];
          const b = points[i + 1];

          vertices.push(a.x, a.y, a.z, b.x, b.y, b.z);
        }
      };

      // Основные электрические каналы.
      for (let i = 0; i < 22; i++) {
        const start = randomDirection();
        const end = randomDirection();
        const path = buildBolt(start, end, 13, 0.17);

        addPath(path);

        // Несколько ответвлений от основного канала.
        if (Math.random() > 0.18) {
          const branchIndex = 3 + Math.floor(Math.random() * 7);
          const branchStart = path[branchIndex].clone();
          const branchEnd = branchStart.clone()
            .add(randomDirection().multiplyScalar(0.5));

          addPath(buildBolt(branchStart, branchEnd, 6, 0.2));
        }
      }

      // Внешние электрические выбросы.
      for (let i = 0; i < 7; i++) {
        const direction = randomDirection();
        const start = direction.clone().multiplyScalar(1.21);
        const end = direction.clone().multiplyScalar(1.48 + Math.random() * 0.4);
        const middle = start.clone().lerp(end, 0.5);

        middle.add(new THREE.Vector3(
          (Math.random() - 0.5) * 0.25,
          (Math.random() - 0.5) * 0.25,
          (Math.random() - 0.5) * 0.25
        ));

        vertices.push(
          start.x, start.y, start.z,
          middle.x, middle.y, middle.z,
          middle.x, middle.y, middle.z,
          end.x, end.y, end.z
        );
      }

      arcGeometry.setAttribute(
        "position",
        new THREE.Float32BufferAttribute(vertices, 3)
      );
      arcGeometry.computeBoundingSphere();

      const flash = Math.pow(
        Math.max(0, Math.sin(elapsed * 8.7)),
        14
      );

      arcMaterial.opacity = 0.68 + flash * 0.32;
    };
    // Мелкие энергетические частицы вокруг ядра.
    const particleCount = 350;
    const particlePositions = new Float32Array(particleCount * 3);
    const particleSizes = new Float32Array(particleCount);

    for (let i = 0; i < particleCount; i++) {
      const radius = 1.55 + Math.random() * 1.2;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);

      particlePositions[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
      particlePositions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
      particlePositions[i * 3 + 2] = radius * Math.cos(phi);

      particleSizes[i] = 0.5 + Math.random() * 1.5;
    }

    const particleGeometry = new THREE.BufferGeometry();
    particleGeometry.setAttribute(
      "position",
      new THREE.BufferAttribute(particlePositions, 3)
    );

    const particleMaterial = new THREE.PointsMaterial({
      color: 0x75caff,
      size: 0.023,
      transparent: true,
      opacity: 0.22,
      sizeAttenuation: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending
    });

    const particles = new THREE.Points(particleGeometry, particleMaterial);
    root.add(particles);

    // Дополнительные световые акценты.
    const glowGeometry = new THREE.SphereGeometry(0.055, 16, 16);
    const glowMaterial = new THREE.MeshBasicMaterial({
      color: 0x9eeeff,
      transparent: true,
      opacity: 0.85,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });

    const sparks: THREE.Mesh[] = [];

    for (let i = 0; i < 9; i++) {
      const spark = new THREE.Mesh(glowGeometry, glowMaterial.clone());
      const angle = (i / 9) * Math.PI * 2;
      spark.position.set(
        Math.cos(angle) * 1.48,
        Math.sin(angle * 1.7) * 0.8,
        Math.sin(angle) * 1.15
      );
      root.add(spark);
      sparks.push(spark);
    }

    const resize = () => {
      if (!renderer || !host) return;

      const width = Math.max(host.clientWidth, 1);
      const height = Math.max(host.clientHeight, 1);

      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height);
      scenePass?.setSize(width, height);
    };

    const start = async () => {
      try {
        renderer = new THREE.WebGPURenderer({
          antialias: true,
          alpha: true,
          powerPreference: "high-performance"
        });

        renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));

        await renderer.init();
        
        if (disposed) {
          renderer.dispose();
          return;
        }
        
        scenePass = new THREE.PassNode(THREE.PassNode.COLOR, scene, camera);
        const sceneColor = scenePass.getTextureNode("output");
        const bloomPass = bloom(sceneColor, 1.2, 0.38, 0.68);
        pipeline = new THREE.RenderPipeline(renderer);
        pipeline.outputNode = sceneColor.add(bloomPass);

        if (disposed || !host || !renderer) {
          renderer?.dispose();
          return;
        }

        host.appendChild(renderer.domElement);
        renderer.domElement.className = "orb-lab-canvas";

        resize();

        resizeObserver = new ResizeObserver(resize);
        resizeObserver.observe(host);

        setStatus("PLASMA CORE · PROCEDURAL NODE MATERIAL · LIVE");

        let elapsed = 0;
        let previousFrameTime = performance.now();

        renderer.setAnimationLoop(() => {
          if (!renderer || disposed) return;

          const frameTime = performance.now();
          const dt = Math.min((frameTime - previousFrameTime) / 1000, 0.05);
          previousFrameTime = frameTime;
          elapsed += dt;
          lightningTimer += dt;
          if (lightningTimer >= 0.085) {
            lightningTimer = 0;
            updateLightning(elapsed);
          }

          core.rotation.y = elapsed * 0.105;
          core.rotation.x = Math.sin(elapsed * 0.31) * 0.12;

          innerCore.rotation.y = -elapsed * 0.24;
          innerCore.rotation.x = elapsed * 0.17;

          heart.scale.setScalar(0.92 + Math.sin(elapsed * 2.1) * 0.075);

          auraGroup.rotation.y = -elapsed * 0.035;
          auraGroup.rotation.x = Math.sin(elapsed * 0.22) * 0.07;

          particles.rotation.y = elapsed * 0.025;
          particles.rotation.x = Math.sin(elapsed * 0.15) * 0.07;

          sparks.forEach((spark, index) => {
            const angle = elapsed * (0.35 + index * 0.018) + index * 0.7;
            spark.position.x = Math.cos(angle) * (1.35 + Math.sin(elapsed * 1.8 + index) * 0.12);
            spark.position.y = Math.sin(angle * 1.4) * 0.85;
            spark.position.z = Math.sin(angle) * 1.15;
            spark.scale.setScalar(0.65 + (Math.sin(elapsed * 3 + index) + 1) * 0.55);
          });

          blueLight.position.x = Math.sin(elapsed * 0.7) * 2.5;
          cyanLight.position.y = Math.cos(elapsed * 0.55) * 2.0;
          violetLight.position.x = Math.cos(elapsed * 0.4) * 2.0;

          if (pipeline) {
            pipeline.render();
          } else {
            renderer.render(scene, camera);
          }

          frameCount++;

          const now = performance.now();
          if (now - lastFpsTime >= 1000) {
            setFps(Math.round(frameCount * 1000 / (now - lastFpsTime)));
            frameCount = 0;
            lastFpsTime = now;
          }
        });
      } catch (error) {
        console.error("NEXUS Plasma Core:", error);
        setStatus("Ошибка запуска графики. Подробности доступны в консоли.");
      }
    };

    void start();

    return () => {
      disposed = true;
      resizeObserver?.disconnect();

      if (renderer) {
        renderer.setAnimationLoop(null);
        pipeline?.dispose();
        pipeline = null;
        scenePass = null;
        renderer.dispose();
        renderer.domElement.remove();
      }

      const geometries = new Set<THREE.BufferGeometry>();
      const materials = new Set<THREE.Material>();

      scene.traverse((object) => {
        const mesh = object as THREE.Mesh;

        if (mesh.geometry) geometries.add(mesh.geometry);

        if (Array.isArray(mesh.material)) {
          mesh.material.forEach((material) => materials.add(material));
        } else if (mesh.material) {
          materials.add(mesh.material);
        }

        if (object instanceof THREE.Line) {
          const line = object as THREE.Line;
          geometries.add(line.geometry);

          if (Array.isArray(line.material)) {
            line.material.forEach((material) => materials.add(material));
          } else {
            materials.add(line.material);
          }
        }
      });

      geometries.forEach((geometry) => geometry.dispose());
      materials.forEach((material) => material.dispose());
    };
  }, []);

  return (
    <div className="orb-lab">
      <div className="orb-lab-heading">
        <div>
          <div className="eyebrow">NEXUS GRAPHICS EXPERIMENT</div>
          <h1>Orb <span>Laboratory</span></h1>
          <p className="page-description">
            Процедурная плазма, энергетические потоки и объёмное свечение.
          </p>
        </div>

        <div className="orb-lab-metrics">
          <div className="orb-lab-metric">
            <span>FPS</span>
            <strong>{fps || "—"}</strong>
          </div>
          <div className="orb-lab-metric">
            <span>ENGINE</span>
            <strong>THREE.JS</strong>
          </div>
        </div>
      </div>

      <div className="orb-lab-stage" ref={hostRef}>
        <div className="orb-lab-overlay">
          <span className="orb-lab-live-dot" />
          PLASMA CORE · LIVE
        </div>
      </div>

      <div className="orb-lab-status">
        <span className="orb-lab-status-dot" />
        {status}
      </div>

      <div className="orb-lab-info">
        <div>
          <strong>01 / PLASMA SURFACE</strong>
          <span>Процедурная деформация и многослойная энергетическая структура</span>
        </div>
        <div>
          <strong>02 / ENERGY STREAMS</strong>
          <span>Пространственные плазменные ленты и электрические дуги</span>
        </div>
        <div>
          <strong>03 / VOLUMETRIC GLOW</strong>
          <span>Внутреннее ядро, внешняя аура и динамическое освещение</span>
        </div>
      </div>
    </div>
  );
}




