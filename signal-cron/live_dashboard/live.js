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
    var cv = document.getElementById("crossCanvas");
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

  // ---- BOIDS kawanan mood-pasar (panel LIVE FEED, tick BTC real) ----
  var flock = [], ticks = [], i;
  for (i = 0; i < 40; i++) flock.push({x: Math.random(), y: Math.random(),
    vx: (Math.random() - 0.5) * 0.004, vy: (Math.random() - 0.5) * 0.004});
  setInterval(function () {
    jget(API + "/api/v3/ticker/price?symbol=" + SYM, function (t) {
      if (!t || !t.price) return;
      ticks.push(parseFloat(t.price));
      if (ticks.length > 40) ticks.shift();
    });
  }, 3000);
  function mood() { // 0 tenang -> 1 erupt, dari volatilitas tick
    if (ticks.length < 10) return 0.25;
    var s = 0, j;
    for (j = 1; j < ticks.length; j++) s += Math.abs(Math.log(ticks[j] / ticks[j - 1]));
    return Math.max(0, Math.min(1, (s / ticks.length) * 900));
  }
  (function boidsLoop() {
    try {
      var cv = document.getElementById("globeMain");
      if (cv) {
        var f = fitCv(cv), ctx = f.ctx, e = mood();
        ctx.setTransform(f.dpr, 0, 0, f.dpr, 0, 0);
        ctx.fillStyle = "rgba(0,0,0,.28)";
        ctx.fillRect(0, 0, f.W, f.H);
        var W = f.W, H = f.H, R = 0.09 + (1 - e) * 0.12, SP = 0.0016 + e * 0.004, j, k;
        flock.forEach(function (b) {
          var ax = 0, ay = 0, nx = 0, ny = 0, avx = 0, avy = 0;
          flock.forEach(function (o) {
            if (o === b) return;
            var dx = b.x - o.x, dy = b.y - o.y, dd = Math.sqrt(dx * dx + dy * dy) || 0.001;
            if (dd < 0.09) { ax += dx / dd * 0.0006; ay += dy / dd * 0.0006; }
            if (dd < R) { nx += o.x; ny += o.y; avx += o.vx; avy += o.vy; k = (k || 0) + 1; }
          });
          var n = flock.length;
          ax += (nx / n - b.x) * 0.002 + (avx / n - b.vx) * 0.03;
          ay += (ny / n - b.y) * 0.002 + (avy / n - b.vy) * 0.03;
          // pusat magnet lemah agar tak kabur
          ax += (0.5 - b.x) * 0.0004; ay += (0.5 - b.y) * 0.0004;
          b.vx += ax; b.vy += ay;
          var sp = Math.sqrt(b.vx * b.vx + b.vy * b.vy) || 1, mx = SP * 3;
          if (sp > mx) { b.vx *= mx / sp; b.vy *= mx / sp; }
          b.x += b.vx; b.y += b.vy;
          if (b.x < 0) b.x += 1; if (b.x > 1) b.x -= 1;
          if (b.y < 0) b.y += 1; if (b.y > 1) b.y -= 1;
        });
        flock.forEach(function (b) {
          var ang = Math.atan2(b.vy, b.vx);
          var g = Math.round(255 - e * 200), r = Math.round(140 + e * 115);
          ctx.save();
          ctx.translate(b.x * W, b.y * H);
          ctx.rotate(ang);
          ctx.fillStyle = "rgb(" + r + "," + g + ",60)";
          ctx.shadowColor = ctx.fillStyle; ctx.shadowBlur = 6 + e * 10;
          ctx.beginPath();
          ctx.moveTo(7, 0); ctx.lineTo(-5, -4); ctx.lineTo(-2, 0); ctx.lineTo(-5, 4);
          ctx.closePath(); ctx.fill();
          ctx.restore();
        });
        ctx.fillStyle = "rgba(238,243,230,.8)"; ctx.font = "9px ui-monospace,monospace"; ctx.textAlign = "left";
        ctx.fillText(e > 0.6 ? "ERUPT" : (e > 0.3 ? "AGITATED" : "CALM"), 10, H - 10);
      }
    } catch (err) {}
    requestAnimationFrame(boidsLoop);
  })();

  // ---- util kanvas ----
  function fitCv(cv) {
    var r = cv.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
    cv.width = Math.max(50, r.width * dpr); cv.height = Math.max(50, r.height * dpr);
    return {ctx: cv.getContext("2d"), dpr: dpr, W: r.width, H: r.height};
  }

  // (radar dicabut: crossCanvas dipakai bola 3D)

  // ---- WATERFALL trade live (panel THE WIRE, aggTrades BTC real) ----
  var falls = [], lastTid = 0;
  setInterval(function () {
    jget(API + "/api/v3/aggTrades?symbol=" + SYM + "&limit=30", function (t) {
      if (!t || !t.length) return;
      t.forEach(function (x) {
        if (x.a > lastTid) {
          lastTid = Math.max(lastTid, x.a);
          var usd = parseFloat(x.q) * parseFloat(x.p);
          falls.push({x: Math.random(), y: -0.05, vy: 0.004 + Math.min(0.02, usd / 5000000),
                      w: 3 + Math.min(26, usd / 8000), sell: !!x.m,
                      usd: usd, px: parseFloat(x.p)});
        }
      });
      if (falls.length > 70) falls = falls.slice(-70);
    });
  }, 2000);
  (function wireLoop() {
    try {
      var cv = document.getElementById("wireCanvas");
      if (cv) {
        var f = fitCv(cv), ctx = f.ctx;
        ctx.setTransform(f.dpr, 0, 0, f.dpr, 0, 0);
        ctx.clearRect(0, 0, f.W, f.H);
        falls.forEach(function (b) {
          b.y += b.vy;
          var col = b.sell ? "#ff4d5e" : "#b4ff39";
          ctx.globalAlpha = Math.max(0, 1 - b.y * 0.8);
          ctx.fillStyle = col;
          var bw = Math.min(f.W * 0.8, b.w * 3);
          ctx.fillRect(b.x * f.W - bw / 2, b.y * f.H, bw, 3);
          if (b.usd > 100000) {
            ctx.fillStyle = "#fff"; ctx.font = "8px ui-monospace,monospace"; ctx.textAlign = "center";
            ctx.fillText("$" + (b.usd / 1000).toFixed(0) + "K", b.x * f.W, b.y * f.H - 3);
          }
        });
        ctx.globalAlpha = 1;
        falls = falls.filter(function (b) { return b.y < 1.1; });
      }
    } catch (e) {}
    requestAnimationFrame(wireLoop);
  })();

  // ---- WARP tunnel (belakang teks SCAN LOG) ----
  var warp = [];
  (function warpLoop() {
    try {
      var cv = document.getElementById("warpCanvas");
      if (cv) {
        var f = fitCv(cv), ctx = f.ctx, i;
        ctx.setTransform(f.dpr, 0, 0, f.dpr, 0, 0);
        ctx.clearRect(0, 0, f.W, f.H);
        if (!warp.length) for (i = 0; i < 60; i++) warp.push({a: Math.random() * 7, r: Math.random(), sp: 0.004 + Math.random() * 0.012});
        var cx = f.W / 2, cy = f.H / 2, R = Math.max(f.W, f.H) / 2;
        warp.forEach(function (s) {
          s.r += s.sp;
          if (s.r > 1) { s.r = 0.02; s.a = Math.random() * 7; }
          var x0 = cx + Math.cos(s.a) * s.r * R, y0 = cy + Math.sin(s.a) * s.r * R;
          var r2 = Math.min(1, s.r + s.sp * 6);
          var x1 = cx + Math.cos(s.a) * r2 * R, y1 = cy + Math.sin(s.a) * r2 * R;
          ctx.strokeStyle = "rgba(180,255,57," + (0.05 + s.r * 0.3).toFixed(2) + ")";
          ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.stroke();
        });
      }
    } catch (e) {}
    requestAnimationFrame(warpLoop);
  })();
})();
