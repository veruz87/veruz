/* HERO 3D (Three.js WebGL): inti icosahedron + 3 cincin orbit partikel + pulse whale.
   Data: aggTrades BTC real. Gagal CDN/WebGL = pesan fallback. */
(function () {
  function fail(msg) {
    fallback2d(el || document.getElementById("hero3d"), "HERO");
  }
  function fallback2d(elm, label) {
    if (!elm) return;
    var cv = document.createElement("canvas");
    cv.style.cssText = "position:absolute;inset:0;width:100%;height:100%";
    elm.style.position = "relative";
    elm.appendChild(cv);
    var dots = [], i;
    for (i = 0; i < 90; i++) dots.push({a: Math.random() * 7, r: 0.3 + Math.random() * 0.55,
      sp: 0.002 + Math.random() * 0.005, s: 1 + Math.random() * 2});
    var ang = 0;
    (function loop() {
      requestAnimationFrame(loop);
      var r = elm.getBoundingClientRect();
      if (r.width < 10) return;
      var dpr = window.devicePixelRatio || 1;
      cv.width = r.width * dpr; cv.height = r.height * dpr;
      var ctx = cv.getContext("2d");
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.fillStyle = "rgba(0,0,0,.35)";
      ctx.fillRect(0, 0, r.width, r.height);
      var cx = r.width / 2, cy = r.height / 2, R = Math.min(r.width, r.height) * 0.4;
      ang += 0.004;
      ctx.strokeStyle = "rgba(180,255,57,.3)";
      ctx.beginPath(); ctx.arc(cx, cy, R, 0, 7); ctx.stroke();
      dots.forEach(function (d) {
        d.a += d.sp;
        ctx.fillStyle = "#b4ff39";
        ctx.beginPath(); ctx.arc(cx + Math.cos(d.a + ang) * R * d.r, cy + Math.sin(d.a + ang) * R * d.r * 0.8, d.s, 0, 7); ctx.fill();
      });
      ctx.fillStyle = "rgba(238,243,230,.7)"; ctx.font = "9px monospace"; ctx.textAlign = "left";
      ctx.fillText(label + " · 2D", 10, r.height - 10);
    })();
  }
  if (!window.THREE) { fail("3D offline (CDN)"); return; }
  var el = document.getElementById("hero3d");
  if (!el) return;
  var W = el.clientWidth || 600, H = el.clientHeight || 260;
  var renderer;
  try {
    renderer = new THREE.WebGLRenderer({antialias: true, alpha: true});
  } catch (e) { fail("WebGL mati"); return; }
  renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
  renderer.setSize(W, H);
  el.appendChild(renderer.domElement);
  var scene = new THREE.Scene();
  var camera = new THREE.PerspectiveCamera(50, W / H, 0.1, 100);
  camera.position.set(0, 0.7, 5.2);
  camera.lookAt(0, 0, 0);
  var group = new THREE.Group();
  scene.add(group);
  // inti icosahedron gold wireframe + glow dalam
  var core = new THREE.Mesh(
    new THREE.IcosahedronGeometry(0.85, 1),
    new THREE.MeshBasicMaterial({color: 0xffb03a, wireframe: true, transparent: true, opacity: 0.9}));
  group.add(core);
  var glowTex = (function () {
    var c = document.createElement("canvas");
    c.width = c.height = 128;
    var g = c.getContext("2d");
    var gr = g.createRadialGradient(64, 64, 2, 64, 64, 64);
    gr.addColorStop(0, "rgba(255,210,140,1)");
    gr.addColorStop(0.4, "rgba(255,160,50,.45)");
    gr.addColorStop(1, "rgba(255,140,30,0)");
    g.fillStyle = gr;
    g.fillRect(0, 0, 128, 128);
    return new THREE.CanvasTexture(c);
  })();
  var glow = new THREE.Sprite(new THREE.SpriteMaterial({map: glowTex, transparent: true,
    blending: THREE.AdditiveBlending, depthWrite: false}));
  glow.scale.set(3.2, 3.2, 1);
  group.add(glow);
  // 3 cincin orbit miring + partikelnya
  var RINGS = [
    {c: 0xb4ff39, r: 2.1, tilt: [0.5, 0, 0.2], n: 130, sp: 0.22},
    {c: 0x00e5ff, r: 1.7, tilt: [-0.4, 0.1, 0.5], n: 110, sp: -0.18},
    {c: 0xff4d5e, r: 1.35, tilt: [0.2, -0.3, -0.4], n: 90, sp: 0.26}
  ];
  var systems = [];
  RINGS.forEach(function (rg) {
    var holder = new THREE.Group();
    holder.rotation.set(rg.tilt[0], rg.tilt[1], rg.tilt[2]);
    var pos = new Float32Array(rg.n * 3), col = new Float32Array(rg.n * 3);
    var base = new THREE.Color(rg.c);
    for (var i = 0; i < rg.n; i++) {
      var a = (i / rg.n) * Math.PI * 2;
      pos[i * 3] = Math.cos(a) * rg.r;
      pos[i * 3 + 1] = 0;
      pos[i * 3 + 2] = Math.sin(a) * rg.r;
      var v = 0.5 + Math.random() * 0.5;
      col[i * 3] = base.r * v; col[i * 3 + 1] = base.g * v; col[i * 3 + 2] = base.b * v;
    }
    var geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    geo.setAttribute("color", new THREE.BufferAttribute(col, 3));
    var pts = new THREE.Points(geo, new THREE.PointsMaterial({size: 0.055, vertexColors: true,
      blending: THREE.AdditiveBlending, transparent: true, depthWrite: false}));
    holder.add(pts);
    var ring = new THREE.Mesh(
      new THREE.TorusGeometry(rg.r, 0.006, 8, 128),
      new THREE.MeshBasicMaterial({color: rg.c, transparent: true, opacity: 0.35}));
    ring.rotation.x = Math.PI / 2;
    holder.add(ring);
    group.add(holder);
    systems.push({holder: holder, sp: rg.sp});
  });
  // bintang latar
  (function () {
    var n = 250, p = new Float32Array(n * 3), i;
    for (i = 0; i < n; i++) {
      p[i * 3] = (Math.random() - 0.5) * 14;
      p[i * 3 + 1] = (Math.random() - 0.5) * 8;
      p[i * 3 + 2] = -2 - Math.random() * 6;
    }
    var g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(p, 3));
    scene.add(new THREE.Points(g, new THREE.PointsMaterial({color: 0x889988, size: 0.03,
      transparent: true, opacity: 0.7})));
  })();
  // pulse whale: trade real -> flash inti + burst
  var pulse = 0, lastId = 0, bursts = [];
  setInterval(function () {
    fetch("https://data-api.binance.vision/api/v3/aggTrades?symbol=BTCUSDT&limit=20")
      .then(function (r) { return r.json(); }).then(function (t) {
        if (!t || !t.length) return;
        t.forEach(function (x) {
          if (x.a <= lastId) return;
          lastId = Math.max(lastId, x.a);
          var usd = parseFloat(x.q) * parseFloat(x.p);
          if (usd >= 50000) {
            pulse = Math.min(1.5, pulse + 0.9);
            for (var j = 0; j < 24; j++) {
              var va = Math.random() * Math.PI * 2, vb = Math.acos(2 * Math.random() - 1);
              bursts.push({vx: Math.sin(vb) * Math.cos(va), vy: Math.cos(vb), vz: Math.sin(vb) * Math.sin(va),
                           life: 1, sell: !!x.m});
            }
          } else {
            pulse = Math.min(1.5, pulse + 0.04);
          }
        });
      }).catch(function () {});
  }, 2000);
  var burstGeo = new THREE.BufferGeometry();
  var burstPos = new Float32Array(240 * 3);
  burstGeo.setAttribute("position", new THREE.BufferAttribute(burstPos, 3));
  var burstPts = new THREE.Points(burstGeo, new THREE.PointsMaterial({color: 0xffcf90, size: 0.06,
    blending: THREE.AdditiveBlending, transparent: true, depthWrite: false}));
  scene.add(burstPts);
  var burstLive = [];
  // drag putar
  var drag = false, px = 0;
  el.addEventListener("pointerdown", function (e) { drag = true; px = e.clientX; });
  window.addEventListener("pointerup", function () { drag = false; });
  el.addEventListener("pointermove", function (e) {
    if (!drag) return;
    group.rotation.y += (e.clientX - px) * 0.008;
    px = e.clientX;
  });
  (function tick() {
    requestAnimationFrame(tick);
    if (document.hidden) return;
    var r = el.getBoundingClientRect();
    if (r.width < 10) return;
    if (Math.abs(r.width / r.height - camera.aspect) > 0.01) {
      camera.aspect = r.width / r.height;
      camera.updateProjectionMatrix();
      renderer.setSize(r.width, r.height);
    }
    pulse = Math.max(0.12, pulse * 0.97);
    group.rotation.y += 0.0035 * (1 + pulse);
    core.rotation.x += 0.002;
    core.scale.setScalar(1 + pulse * 0.25);
    glow.scale.set(3.2 * (1 + pulse * 0.5), 3.2 * (1 + pulse * 0.5), 1);
    systems.forEach(function (s) { s.holder.rotation.y += s.sp * 0.01 * (1 + pulse); });
    // sebar partikel ledakan whale
    if (bursts.length && burstLive.length < 240) {
      var b = bursts.shift();
      burstLive.push({x: 0, y: 0, z: 0, vx: b.vx * 0.06, vy: b.vy * 0.06, vz: b.vz * 0.06, life: 1});
    }
    for (var i = burstLive.length - 1; i >= 0; i--) {
      var p = burstLive[i];
      p.x += p.vx; p.y += p.vy; p.z += p.vz; p.life -= 0.02;
      if (p.life <= 0) burstLive.splice(i, 1);
    }
    for (var k = 0; k < 240; k++) {
      var q = burstLive[k];
      burstPos[k * 3] = q ? q.x : 0;
      burstPos[k * 3 + 1] = q ? q.y : 0;
      burstPos[k * 3 + 2] = q ? q.z - 5 : -5;
    }
    burstGeo.attributes.position.needsUpdate = true;
    renderer.render(scene, camera);
  })();
})();
