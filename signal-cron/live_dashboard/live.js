/* LIVE browser visuals: Binance public API langsung (tanpa key).
   Strategi/state tetap dari live_data.json (cron 15 mnt). File ini murni visual. */
(function () {
  var API = "https://data-api.binance.vision";
  var SYM = "BTCUSDT";
  var DSS_SYMS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT"];

  function jget(url, cb) {
    fetch(url).then(function (r) { return r.json(); }).then(cb).catch(function () {});
  }

  // (bola 3D dicabut dari ORBIT: diganti neural burst)

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

  pullKlines(); pullDss();

  // ---- IRIS RING (panel LIVE FEED): cincin partikel + tick vol real ----
  var iris = [], it;
  for (it = 0; it < 380; it++) {
    var band = Math.random();
    iris.push({a: Math.random() * Math.PI * 2,
               r: band < 0.62 ? 0.30 + Math.random() * 0.05 : (band < 0.85 ? 0.42 + Math.random() * 0.1 : 0.55 + Math.random() * 0.2),
               sp: 0.002 + Math.random() * 0.006, sz: 0.8 + Math.random() * 1.8});
  }
  var irisVol = 0, irisTicks = [];
  setInterval(function () {
    jget(API + "/api/v3/ticker/price?symbol=" + SYM, function (t) {
      if (!t || !t.price) return;
      irisTicks.push(parseFloat(t.price));
      if (irisTicks.length > 30) irisTicks.shift();
      var s = 0, j;
      for (j = 1; j < irisTicks.length; j++) s += Math.abs(Math.log(irisTicks[j] / irisTicks[j - 1]));
      irisVol = Math.max(0, Math.min(1, (s / irisTicks.length) * 1600));
    });
  }, 2000);
  (function irisLoop() {
    try {
      var cv = document.getElementById("globeMain");
      if (cv) {
        var f = fitCv(cv), ctx = f.ctx;
        ctx.setTransform(f.dpr, 0, 0, f.dpr, 0, 0);
        var W = f.W, H = f.H;
        ctx.fillStyle = "rgba(0,0,0,.3)";
        ctx.fillRect(0, 0, W, H);
        var cx = W / 2, cy = H / 2, R = Math.min(W, H) * 0.42;
        var rot = Date.now() / 1000 * (0.12 + irisVol * 0.5), j;
        // crosshair + tick ring
        ctx.strokeStyle = "rgba(255,255,255,.12)";
        ctx.beginPath(); ctx.moveTo(cx - R * 1.15, cy); ctx.lineTo(cx + R * 1.15, cy);
        ctx.moveTo(cx, cy - R * 1.15); ctx.lineTo(cx, cy + R * 1.15); ctx.stroke();
        for (j = 0; j < 48; j++) {
          var ta = j / 48 * Math.PI * 2, big = j % 12 === 0;
          ctx.strokeStyle = big ? "rgba(255,255,255,.4)" : "rgba(255,255,255,.12)";
          ctx.beginPath();
          ctx.moveTo(cx + Math.cos(ta) * R * 1.08, cy + Math.sin(ta) * R * 1.08);
          ctx.lineTo(cx + Math.cos(ta) * R * (big ? 1.18 : 1.13), cy + Math.sin(ta) * R * (big ? 1.18 : 1.13));
          ctx.stroke();
        }
        // lubang tengah
        var grd = ctx.createRadialGradient(cx, cy, R * 0.1, cx, cy, R * 0.3);
        grd.addColorStop(0, "rgba(0,0,0,0)");
        grd.addColorStop(1, "rgba(0,0,0,.85)");
        ctx.fillStyle = grd;
        ctx.beginPath(); ctx.arc(cx, cy, R * 0.3, 0, 7); ctx.fill();
        ctx.strokeStyle = "rgba(255,255,255,.25)";
        ctx.beginPath(); ctx.arc(cx, cy, R * 0.3, 0, 7); ctx.stroke();
        // partikel cincin (monokrom, tebal ikut volatilitas)
        iris.forEach(function (p) {
          p.a += p.sp * (1 + irisVol * 3);
          var rr = p.r * (1 + Math.sin(Date.now() / 900 + p.a * 3) * 0.02 * (1 + irisVol * 2));
          var x = cx + Math.cos(p.a) * rr * R * 1.35;
          var y = cy + Math.sin(p.a) * rr * R * 1.35;
          if (x < -10 || x > W + 10 || y < -10 || y > H + 10) return;
          var al = 0.25 + (rr - 0.28) * 1.6;
          ctx.fillStyle = "rgba(240,240,240," + Math.max(0.1, Math.min(0.9, al)).toFixed(2) + ")";
          var sz = p.sz * (1 + irisVol * 1.5);
          ctx.fillRect(x, y, sz, sz);
        });
        ctx.fillStyle = "rgba(238,243,230,.85)"; ctx.font = "9px ui-monospace,monospace"; ctx.textAlign = "left";
        ctx.fillText("IRIS · " + SYM.replace("USDT", ""), 10, H - 10);
      }
    } catch (err) {}
    requestAnimationFrame(irisLoop);
  })();
  setInterval(pullKlines, 15000);
  setInterval(pullDss, 30000);

  // ---- NEURAL BURST (panel NEURAL): tiap trade real = ledakan neuron ----
  var neurons = [], sparks = [], labels = [], energy = 0.3, ni;
  for (ni = 0; ni < 26; ni++) {
    var ring = ni % 2 ? 0.32 : 0.2, aa = (ni / 26) * Math.PI * 2;
    neurons.push({a: aa, r: ring, sp: 0.0016 + Math.random() * 0.002, sz: 2 + Math.random() * 2.5});
  }
  setInterval(function () {
    jget(API + "/api/v3/aggTrades?symbol=" + SYM + "&limit=20", function (t) {
      if (!t || !t.length) return;
      t.forEach(function (x) {
        if ((window.__nLast || 0) >= x.a) return;
        window.__nLast = Math.max(window.__nLast || 0, x.a);
        var usd = parseFloat(x.q) * parseFloat(x.p);
        var big = usd >= 50000;
        energy = Math.min(1.4, energy + (big ? 0.5 : 0.06 + Math.min(0.2, usd / 200000)));
        var n = big ? 26 : 6;
        for (var j = 0; j < n; j++) {
          var va = Math.random() * Math.PI * 2, vv = 0.008 + Math.random() * (big ? 0.05 : 0.02);
          sparks.push({x: 0.5, y: 0.5, vx: Math.cos(va) * vv, vy: Math.sin(va) * vv,
                       life: 1, sell: !!x.m, big: big});
        }
        if (sparks.length > 260) sparks = sparks.slice(-260);
        if (big) labels.push({t: "$" + (usd / 1000).toFixed(0) + "K " + (x.m ? "SELL" : "BUY"), life: 1});
      });
    });
  }, 2000);

  // ---- TERRAIN ombak 3D tick-real (panel LIVE FEED): scroll cepat ----
  // (dicabut: diganti neural burst)
  (function neuralLoop() {
    try {
      var cv = document.getElementById("crossCanvas");
      if (cv) {
        var f = fitCv(cv), ctx = f.ctx;
        ctx.setTransform(f.dpr, 0, 0, f.dpr, 0, 0);
        var W = f.W, H = f.H;
        ctx.fillStyle = "rgba(0,0,0,.3)";
        ctx.fillRect(0, 0, W, H);
        var cx = W / 2, cy = H / 2, R = Math.min(W, H) * 0.34;
        energy = Math.max(0.12, energy * 0.985);
        var j, k;
        // posisi neuron mengorbit
        var pts = neurons.map(function (p) {
          p.a += p.sp * (0.5 + energy);
          return {x: cx + Math.cos(p.a) * R * p.r * 2.4, y: cy + Math.sin(p.a * 1.3) * R * p.r * 1.4, sz: p.sz};
        });
        // koneksi antar neuron dekat
        ctx.lineWidth = 1;
        for (j = 0; j < pts.length; j++) {
          for (k = j + 1; k < pts.length; k++) {
            var dx = pts[j].x - pts[k].x, dy = pts[j].y - pts[k].y;
            var dd = Math.sqrt(dx * dx + dy * dy);
            if (dd < R * 0.9) {
              ctx.strokeStyle = "rgba(255,140,40," + (0.22 * (1 - dd / (R * 0.9)) * (0.5 + energy)).toFixed(2) + ")";
              ctx.beginPath(); ctx.moveTo(pts[j].x, pts[j].y); ctx.lineTo(pts[k].x, pts[k].y); ctx.stroke();
            }
          }
          // hub -> neuron
          ctx.strokeStyle = "rgba(255,180,60," + (0.1 + energy * 0.25).toFixed(2) + ")";
          ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(pts[j].x, pts[j].y); ctx.stroke();
        }
        // hub
        var pulse = 6 + Math.sin(Date.now() / 180) * 2 + energy * 10;
        ctx.beginPath(); ctx.arc(cx, cy, pulse, 0, 7);
        ctx.fillStyle = "#ffb03a"; ctx.shadowColor = "#ff7a1a"; ctx.shadowBlur = 20 + energy * 30; ctx.fill();
        ctx.shadowBlur = 0;
        // neuron
        pts.forEach(function (q) {
          ctx.beginPath(); ctx.arc(q.x, q.y, q.sz + energy * 2, 0, 7);
          ctx.fillStyle = "#ffd9a0"; ctx.shadowColor = "#ff9a2e"; ctx.shadowBlur = 6 + energy * 10; ctx.fill();
          ctx.shadowBlur = 0;
        });
        // ledakan spark trade
        sparks.forEach(function (s) {
          s.x += s.vx; s.y += s.vy; s.vx *= 0.985; s.vy *= 0.985; s.life -= 0.012;
          ctx.globalAlpha = Math.max(0, s.life);
          ctx.fillStyle = s.sell ? "#ff4d5e" : "#b4ff39";
          ctx.beginPath(); ctx.arc(s.x * W, s.y * H, s.big ? 3 : 1.8, 0, 7); ctx.fill();
        });
        ctx.globalAlpha = 1;
        sparks = sparks.filter(function (s) { return s.life > 0; });
        // label whale melayang
        labels.forEach(function (L, ix) {
          L.life -= 0.008;
          ctx.globalAlpha = Math.max(0, L.life);
          ctx.fillStyle = "#fff"; ctx.font = "bold 11px ui-monospace,monospace"; ctx.textAlign = "center";
          ctx.fillText(L.t, cx, cy - R * 0.9 - (1 - L.life) * 30);
        });
        ctx.globalAlpha = 1;
        labels = labels.filter(function (L) { return L.life > 0; });
        ctx.fillStyle = "rgba(238,243,230,.85)"; ctx.font = "9px ui-monospace,monospace"; ctx.textAlign = "left";
        ctx.fillText("NEURAL · " + sparks.length + " sparks", 10, H - 10);
      }
    } catch (err) {}
    requestAnimationFrame(neuralLoop);
  })();

  // ---- util kanvas ----
  function fitCv(cv) {
    var r = cv.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
    cv.width = Math.max(50, r.width * dpr); cv.height = Math.max(50, r.height * dpr);
    return {ctx: cv.getContext("2d"), dpr: dpr, W: r.width, H: r.height};
  }

  // (radar dicabut: crossCanvas dipakai bola 3D)

  // ---- POSISI live: mark+pnl tiap 4 detik dari ticker browser ----
  function fpl(v) { return v < 1 ? v.toFixed(4) : (v < 100 ? v.toFixed(2) : v.toFixed(1)); }
  function moneyL(v) { return (v < 0 ? "-$" : "$") + Math.abs(v).toFixed(2); }
  setInterval(function () {
    var meta = window.__posMeta || [];
    if (!meta.length) return;
    jget(API + "/api/v3/ticker/price", function (all) {
      if (!all || !all.length) return;
      var px = {};
      all.forEach(function (t) { px[t.symbol] = parseFloat(t.price); });
      meta.forEach(function (p) {
        var mk = document.getElementById("mk" + p.id), pn = document.getElementById("pn" + p.id);
        if (!mk || !pn || !px[p.sym]) return;
        var r = (px[p.sym] - p.entry) / p.entry, usd = r * p.dep;
        mk.textContent = fpl(px[p.sym]);
        pn.textContent = moneyL(usd);
        pn.className = usd >= 0 ? "up" : "dn";
      });
    });
  }, 4000);
  var TAPE = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"], tapeLast = {}, tapeQ = [];
  setInterval(function () {
    TAPE.forEach(function (s) {
      jget(API + "/api/v3/aggTrades?symbol=" + s + "&limit=6", function (t) {
        if (!t || !t.length) return;
        t.forEach(function (x) {
          if ((tapeLast[s] || 0) >= x.a) return;
          tapeLast[s] = Math.max(tapeLast[s] || 0, x.a);
          var usd = parseFloat(x.q) * parseFloat(x.p);
          var big = usd >= 50000 ? " <b>WHALE</b>" : "";
          tapeQ.push({s: s, m: !!x.m, p: parseFloat(x.p), usd: usd, big: big, a: x.a});
        });
        if (tapeQ.length > 60) tapeQ = tapeQ.slice(-60);
      });
    });
  }, 1000);
  // konsumen: 1 baris per 250ms -> turun berurutan, bukan lompat
  setInterval(function () {
    var si = document.getElementById("streamInner");
    if (!si || !tapeQ.length) return;
    var x = tapeQ.shift();
    var tmp = document.createElement("div");
    tmp.innerHTML = '<div class="trow fresh"><span class="t">' + x.s.replace("USDT", "") + "</span>" +
      '<span class="' + (x.m ? "dn" : "up") + '">' + x.p.toLocaleString("en-US") +
      "</span> $" + (x.usd >= 1000 ? (x.usd / 1000).toFixed(1) + "K" : x.usd.toFixed(0)) + x.big + "</div>";
    si.insertBefore(tmp.firstChild, si.firstChild);
    while (si.children.length > 40) si.removeChild(si.lastChild);
  }, 250);
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
