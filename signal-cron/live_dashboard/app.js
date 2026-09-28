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

    // rail pairs: grup TRADE penuh + WATCH ringkas (data real)
    var rail = "";
    var tm = (d.market || []).filter(function (m) { return m.trade; });
    var wm = (d.market || []).filter(function (m) { return !m.trade; });
    function card(m, compact) {
      var hot = m.dss4 <= 35, hotDn = m.dss4 >= 65;
      var lamp = hot ? "on" : (hotDn ? "warn" : "");
      var open = (d.positions || []).some(function (p) { return p.sym === m.sym; });
      var v = m.vol || 0;
      var vs = v >= 1e9 ? (v/1e9).toFixed(1)+"B" : (v >= 1e6 ? (v/1e6).toFixed(0)+"M" : (v/1e3).toFixed(0)+"K");
      return '<div class="pair"><span class="lamp ' + lamp + '"></span><span class="sym">' +
        m.sym.replace("USDT", "") + '</span><span class="px">$' +
        Number(m.price).toLocaleString("en-US", {maximumFractionDigits: m.price < 100 ? 3 : 1}) + "</span>" +
        '<div class="dssbar"><i style="width:' + Math.max(0, Math.min(100, m.dss4)) + '%;' +
        (m.dss4 >= 70 || m.dss4 <= 30 ? "background:var(--amber)" : "") + '"></i></div>' +
        '<div class="meta"><span>4H ' + m.dss4.toFixed(0) + (m.dss1 ? ' · 1D ' + m.dss1.toFixed(0) : "") +
        " · VOL " + vs + "</span><span>" + (open ? "IN POS" : (m.trade ? "FLAT" : "WATCH")) + "</span></div></div>";
    }
    tm.forEach(function (m) { rail += card(m); });
    if (wm.length) {
      rail += '<div class="meta" style="padding:4px 2px">— WATCH —</div>';
      wm.forEach(function (m) { rail += card(m); });
    }
    $("railPairs").innerHTML = rail;

    // openUsd untuk mood partikel (tabel tengah dihapus, pindah kanan)
    var openUsd = 0;
    (d.positions || []).forEach(function (p) {
      var r = (p.mark - p.entry) / p.entry;
      openUsd += r * eq * 0.05 * (a.leverage || 5);
    });

    // stream SCAN-LOG + trade tutup di atasnya (data real, terbaru di atas)
    var sc = "";
    (d.log || []).slice(-6).reverse().forEach(function (t) {
      var usd = t.pnl / 100 * eq;
      sc += '<div><span class="t">' + t.time + "</span><b>" + t.sym.replace("USDT", "") + " " +
        t.tf + " " + t.reason + '</b> <span class="' + (t.pnl >= 0 ? "up" : "dn") + '">' +
        money(usd) + "</span></div>";
    });
    (d.scan || []).forEach(function (s) {
      var skip = s.msg.indexOf("SKIP") >= 0;
      sc = '<div><span class="t">' + s.t + "</span>" +
        '<span class="' + (skip ? "dn" : "up") + '">' + s.msg + "</span></div>" + sc;
    });
    var si = document.getElementById("streamInner");
    if (si) si.innerHTML = sc || '<div style="color:var(--dim)">— memindai —</div>';
    // stream EXECUTION dihapus (digabung ke SCAN di atas); blok mati dibuang

    // mood partikel dari open pnl
    var mood = openUsd >= 0 ? 1 : -1;
    if (!(d.positions || []).length) mood = 0;
    // ringkas posisi kanan (data real)
    var p2 = "<tr><th>Sym</th><th>TF</th><th>PnL $</th></tr>";
    (d.positions || []).forEach(function (p) {
      var r = (p.mark - p.entry) / p.entry;
      var usd = r * eq * 0.05 * (a.leverage || 5);
      p2 += "<tr><td>" + p.sym.replace("USDT", "") + "</td><td>" + p.tf + '</td><td class="' +
        (usd >= 0 ? "up" : "dn") + '">' + money(usd) + "</td></tr>";
    });
    if (!(d.positions || []).length)
      p2 += '<tr><td colspan="3" style="text-align:center;color:var(--dim)">FLAT</td></tr>';
    var p2el = document.getElementById("posTable2");
    if (p2el) p2el.innerHTML = p2;
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
    var cv = $("crossCanvas"); if (!cv) return;
    var dpr = fit(cv), ctx = cv.getContext("2d");
    ctx.scale(dpr, dpr);
    var W = cv.width / dpr, H = cv.height / dpr;
    ctx.clearRect(0, 0, W, H);
    var keys = Object.keys(dx || {});
    if (!keys.length) {
      ctx.fillStyle = "#a7b39c"; ctx.font = "11px ui-monospace,monospace";
      ctx.fillText("menunggu feed…", 12, 20);
      return;
    }
    var cols = ["#b4ff39", "#00e5ff", "#ffb224", "#ff4d5e", "#c792ea", "#7fb3ff"];
    // zona 80/20 (area chart mulai di bawah judul agar tak tabrakan legenda)
    ctx.strokeStyle = "rgba(255,178,36,.25)"; ctx.setLineDash([4, 4]);
    [80, 20].forEach(function (z) {
      var y = 6 + (1 - z / 100) * (H - 26);
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
    });
    ctx.setLineDash([]);
    // titik cross antar garis (show-off dari data real)
    function crossAt(a, b) {
      var out = [];
      for (var i = 1; i < a.length && i < b.length; i++) {
        if ((a[i-1] <= b[i-1] && a[i] > b[i]) || (a[i-1] >= b[i-1] && a[i] < b[i])) out.push(i);
      }
      return out;
    }
    var series = keys.map(function (k) { return dx[k] || []; });
    // legenda horizontal di bawah (tak menutupi judul/panel)
    var lx0 = 8;
    keys.forEach(function (k, ki) {
      var col = cols[ki % cols.length];
      ctx.fillStyle = col;
      ctx.fillRect(lx0, H - 12, 14, 3);
      ctx.fillStyle = "#eef3e6"; ctx.font = "9px ui-monospace,monospace"; ctx.textAlign = "left";
      ctx.fillText(k, lx0 + 17, H - 3);
      lx0 += 17 + ctx.measureText(k).width + 12;
    });
    keys.forEach(function (k, ki) {
      var v = series[ki];
      if (v.length < 2) return;
      var col = cols[ki % cols.length];
      ctx.beginPath();
      v.forEach(function (val, i) {
        var x = 4 + i * (W - 8) / (v.length - 1);
        var y = 6 + (1 - Math.max(0, Math.min(100, val)) / 100) * (H - 26);
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      });
      ctx.strokeStyle = col; ctx.lineWidth = 1.6;
      ctx.shadowColor = col; ctx.shadowBlur = 7; ctx.stroke(); ctx.shadowBlur = 0;
    });
    // flash cross terbaru
    var pulse = 2 + Math.sin(Date.now() / 250) * 1.5;
    for (var a = 0; a < series.length; a++) {
      for (var b = a + 1; b < series.length; b++) {
        crossAt(series[a], series[b]).slice(-2).forEach(function (i) {
          var v = series[a];
          var x = 4 + i * (W - 8) / (v.length - 1);
          var y = 6 + (1 - Math.max(0, Math.min(100, v[i])) / 100) * (H - 26);
          ctx.beginPath(); ctx.arc(x, y, pulse + 1.5, 0, 7);
          ctx.fillStyle = "#ffffff"; ctx.fill();
        });
      }
    }
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
