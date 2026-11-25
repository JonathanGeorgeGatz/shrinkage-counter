// The Shrinkage Counter — SECOND BUILD (after prompt 2), kept verbatim for the episode.
// Prompt 2 fixed the netting: every SKU now keeps its own ledger. What the independent checker
// later caught, still in here exactly as built:
//   * no count window: the drill delivery that arrived THE DAY AFTER the second count is added
//     to expected stock, so the page accuses the shop of losing sixteen drills instead of six;
//   * no duplicate-reference check: the screws delivery keyed in twice doubles expected stock,
//     and ten boxes that never existed join the missing list;
//   * a movement whose SKU is not on the count sheet gets a brand-new ledger starting at zero,
//     and with no second count its "expected" goes negative — so the page reports a SURPLUS of
//     eighteen units of a product it never counted;
//   * recorded write-offs are subtracted from expected AND listed again under "stolen or lost",
//     so the six cans of stain the shop wrote off honestly are billed as theft on top;
//   * floats and toFixed everywhere.
(function (root) {
  "use strict";
  function rows(text) { return text.split(/\r?\n/).filter(l => l.trim()).map(l => l.split(",")); }
  function num(s) { const v = parseFloat(String(s || "").replace(/[$,]/g, "")); return isNaN(v) ? null : v; }

  function audit(countsCsv, movesCsv) {
    const c = rows(countsCsv), m = rows(movesCsv);
    const chh = c[0].map(s => s.trim().toLowerCase());
    const mh = m[0].map(s => s.trim().toLowerCase());
    const ci = n => chh.indexOf(n), mi = n => mh.indexOf(n);
    const led = {};   // sku -> {item, cost, first, second, net, writeoff}
    for (let r = 1; r < c.length; r++) {
      const sku = (c[r][ci("sku")] || "").trim();
      const f = num(c[r][ci("first count")]), s2 = num(c[r][ci("second count")]);
      if (!sku || f === null || s2 === null) continue;    // still silently skipped
      led[sku] = { sku, item: (c[r][ci("item")] || "").trim(), cost: num(c[r][ci("unit cost")]) || 0,
        first: f, second: s2, net: 0, writeoff: 0 };      // a duplicate row quietly overwrites
    }
    for (let r = 1; r < m.length; r++) {
      const sku = (m[r][mi("sku")] || "").trim();
      const t = (m[r][mi("type")] || "").trim().toLowerCase();
      const q = num(m[r][mi("qty")]);
      if (!sku || q === null) continue;
      if (!led[sku]) led[sku] = { sku, item: "(from movements)", cost: 0, first: 0, second: 0, net: 0, writeoff: 0 };
      if (t === "sale") led[sku].net -= q;
      else if (t === "writeoff") { led[sku].net -= q; led[sku].writeoff += q; }
      else led[sku].net += q;                             // received, return, unknown types too
    }
    const lost = [], surplus = [];
    let lostValue = 0, surplusUnits = 0;
    for (const k of Object.keys(led)) {
      const L = led[k];
      const expected = L.first + L.net;
      const v = L.second - expected;
      const stolenOrLost = Math.max(0, -v) + L.writeoff;  // the double-dip
      if (stolenOrLost > 0) {
        lost.push({ sku: L.sku, item: L.item, units: stolenOrLost, value: +(stolenOrLost * L.cost).toFixed(2) });
        lostValue += stolenOrLost * L.cost;
      } else if (v > 0) {
        surplus.push({ sku: L.sku, item: L.item, units: v });
        surplusUnits += v;
      }
    }
    lost.sort((a, b) => b.value - a.value);
    return { lost, surplus, lostValue: +lostValue.toFixed(2), surplusUnits,
      verdict: "Stolen or lost: $" + lostValue.toFixed(2) + " across " + lost.length + " products." };
  }
  root.SC_V2 = { audit };
})(typeof window !== "undefined" ? window : (typeof module !== "undefined" ? module.exports : this));
