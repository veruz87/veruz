/* LIVE browser visuals: Binance public API langsung (tanpa key).
   Strategi/state tetap dari live_data.json (cron 15 mnt). File ini murni visual. */
(function () {
  var API = "https://data-api.binance.vision";
  var SYM = "BTCUSDT";
  var DSS_SYMS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT"];

  function jget(url, cb) {
    fetch(url).then(function (r) { return r.json(); }).then(cb).catch(function () {});
  }

  // ---- depth order book -> panel LIVE FEED ----
  function drawDepth() {
    jget(API + "/api/v3/depth?symbol=" + SYM + "&limit=15", function (d) {
      if (!d || !d.asks || !d.bids) return;
      var asks = d.asks.slice().reverse(), bids = d.bids;
      var mx = 0, i;
      for (i = 0; i < asks.length; i++) mx = Math.max(mx, parseFloat(asks[i][1]));
      for (i = 0; i < bids.length; i++) mx = Math.max(mx, parseFloat(bids[i][1]));
      if (mx <= 0) mx = 1;
      function row(p, q, cls) {
        var w = Math.max(2, parseFloat(q) / mx * 100);
        return '<div class="drow ' + cls + '"><span class="dp">' + parseFloat(p).toFixed(1) +
          '</span><span class="dbar"><i style="width:' + w.toFixed(1) + '%"></i></span>' +
          '<span class="dq">' + parseFloat(q).toFixed(3) + "</span></div>";
      }
      var ha = "", hb = "";
      for (i = 0; i < asks.length; i++) ha += row(asks[i][0], asks[i][1], "ask");
      for (i = 0; i < bids.length; i++) hb += row(bids[i][0], bids[i][1], "bid");
      var a = document.getElementById("depthAsk"), b = document.getElementById("depthBid");
      if (a) a.innerHTML = ha;
      if (b) b.innerHTML = hb;
      var bestA = parseFloat(d.asks[d.asks.length - 1][0]),
          bestB = parseFloat(d.bids[0][0]),
          mid = document.getElementById("depthMid");
      if (mid) mid.textContent = bestB.toFixed(1) + " / " + bestA.toFixed(1) +
        "  ·  spread " + (bestA - bestB).toFixed(1);
    });
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

  drawDepth(); pullKlines(); pullDss();
  setInterval(drawDepth, 3000);
  setInterval(pullKlines, 15000);
  setInterval(pullDss, 30000);
})();
