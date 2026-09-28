/* LIVE browser visuals: Binance public API langsung (tanpa key).
   Strategi/state tetap dari live_data.json (cron 15 mnt). File ini murni visual. */
(function () {
  var API = "https://data-api.binance.vision";
  var SYM = "BTCUSDT";
  var DSS_SYMS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT"];

  function jget(url, cb) {
    fetch(url).then(function (r) { return r.json(); }).then(cb).catch(function () {});
  }

  // ---- bola 3D pair (proyeksi orthographic, data feed cron) ----
  var nodes = [], stars = [], angY = 0;
  (function initSphere() {
    var N = 64, i, phi, th;
    for (i = 0; i < N; i++) {
      phi = Math.acos(1 - 2 * (i + 0.5) / N);
      th = Math.PI * (1 + Math.sqrt(5)) * i;
      nodes.push({x: Math.sin(phi) * Math.cos(th), y: Math.cos(phi), z: Math.sin(phi) * Math.sin(th),
                  vx: (Math.random() - 0.5) * 0.02, vy: (Math.random() - 0.5) * 0.02});
    }
    for (i = 0; i < 70; i++) stars.push({x: Math.random() * 2 - 1, y: Math.random() * 2 - 1, z: Math.random()});
  })();
  function drawGlobe() {
    var cv = document.getElementById("globe");
    if (!cv) { requestAnimationFrame(drawGlobe); return; }
    var r = cv.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
    if (cv.width !== Math.max(50, r.width * dpr)) { cv.width = Math.max(50, r.width * dpr); cv.height = Math.max(50, r.height * dpr); }
    var ctx = cv.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    var W = r.width, H = r.height;
    ctx.clearRect(0, 0, W, H);
    var R = Math.min(W, H) * 0.36, cx = W / 2, cy = H / 2;
    angY += 0.004;
    var cyA = Math.cos(angY), syA = Math.sin(angY);
    var pairs = window.__pairs || [], posSyms = window.__posSyms || {};
    var vmax = 1, i;
    pairs.forEach(function (m) { vmax = Math.max(vmax, m.vol || 0); });
    // orbit + wireframe
    ctx.strokeStyle = "rgba(180,255,57,.14)";
    ctx.lineWidth = 1;
    [-0.6, 0, 0.6].forEach(function (k) {
      ctx.beginPath();
      ctx.ellipse(cx, cy, R, R * 0.32, 0, 0, 7);
      ctx.stroke();
      void k;
    });
    ctx.beginPath(); ctx.arc(cx, cy, R, 0, 7); ctx.stroke();
    // bintang latar
    ctx.fillStyle = "rgba(255,255,255,.35)";
    stars.forEach(function (s) {
      s.x += 0.0006; if (s.x > 1) s.x = -1;
      ctx.fillRect(cx + s.x * R * 1.6, cy + s.y * R * 1.6, 1.2, 1.2);
    });
    // node pair pada bola
    var pts = [];
    for (i = 0; i < nodes.length; i++) {
      var p = nodes[i], m = pairs.length ? pairs[i % pairs.length] : null;
      var x1 = p.x * cyA + p.z * syA, z1 = -p.x * syA + p.z * cyA, y1 = p.y;
      var sx = cx + x1 * R, sy = cy - y1 * R, depth = (z1 + 1) / 2;
      var sz = m ? (5 + 13 * Math.log(1 + (m.vol || 0) / vmax * 9) / Math.log(10)) : 3;
      var col = "#b4ff39", glow = 8;
      if (m) {
        if (m.dss4 <= 30) { col = "#00e5ff"; glow = 14; }
        else if (m.dss4 >= 70) { col = "#ff4d5e"; glow = 14; }
        if (posSyms[m.sym]) { col = "#ffffff"; glow = 18; }
      }
      pts.push({x: sx, y: sy, z: depth, r: sz * (0.55 + depth * 0.7), col: col, glow: glow,
                sym: m ? m.sym.replace("USDT", "") : "", open: m ? !!posSyms[m.sym] : false});
    }
    pts.sort(function (a, b) { return a.z - b.z; });
    pts.forEach(function (q) {
      ctx.globalAlpha = 0.35 + q.z * 0.65;
      ctx.beginPath(); ctx.arc(q.x, q.y, q.r, 0, 7);
      ctx.fillStyle = q.col; ctx.shadowColor = q.col; ctx.shadowBlur = q.glow; ctx.fill();
      ctx.shadowBlur = 0;
      if (q.z > 0.55) {
        ctx.fillStyle = "#ffffff"; ctx.font = "9px ui-monospace,monospace"; ctx.textAlign = "center";
        ctx.fillText(q.sym, q.x, q.y + q.r + 10);
      }
      if (q.open) {
        ctx.beginPath(); ctx.arc(q.x, q.y, q.r + 4, 0, 7);
        ctx.strokeStyle = "#ffffff"; ctx.stroke();
      }
    });
    ctx.globalAlpha = 1;
    requestAnimationFrame(drawGlobe);
  }

  // ---- 1m candles BTC -> dipakai app.js drawBtc ----
  function pullKlines() {
    jget(API + "/api/v3/klines?symbol=" + SYM + "&interval=1m&limit=90", function (k) {
      if (!k || !k.length) return;
      window.__liveBtc = k.map(function (b) {
        return {o: parseFloat(b[1]), h: parseFloat(b[2]), l: parseFloat(b[3]), c: parseFloat(b[4])};
      });
    });
  }

  // ---- DSS 1m multi-pair -> dipakai app.js drawCross ----
  function emaArr(v, n) {
    var k = 2 / (n + 1), e = v[0], o = [e], i;
    for (i = 1; i < v.length; i++) { e = v[i] * k + e * (1 - k); o.push(e); }
    return o;
  }
  function pullDss() {
    var out = {}, left = DSS_SYMS.length, i;
    window.__liveDss = window.__liveDss || {};
    DSS_SYMS.forEach(function (s) {
      jget(API + "/api/v3/klines?symbol=" + s + "&interval=1m&limit=120", function (k) {
        if (k && k.length > 15) {
          var cc = [], hh = [], ll = [], j;
          for (j = 0; j < k.length; j++) {
            cc.push(parseFloat(k[j][4])); hh.push(parseFloat(k[j][2])); ll.push(parseFloat(k[j][3]));
          }
          var s1 = [], jj, lo, hi;
          for (j = 0; j < cc.length; j++) {
            lo = Math.min.apply(null, ll.slice(Math.max(0, j - 9), j + 1));
            hi = Math.max.apply(null, hh.slice(Math.max(0, j - 9), j + 1));
            s1.push(hi > lo ? 100 * (cc[j] - lo) / (hi - lo) : 50);
          }
          out[s.replace("USDT", "")] = emaArr(s1, 9).slice(-60).map(function (v) {
            return Math.round(v * 10) / 10;
          });
        }
        if (--left === 0 && Object.keys(out).length) window.__liveDss = out;
      });
    });
  }

  drawGlobe(); pullKlines(); pullDss();
  setInterval(pullKlines, 15000);
  setInterval(pullDss, 30000);
})();
