/* GLOBE 3D pair (Three.js WebGL): 700 titik + 21 label koin.
   Data: window.__pairs (feed cron). Gagal CDN = pesan fallback. */
(function () {
  function fail(msg) {
    var el = document.getElementById("globe3d");
    if (el) el.innerHTML = '<div style="color:#8a937f;font:11px monospace;padding:20px">' + msg + "</div>";
  }
  if (!window.THREE) { fail("3D offline (CDN)"); return; }
  var el = document.getElementById("globe3d");
  if (!el) return;
  var W = el.clientWidth || 300, H = el.clientHeight || 260;
  var renderer;
  try {
    renderer = new THREE.WebGLRenderer({antialias: true, alpha: true});
  } catch (e) { fail("WebGL mati"); return; }
  renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
  renderer.setSize(W, H);
  el.appendChild(renderer.domElement);
  var scene = new THREE.Scene();
  var camera = new THREE.PerspectiveCamera(50, W / H, 0.1, 100);
  camera.position.z = 4.2;
  var group = new THREE.Group();
  scene.add(group);
  // bola titik
  var N = 700, pos = new Float32Array(N * 3), col = new Float32Array(N * 3);
  var i, phi, th;
  for (i = 0; i < N; i++) {
    phi = Math.acos(1 - 2 * (i + 0.5) / N);
    th = Math.PI * (1 + Math.sqrt(5)) * i;
    pos[i * 3] = 1.5 * Math.sin(phi) * Math.cos(th);
    pos[i * 3 + 1] = 1.5 * Math.cos(phi);
    pos[i * 3 + 2] = 1.5 * Math.sin(phi) * Math.sin(th);
    col[i * 3] = 0.35; col[i * 3 + 1] = 0.5; col[i * 3 + 2] = 0.2;
  }
  var geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  geo.setAttribute("color", new THREE.BufferAttribute(col, 3));
  var pts = new THREE.Points(geo, new THREE.PointsMaterial({size: 0.035, vertexColors: true,
    blending: THREE.AdditiveBlending, transparent: true, depthWrite: false}));
  group.add(pts);
  // wireframe halus
  var wire = new THREE.LineSegments(
    new THREE.WireframeGeometry(new THREE.SphereGeometry(1.52, 18, 12)),
    new THREE.LineBasicMaterial({color: 0x2a3a1a, transparent: true, opacity: 0.5}));
  group.add(wire);
  // label koin (sprite, top-21)
  var labels = [];
  function textSprite(txt, color) {
    var c = document.createElement("canvas");
    c.width = 128; c.height = 32;
    var g = c.getContext("2d");
    g.font = "bold 20px monospace"; g.textAlign = "center";
    g.shadowColor = color; g.shadowBlur = 8; g.fillStyle = color;
    g.fillText(txt, 64, 23);
    var sp = new THREE.Sprite(new THREE.SpriteMaterial({map: new THREE.CanvasTexture(c),
      transparent: true, depthWrite: false}));
    sp.scale.set(0.55, 0.14, 1);
    return sp;
  }
  function refreshLabels() {
    var pairs = (window.__pairs || []).slice(0, 21);
    if (!pairs.length) return;
    labels.forEach(function (l) { group.remove(l); });
    labels = [];
    var vmax = 1;
    pairs.forEach(function (m) { vmax = Math.max(vmax, m.vol || 0); });
    pairs.forEach(function (m, ix) {
      var color = "#b4ff39";
      if (m.dss4 <= 30) color = "#00e5ff";
      else if (m.dss4 >= 70) color = "#ff4d5e";
      var sp = textSprite(m.sym.replace("USDT", ""), color);
      var a = (ix / pairs.length) * Math.PI * 2;
      var s = 0.8 + 0.5 * ((m.vol || 0) / vmax);
      sp.position.set(Math.cos(a) * 1.9, (ix % 2 ? 0.7 : -0.7) + (ix % 5) * 0.14 - 0.3, Math.sin(a) * 1.9);
      sp.scale.set(0.45 * s + 0.2, 0.11 * s + 0.05, 1);
      group.add(sp);
      labels.push(sp);
    });
  }
  refreshLabels();
  setInterval(refreshLabels, 30000);
  // drag putar (desktop)
  var drag = false, px = 0, vx = 0.0035;
  el.addEventListener("pointerdown", function (e) { drag = true; px = e.clientX; });
  window.addEventListener("pointerup", function () { drag = false; });
  el.addEventListener("pointermove", function (e) {
    if (!drag) return;
    group.rotation.y += (e.clientX - px) * 0.008;
    px = e.clientX;
    vx = 0.0015;
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
    group.rotation.y += vx;
    renderer.render(scene, camera);
  })();
})();
