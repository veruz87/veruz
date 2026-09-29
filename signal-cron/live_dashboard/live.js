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

  // ---- ORBITAL MIND (panel LIVE FEED ala GROK): orbit warna + inti emas ----
  var orbTicks = [], orbPulse = 0, orbWhales = [];
  setInterval(function () {
    jget(API + "/api/v3/ticker/price?symbol=" + SYM, function (t) {
      if (!t || !t.price) return;
      orbTicks.push(parseFloat(t.price));
      if (orbTicks.length > 40) orbTicks.shift();
    });
    jget(API + "/api/v3/aggTrades?symbol=" + SYM + "&limit=10", function (tr) {
      if (!tr || !tr.length) return;
      tr.forEach(function (x) {
        var usd = parseFloat(x.q) * parseFloat(x.p);
        if (usd >= 100000) {
          orbPulse = Math.min(1.5, orbPulse + 0.7);
          orbWhales.push({t: Date.now(), usd: usd, sell: !!x.m});
        }
      });
      if (orbWhales.length > 6) orbWhales = orbWhales.slice(-6);
    });
  }, 2000);
  var ORBITS = [
    {c: "#b4ff39", rx: 1.0, ry: 0.34, tilt: 0.25, sp: 0.11},
    {c: "#00e5ff", rx: 0.88, ry: 0.42, tilt: -0.35, sp: -0.09},
    {c: "#ffffff", rx: 0.76, ry: 0.3, tilt: 0.5, sp: 0.13},
    {c: "#ffb03a", rx: 0.64, ry: 0.5, tilt: -0.15, sp: -0.12},
    {c: "#ff4d5e", rx: 0.54, ry: 0.36, tilt: 0.4, sp: 0.15},
    {c: "#c792ea", rx: 0.44, ry: 0.46, tilt: -0.45, sp: -0.1},
    {c: "#7fb3ff", rx: 0.34, ry: 0.34, tilt: 0.1, sp: 0.17}
  ];
  var orbDots = [];
  ORBITS.forEach(function (o, ix) {
    for (var j = 0; j < 6; j++) orbDots.push({o: ix, a: Math.random() * Math.PI * 2, sz: 1.5 + Math.random() * 2});
  });
  (function orbitalLoop() {
    try {
      var cv = document.getElementById("globeMain");
      if (cv) {
        var f = fitCv(cv), ctx = f.ctx;
        ctx.setTransform(f.dpr, 0, 0, f.dpr, 0, 0);
        var W = f.W, H = f.H;
        // jejak gerak (motion trail) ala video
        ctx.fillStyle = "rgba(4,6,4,.32)";
        ctx.fillRect(0, 0, W, H);
        var cx = W / 2, cy = H / 2, RX = W * 0.44, RY = H * 0.44;
        orbPulse = Math.max(0, orbPulse * 0.97);
        var t = Date.now() / 1000;
        // rel orbit penuhi panel
        ORBITS.forEach(function (o, ix) {
          ctx.save();
          ctx.translate(cx, cy);
          ctx.rotate(o.tilt);
          ctx.strokeStyle = o.c;
          ctx.globalAlpha = 0.3;
          ctx.setLineDash([2, 5]);
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.ellipse(0, 0, RX * o.rx, RY * o.rx, 0, 0, 7);
          ctx.stroke();
          ctx.setLineDash([]);
          ctx.restore();
        });
        // titik pejalan + kelip
        orbDots.forEach(function (d) {
          var o = ORBITS[d.o];
          d.a += o.sp * 0.03 * (1 + orbPulse);
          var ex = Math.cos(d.a) * RX * o.rx, ey = Math.sin(d.a) * RY * o.rx;
          var x = cx + ex * Math.cos(o.tilt) - ey * Math.sin(o.tilt);
          var y = cy + ex * Math.sin(o.tilt) + ey * Math.cos(o.tilt);
          var tw = 0.6 + 0.4 * Math.sin(t * 5 + d.a * 7);
          ctx.globalAlpha = 0.95;
          ctx.fillStyle = o.c;
          ctx.shadowColor = o.c; ctx.shadowBlur = 10;
          ctx.beginPath(); ctx.arc(x, y, d.sz * tw + orbPulse, 0, 7); ctx.fill();
          ctx.shadowBlur = 0;
        });
        ctx.globalAlpha = 1;
        // inti emas berdenyut
        var pr = Math.min(RX, RY) * 0.22 * (1 + orbPulse * 0.8 + Math.sin(t * 3) * 0.07);
        var g = ctx.createRadialGradient(cx, cy, 1, cx, cy, pr * 3.2);
        g.addColorStop(0, "rgba(255,220,150,.95)");
        g.addColorStop(0.35, "rgba(255,170,60,.55)");
        g.addColorStop(1, "rgba(255,140,30,0)");
        ctx.fillStyle = g;
        ctx.beginPath(); ctx.arc(cx, cy, pr * 3.2, 0, 7); ctx.fill();
        ctx.fillStyle = "#ffe9c4";
        ctx.beginPath(); ctx.arc(cx, cy, pr * 0.55, 0, 7); ctx.fill();
        // label whale terbaru
        var now = Date.now();
        orbWhales = orbWhales.filter(function (s) { return now - s.t < 15000; });
        orbWhales.forEach(function (s, ix) {
          var age = (now - s.t) / 15000;
          ctx.globalAlpha = 1 - age;
          ctx.fillStyle = s.sell ? "#ff4d5e" : "#b4ff39";
          ctx.font = "bold 10px ui-monospace,monospace"; ctx.textAlign = "right";
          ctx.fillText("$" + (s.usd / 1000).toFixed(0) + "K", W - 10, 20 + ix * 16);
          ctx.globalAlpha = 1;
        });
        // HUD sudut: harga + meter energi
        var last = orbTicks.length ? orbTicks[orbTicks.length - 1] : 0;
        ctx.fillStyle = "#eef3e6"; ctx.font = "bold 14px ui-monospace,monospace"; ctx.textAlign = "left";
        ctx.fillText(last ? last.toLocaleString("en-US") : "BTC", 10, 22);
        ctx.fillStyle = "rgba(238,243,230,.6)"; ctx.font = "9px ui-monospace,monospace";
        var eb = Math.round(orbPulse * 100);
        ctx.fillText("NRG " + eb + "%", 10, H - 10);
        ctx.fillStyle = "rgba(180,255,57,.5)";
        ctx.fillRect(10, H - 7, 60 * Math.min(1, orbPulse), 2);
      }
    } catch (err) {}
    requestAnimationFrame(orbitalLoop);
  })();
  setInterval(pullKlines, 15000);
  setInterval(pullDss, 30000);

  // (neural burst pindah ke three-globe.js? tidak — dicabut, diganti globe 3D)

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
