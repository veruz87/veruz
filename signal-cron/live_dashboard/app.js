/* SIGNAL ROOM engine: data real dari live_data.json, visual show-off milik sendiri. */
(function () {
  var FEED = "../live_data.json";
  var parts = []; // particle field
  function $(id) { return document.getElementById(id); }
  function money(v) { return (v < 0 ? "-$" : "$") + Math.abs(v).toFixed(2); }

  function fit(cv) {
    var r = cv.getBoundingClientRect();
    var dpr = window.devicePixelRatio || 1;
    cv.width = Math.max(50, r.width * dpr); cv.height = Math.max(50, r.height * dpr);
    return dpr;
  }

  function render(d) {
    var a = d.account || {};
    var eq = a.equity || 0, start = a.startEquity || eq;
    var en = $("eqNum");
    en.textContent = "$" + eq.toLocaleString("en-US", {minimumFractionDigits: 2, maximumFractionDigits: 2});
    en.className = "v big" + (eq >= start ? "" : " neg");
    var n = a.totalTrades || 0;
    // stat equity SEJAJAR (label 11px, angka 19px, tanpa card)
    var es = $("eqStats");
    if (es) {
      function bx(k, v, cls) {
        return '<div class="eitem"><div class="k">' + k + '</div><div class="v ' + cls + '">' + v + "</div></div>";
      }
      es.innerHTML =
        bx("P&L", money(a.totalPnl || 0), (a.totalPnl || 0) >= 0 ? "up" : "dn") +
        bx("TRADES", n, "") +
        bx("WIN%", (a.winRate || 0).toFixed(1) + "%", "") +
        bx("VOL", "$" + Math.round(a.volUsd || 0).toLocaleString("en-US"), "") +
        bx("AVG/TRD", money(a.avgTrd || 0), (a.avgTrd || 0) >= 0 ? "up" : "dn") +
        bx("P.FACTOR", (a.profitFactor || 0).toFixed(2), "") +
        bx("MAX DD", (a.maxDd || 0).toFixed(1) + "%", (a.maxDd || 0) >= -5 ? "" : "dn");
    }
    // funding BTC header
    var fd = document.getElementById("fund");
    if (fd) {
      var fr = d.account ? d.account.funding : null;
      fd.textContent = (fr === null || fr === undefined) ? "FUND BTC —" :
        "FUND BTC " + (fr >= 0 ? "+" : "") + (fr * 100).toFixed(4) + "%";
    }
    $("clock").textContent = d.updated ? d.updated + " WIB" : "--:--:--";
    try {
      var bt = document.getElementById("buildTag");
      if (bt) bt.textContent = "build " + document.lastModified;
    } catch (e) {}

    // TOP MOVERS: 5 paling ekstrem + HEATMAP 21 tile (data real feed)
    var mk = (d.market || []).slice();
    function heat(m) {
      if (m.dss4 <= 30) return "background:rgba(0,229,255,.22);border-color:#00e5ff";
      if (m.dss4 >= 70) return "background:rgba(255,77,94,.22);border-color:#ff4d5e";
      return "background:rgba(180,255,57,.08);border-color:var(--line)";
    }
    mk.sort(function (a, b) { return Math.abs(b.dss4 - 50) - Math.abs(a.dss4 - 50); });
    var topHtml = "";
    mk.slice(0, 5).forEach(function (m) {
      var open = (d.positions || []).some(function (p) { return p.sym === m.sym; });
      topHtml += '<div class="pair hot" style="' + heat(m) + '"><span class="sym">' +
        m.sym.replace("USDT", "") + '</span><span class="px">' + m.dss4.toFixed(0) + "</span>" +
        '<div class="meta"><span>$' + Number(m.price).toLocaleString("en-US",
          {maximumFractionDigits: m.price < 100 ? 3 : 1}) + "</span>" +
        (open ? "<span>IN POS</span>" : "<span></span>") + "</div></div>";
    });
    var rt = document.getElementById("railTop");
    if (rt) rt.innerHTML = topHtml;
    var hg = "";
    (d.market || []).forEach(function (m) {
      hg += '<div class="tile" style="' + heat(m) + '"><b>' + m.sym.replace("USDT", "") +
        "</b><span>" + m.dss4.toFixed(0) + "</span></div>";
    });
    var hgel = document.getElementById("heatGrid");
    if (hgel) hgel.innerHTML = hg;

    // openUsd untuk mood partikel (tabel tengah dihapus, pindah kanan)
    var openUsd = 0;
    (d.positions || []).forEach(function (p) {
      var r = (p.mark - p.entry) / p.entry;
      openUsd += r * eq * 0.05 * (a.leverage || 5);
    });

    // SCAN-LOG teks dicabut: streamInner dimiliki ticker live (live.js).
    // Keputusan bot tetap ada di live_data.json (scan + log).
    // stream EXECUTION dihapus (digabung ke SCAN di atas); blok mati dibuang

    // mood partikel dari open pnl
    var mood = openUsd >= 0 ? 1 : -1;
    if (!(d.positions || []).length) mood = 0;
    // ringkas posisi kanan: entry statis, mark+pnl dihidupkan live.js tiap detik
    window.__posMeta = [];
    function fp(v) { return v < 1 ? v.toFixed(4) : (v < 100 ? v.toFixed(2) : v.toFixed(1)); }
    var p2 = "<tr><th>Sym</th><th>Entry</th><th>Mark</th><th>PnL $</th></tr>";
    (d.positions || []).forEach(function (p) {
      var r = (p.mark - p.entry) / p.entry;
      var usd = r * (p.dep || 0);
      var id = p.sym + "_" + p.tf;
      window.__posMeta.push({id: id, sym: p.sym, entry: p.entry, dep: p.dep || 0});
      p2 += "<tr><td>" + p.sym.replace("USDT", "") + "</td><td>" + fp(p.entry) +
        '</td><td id="mk' + id + '">' + fp(p.mark) + '</td><td id="pn' + id + '" class="' +
        (usd >= 0 ? "up" : "dn") + '">' + money(usd) + "</td></tr>";
    });
    if (!(d.positions || []).length)
      p2 += '<tr><td colspan="3" style="text-align:center;color:var(--dim)">FLAT</td></tr>';
    var p2el = document.getElementById("posTable2");
    if (p2el) {
      if ((d.positions || []).length) {
        p2el.innerHTML = p2;
      } else {
        p2el.innerHTML = "<tr><td colspan='4' style='text-align:center;color:var(--dim)'>STANDBY</td></tr>";
      }
    }
    // THE WIRE: whale + likuidasi real (data real feed)
    var wr = "";
    (d.wire || []).forEach(function (w) {
      var cls = w.msg.indexOf("WHALE BUY") >= 0 ? "whale-b" :
                (w.msg.indexOf("WHALE SELL") >= 0 ? "whale-s" : "liq");
      wr += '<div><span class="t">' + w.t + '</span><span class="' + cls + '">' + w.msg + "</span></div>";
    });
    var wel = document.getElementById("wireInner");
    if (wel) {
      wel.innerHTML = wr || '<div style="color:var(--dim)">— menyadap —</div>';
      var wp = document.getElementById("wire");
      if (wp) wp.scrollTop = wp.scrollHeight;
    }
    // expose untuk globe 3D (live.js): pair + posisi open
    window.__pairs = d.market || [];
    window.__posSyms = {};
    (d.positions || []).forEach(function (p) { window.__posSyms[p.sym] = 1; });
    // strip equity curve (data real feed)
    (function () {
      var cv = document.getElementById("eqCurve");
      if (!cv) return;
      var hist = d.equityCurve || [];
      var r = cv.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
      cv.width = Math.max(50, r.width * dpr); cv.height = Math.max(50, r.height * dpr);
      var ctx = cv.getContext("2d");
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      var W = r.width, H = r.height;
      ctx.clearRect(0, 0, W, H);
      if (hist.length < 2) {
        ctx.fillStyle = "#5f6f57"; ctx.font = "11px ui-monospace,monospace";
        ctx.fillText("menunggu riwayat…", 12, 20);
        return;
      }
      var mn = Math.min.apply(null, hist), mx = Math.max.apply(null, hist), rg = (mx - mn) || 1;
      var up = hist[hist.length - 1] >= hist[0];
      var col = up ? "#b4ff39" : "#ff4d5e";
      var grad = ctx.createLinearGradient(0, 0, 0, H);
      grad.addColorStop(0, up ? "rgba(180,255,57,.35)" : "rgba(255,77,94,.35)");
      grad.addColorStop(1, "rgba(0,0,0,0)");
      ctx.beginPath();
      hist.forEach(function (v, i) {
        var x = 4 + i * (W - 8) / (hist.length - 1);
        var y = 5 + (1 - (v - mn) / rg) * (H - 10);
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      });
      ctx.strokeStyle = col; ctx.lineWidth = 1.8;
      ctx.shadowColor = col; ctx.shadowBlur = 8; ctx.stroke(); ctx.shadowBlur = 0;
      ctx.lineTo(W - 4, H); ctx.lineTo(4, H); ctx.closePath();
      ctx.fillStyle = grad; ctx.fill();
      ctx.fillStyle = "#eef3e6"; ctx.font = "10px ui-monospace,monospace"; ctx.textAlign = "left";
      ctx.fillText("$" + hist[hist.length - 1].toFixed(2), 8, 14);
    })();
    drawBtc(window.__liveBtc || d.btc1m || []);
    drawCross(window.__liveDss || d.dssX || {});
    seedField(mood, (d.positions || []).length, d.market || []);
  }

  function drawBtc(bars) {
    var cv = $("btcCanvas"); if (!cv) return;
    var dpr = fit(cv), ctx = cv.getContext("2d");
    ctx.scale(dpr, dpr);
    var W = cv.width / dpr, H = cv.height / dpr;
    ctx.clearRect(0, 0, W, H);
    if (!bars.length) {
      ctx.fillStyle = "#5f6f57"; ctx.font = "11px ui-monospace,monospace";
      ctx.fillText("menunggu feed 1m…", 12, 20);
      return;
    }
    var mn = Infinity, mx = -Infinity, i, b;
    for (i = 0; i < bars.length; i++) {
      b = bars[i];
      if (b.l < mn) mn = b.l;
      if (b.h > mx) mx = b.h;
    }
    var rg = (mx - mn) || 1;
    var n = bars.length, bw = Math.max(2, (W - 8) / n * 0.62);
    for (i = 0; i < n; i++) {
      b = bars[i];
      var x = 4 + i * (W - 8) / n;
      var yo = 6 + (1 - (b.o - mn) / rg) * (H - 12);
      var yh = 6 + (1 - (b.h - mn) / rg) * (H - 12);
      var yl = 6 + (1 - (b.l - mn) / rg) * (H - 12);
      var yc = 6 + (1 - (b.c - mn) / rg) * (H - 12);
      var up = b.c >= b.o;
      ctx.strokeStyle = up ? "#b4ff39" : "#ff4d5e";
      ctx.fillStyle = up ? "#b4ff39" : "#ff4d5e";
      ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(x + bw / 2, yh); ctx.lineTo(x + bw / 2, yl); ctx.stroke();
      var y0 = Math.min(yo, yc);
      ctx.fillRect(x, y0, bw, Math.max(1, Math.abs(yc - yo)));
    }
    // harga terakhir + garis (show-off)
    var last = bars[n-1].c;
    var ly = 6 + (1 - (last - mn) / rg) * (H - 12);
    ctx.strokeStyle = "rgba(255,178,36,.7)"; ctx.setLineDash([4, 3]);
    ctx.beginPath(); ctx.moveTo(0, ly); ctx.lineTo(W, ly); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle = "#ffb224"; ctx.font = "11px ui-monospace,monospace";
    ctx.fillText(last.toFixed(1), W - 62, ly - 5);
  }

  function drawCross(dx) {
    window.__radarDx = dx || {};
  }

  function seedField(mood, nPos, market) {
    var cv = $("field"); if (!cv) return;
    // node plexus per pair: ukuran = volume real, gerak Brownian, koneksi saat dekat
    var mk = (market || []).map(function (m) { return m.sym; }).join(",");
    if (!seedField._k || seedField._k !== mk || !parts.length) {
      seedField._k = mk;
      parts = (market || []).map(function (m, i) {
        return {x: Math.random(), y: Math.random(), vx: (Math.random()-0.5)*0.0009,
                vy: (Math.random()-0.5)*0.0009, sym: m.sym, pair: true};
      });
      for (var i = 0; i < 40; i++) parts.push({x: Math.random(), y: Math.random(),
        vx: (Math.random()-0.5)*0.0012, vy: (Math.random()-0.5)*0.0012, pair: false});
    }
    // sinkron volume + status
    var vmax = 1;
    (market || []).forEach(function (m) { vmax = Math.max(vmax, m.vol || 0); });
    parts.forEach(function (p) {
      if (!p.pair) return;
      var m = null;
      (market || []).forEach(function (x) { if (x.sym === p.sym) m = x; });
      p.m = m;
      p.r = m ? (7 + 16 * Math.log(1 + (m.vol || 0) / (vmax || 1) * 9) / Math.log(10)) : 7;
    });
    var dpr = fit(cv), ctx = cv.getContext("2d");
    ctx.scale(dpr, dpr);
    var W = cv.width / dpr, H = cv.height / dpr;
    ctx.clearRect(0, 0, W, H);
    var pts = parts.map(function (p) {
      p.x += p.vx; p.y += p.vy;
      if (p.x < 0 || p.x > 1) p.vx *= -1;
      if (p.y < 0 || p.y > 1) p.vy *= -1;
      return {x: p.x * W, y: p.y * H, p: p};
    });
    // koneksi (show-off)
    ctx.lineWidth = 1;
    for (var i = 0; i < pts.length; i++) {
      for (var j = i + 1; j < pts.length; j++) {
        var dx = pts[i].x - pts[j].x, dy = pts[i].y - pts[j].y;
        var dd = Math.sqrt(dx * dx + dy * dy);
        if (dd < 90) {
          ctx.strokeStyle = "rgba(180,255,57," + (0.22 * (1 - dd / 90)).toFixed(2) + ")";
          ctx.beginPath(); ctx.moveTo(pts[i].x, pts[i].y); ctx.lineTo(pts[j].x, pts[j].y); ctx.stroke();
        }
      }
    }
    pts.forEach(function (q) {
      var col = "#b4ff39", rr = 2;   // bola seragam lime (warna teks SIGNAL ROOM)
      if (q.p.pair && q.p.m) {
        rr = q.p.r || 6;
      }
      ctx.beginPath(); ctx.arc(q.x, q.y, rr, 0, 7);
      ctx.fillStyle = col; ctx.shadowColor = col; ctx.shadowBlur = q.p.pair ? 12 : 0; ctx.fill();
      ctx.shadowBlur = 0;
      if (q.p.pair) {
      ctx.fillStyle = "#ffffff"; ctx.font = "9px ui-monospace,monospace"; ctx.textAlign = "center";
      ctx.fillText(q.p.sym.replace("USDT", ""), q.x, q.y + rr + 10);
      }
    });
    requestAnimationFrame(function () { seedField(mood, nPos, market); });
  }

  function poll() {
    fetch("../live_data.json?_=" + Date.now())
      .then(function (r) { return r.json(); })
      .then(function (d) {
        render(d);
        document.getElementById("feeddot").textContent = "● FEED";
      })
      .catch(function () {
        var f = document.getElementById("feeddot");
        if (f) f.textContent = "○ WAITING";
      });
  }
  function tickClock() {
    var now = new Date();
    var el = document.getElementById("clock");
    var wib = new Date(now.getTime() + 7 * 3600 * 1000);
    function p(n) { return (n < 10 ? "0" : "") + n; }
    if (el) el.textContent = p(wib.getHours()) + ":" + p(wib.getMinutes()) + ":" + p(wib.getSeconds()) + " WIB";
  }
  poll();
  setInterval(poll, 30000);
  tickClock();
  setInterval(tickClock, 1000);
})();
