// The Shrinkage Counter — FIRST BUILD (prompt 1), kept verbatim for the episode.
// Its sins, exactly as the naive build made them:
//   * ONE ledger for the whole store: every count and every movement summed into store totals,
//     so a surplus on one shelf CANCELS missing units on another — the store "nets out";
//   * no SKU matching, no count window, no duplicate-reference check: every row that parses is
//     believed, including the delivery that arrived after the second count and the delivery
//     keyed in twice;
//   * floats and toFixed; rows that don't parse are silently skipped;
//   * the verdict is an "accuracy" percentage with a compliment attached.
(function (root) {
  "use strict";
  function rows(text) { return text.split(/\r?\n/).filter(l => l.trim()).map(l => l.split(",")); }
  function num(s) { const v = parseFloat(String(s || "").replace(/[$,]/g, "")); return isNaN(v) ? null : v; }

  function audit(countsCsv, movesCsv) {
    const c = rows(countsCsv), m = rows(movesCsv);
    const chh = c[0].map(s => s.trim().toLowerCase());
    const mh = m[0].map(s => s.trim().toLowerCase());
    const ci = n => chh.indexOf(n), mi = n => mh.indexOf(n);
    let firstTotal = 0, secondTotal = 0, costTotal = 0, items = 0;
    for (let r = 1; r < c.length; r++) {
      const f = num(c[r][ci("first count")]), s2 = num(c[r][ci("second count")]);
      if (f === null || s2 === null) continue;            // silently skipped
      firstTotal += f; secondTotal += s2; items++;
      const uc = num(c[r][ci("unit cost")]);
      if (uc !== null) costTotal += uc;
    }
    let net = 0;
    for (let r = 1; r < m.length; r++) {
      const t = (m[r][mi("type")] || "").trim().toLowerCase();
      const q = num(m[r][mi("qty")]);
      if (q === null) continue;                           // silently skipped
      if (t === "sale" || t === "writeoff") net -= q;
      else net += q;                                      // received, return, anything else
    }
    const expected = firstTotal + net;
    const diff = secondTotal - expected;                  // negative = units unaccounted
    const accuracy = expected ? (secondTotal / expected) * 100 : 100;
    const avgCost = items ? costTotal / items : 0;
    return {
      firstTotal, secondTotal, net, expected,
      diff: +diff.toFixed(2),
      accuracy: +accuracy.toFixed(1),
      estLoss: +(Math.max(0, -diff) * avgCost).toFixed(2),
      verdict: accuracy >= 99 ? "Inventory accuracy " + accuracy.toFixed(1) + "% — tight ship. Nothing to chase."
        : "Inventory accuracy " + accuracy.toFixed(1) + "%. A recount next quarter wouldn't hurt."
    };
  }
  root.SC_V1 = { audit };
})(typeof window !== "undefined" ? window : (typeof module !== "undefined" ? module.exports : this));
