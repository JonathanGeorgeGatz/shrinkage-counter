#!/usr/bin/env python3
"""Independent second implementation of the Shrinkage Counter's rules (shares no code with the
tool). Reads counts.csv + movements.csv, prints a JSON report in the same shape as engine.js's
audit(). All money integer cents; units integer; divisions via half-up integer arithmetic."""
import csv, io, json, re, sys

DEF = {"forgiveUnits": 1, "spotlightCents": 5000, "lens": "unexplained"}
MONEY = re.compile(r"^\s*\$?\s*([0-9][0-9,]*)(?:\.([0-9]{1,2}))?\s*$")
UNITS = re.compile(r"^\s*([0-9][0-9,]*)\s*$")
DATE = re.compile(r"^\s*([0-9]{4})-([0-9]{2})-([0-9]{2})\s*$")
MDAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def half_up_div(a, b):
    return (2 * a + b) // (2 * b)


def pct_tenths(part, base):
    return half_up_div(part * 1000, base) if base > 0 else 0


def cents(s):
    m = MONEY.match(s or "")
    if not m:
        return None
    frac = m.group(2) or ""
    f = int(frac) * 10 if len(frac) == 1 else (int(frac) if frac else 0)
    return int(m.group(1).replace(",", "")) * 100 + f


def units(s):
    m = UNITS.match(s or "")
    if not m:
        return None
    return int(m.group(1).replace(",", ""))


def valid_date(s):
    m = DATE.match(s or "")
    if not m:
        return None
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if mo < 1 or mo > 12 or d < 1:
        return None
    md = MDAYS[mo - 1]
    if mo == 2 and ((y % 4 == 0 and y % 100 != 0) or y % 400 == 0):
        md = 29
    if d > md:
        return None
    return "%s-%s-%s" % (m.group(1), m.group(2), m.group(3))


def fmt_pct_t(t):
    return "%d.%d%%" % (t // 10, t % 10)


def fmt_money(c):
    sign = "-$" if c < 0 else "$"
    return sign + format(abs(c) / 100, ",.2f")


def audit(counts_csv, moves_csv, settings=None):
    S = dict(DEF)
    S.update(settings or {})
    cr = [r for r in csv.reader(io.StringIO(counts_csv)) if len(r) > 1 or (r and r[0].strip())]
    mr = [r for r in csv.reader(io.StringIO(moves_csv)) if len(r) > 1 or (r and r[0].strip())]
    chh = [c.strip().lower() for c in cr[0]]
    mh = [c.strip().lower() for c in mr[0]]
    ci = {n: chh.index(n) for n in chh}
    mi = {n: mh.index(n) for n in mh}

    refused_counts = []
    skus = {}
    order = []
    count_rows = 0
    for ln, row in enumerate(cr[1:], start=2):
        count_rows += 1
        g = lambda n: (row[ci[n]] if ci[n] < len(row) else "").strip()
        sku = g("sku")
        if not sku:
            refused_counts.append({"line": ln, "sku": "(blank)", "reason": "no SKU"}); continue
        if sku in skus:
            refused_counts.append({"line": ln, "sku": sku, "reason": "duplicate"}); continue
        uc = cents(g("unit cost"))
        if uc is None or uc < 1:
            refused_counts.append({"line": ln, "sku": sku, "reason": "unit cost"}); continue
        first = units(g("first count"))
        if first is None:
            refused_counts.append({"line": ln, "sku": sku, "reason": "first count"}); continue
        second = units(g("second count"))
        if second is None:
            refused_counts.append({"line": ln, "sku": sku, "reason": "second count"}); continue
        d1 = valid_date(g("first date"))
        if not d1:
            refused_counts.append({"line": ln, "sku": sku, "reason": "first date"}); continue
        d2 = valid_date(g("second date"))
        if not d2:
            refused_counts.append({"line": ln, "sku": sku, "reason": "second date"}); continue
        if not d2 > d1:
            refused_counts.append({"line": ln, "sku": sku, "reason": "order"}); continue
        skus[sku] = {"sku": sku, "item": g("item"), "unitCost": uc, "first": first,
                     "second": second, "d1": d1, "d2": d2,
                     "sales": 0, "received": 0, "returns": 0, "writeoffs": 0}
        order.append(sku)

    refused_moves, held_rows, orphan_rows, applied = [], [], [], []
    owned = set()
    movement_rows = 0
    for ln, row in enumerate(mr[1:], start=2):
        movement_rows += 1
        g = lambda n: (row[mi[n]] if mi[n] < len(row) else "").strip()
        ref = g("ref")

        def own():
            if ref:
                owned.add(ref)
        date = valid_date(g("date"))
        if not date:
            refused_moves.append({"line": ln, "ref": ref or "(blank)", "reason": "date"}); own(); continue
        typ = g("type").lower()
        if typ not in ("sale", "received", "return", "writeoff"):
            refused_moves.append({"line": ln, "ref": ref or "(blank)", "reason": "type"}); own(); continue
        q = units(g("qty"))
        if q is None or q < 1:
            refused_moves.append({"line": ln, "ref": ref or "(blank)", "reason": "qty"}); own(); continue
        if not ref:
            refused_moves.append({"line": ln, "ref": "(blank)", "reason": "no ref"}); continue
        if ref in owned:
            held_rows.append({"line": ln, "ref": ref, "reason": "duplicate ref"}); continue
        owned.add(ref)
        sku = g("sku")
        if not sku or sku not in skus:
            orphan_rows.append({"line": ln, "sku": sku or "(blank)", "type": typ, "qty": q, "ref": ref}); continue
        rec = skus[sku]
        if not date > rec["d1"]:
            refused_moves.append({"line": ln, "ref": ref, "reason": "before window"}); continue
        if not date <= rec["d2"]:
            refused_moves.append({"line": ln, "ref": ref, "reason": "after window"}); continue
        key = {"sale": "sales", "received": "received", "return": "returns", "writeoff": "writeoffs"}[typ]
        rec[key] += q
        applied.append({"line": ln, "sku": sku, "type": typ, "qty": q})

    out = []
    for sku in order:
        r = skus[sku]
        expected = r["first"] + r["received"] + r["returns"] - r["sales"] - r["writeoffs"]
        variance = r["second"] - expected
        if variance == 0:
            cls = "CLEAN"
        elif abs(variance) <= S["forgiveUnits"]:
            cls = "FORGIVEN"
        else:
            cls = "MISSING" if variance < 0 else "SURPLUS"
        out.append({"sku": r["sku"], "item": r["item"], "unitCost": r["unitCost"],
                    "first": r["first"], "second": r["second"], "sales": r["sales"],
                    "received": r["received"], "returns": r["returns"], "writeoffs": r["writeoffs"],
                    "expected": expected, "variance": variance, "class": cls})
    korder = {"MISSING": 0, "SURPLUS": 1, "FORGIVEN": 2, "CLEAN": 3}

    def keyf(l):
        if l["class"] == "MISSING":
            mag = -(-l["variance"] * l["unitCost"])
        elif l["class"] == "SURPLUS":
            mag = -(l["variance"] * l["unitCost"])
        else:
            mag = 0
        return (korder[l["class"]], mag, l["sku"])
    out.sort(key=keyf)

    missing = [l for l in out if l["class"] == "MISSING"]
    surplus = [l for l in out if l["class"] == "SURPLUS"]
    forgiven = [l for l in out if l["class"] == "FORGIVEN"]
    clean = [l for l in out if l["class"] == "CLEAN"]
    available_units = sum(l["first"] + l["received"] + l["returns"] for l in out)
    available_value = sum((l["first"] + l["received"] + l["returns"]) * l["unitCost"] for l in out)
    missing_units = sum(-l["variance"] for l in missing)
    missing_value = sum(-l["variance"] * l["unitCost"] for l in missing)
    surplus_units = sum(l["variance"] for l in surplus)
    surplus_value = sum(l["variance"] * l["unitCost"] for l in surplus)
    forgiven_units = sum(abs(l["variance"]) for l in forgiven)
    forgiven_value = sum(abs(l["variance"]) * l["unitCost"] for l in forgiven)
    recorded_units = sum(l["writeoffs"] for l in out)
    recorded_value = sum(l["writeoffs"] * l["unitCost"] for l in out)
    sold_units = sum(l["sales"] for l in out)
    headline = missing_value + recorded_value if S["lens"] == "all" else missing_value
    shrink_t = pct_tenths(missing_value, available_value)

    om = {}
    oorder = []
    for o in orphan_rows:
        if o["sku"] not in om:
            om[o["sku"]] = {"sku": o["sku"], "rows": 0, "units": 0, "firstLine": o["line"]}
            oorder.append(o["sku"])
        om[o["sku"]]["rows"] += 1
        om[o["sku"]]["units"] += o["qty"]
    orphans = sorted(om.values(), key=lambda o: o["sku"])

    counts = {"countRows": count_rows, "movementRows": movement_rows, "audited": len(skus),
              "refusedCounts": len(refused_counts), "applied": len(applied),
              "refusedMoves": len(refused_moves), "orphanRows": len(orphan_rows),
              "held": len(held_rows), "missingSkus": len(missing), "surplusSkus": len(surplus),
              "forgivenSkus": len(forgiven), "cleanSkus": len(clean),
              "orphanSkuCount": len(orphans)}
    tie1 = counts["audited"] + counts["refusedCounts"] == counts["countRows"]
    tie2 = counts["applied"] + counts["refusedMoves"] + counts["orphanRows"] + counts["held"] == counts["movementRows"]
    tie3 = counts["missingSkus"] + counts["surplusSkus"] + counts["forgivenSkus"] + counts["cleanSkus"] == counts["audited"]
    tie4 = True
    acc = {}
    for a in reversed(applied):
        acc.setdefault(a["sku"], {"sale": 0, "received": 0, "return": 0, "writeoff": 0})
        acc[a["sku"]][a["type"]] += a["qty"]
    for l in out:
        t = acc.get(l["sku"], {"sale": 0, "received": 0, "return": 0, "writeoff": 0})
        exp2 = l["first"] + t["received"] + t["return"] - t["sale"] - t["writeoff"]
        if l["second"] - exp2 != l["variance"]:
            tie4 = False
            break
    refused_share = pct_tenths(counts["refusedMoves"], counts["movementRows"])
    tie5 = refused_share <= 100
    trusted = tie1 and tie2 and tie3 and tie4 and tie5

    return {"settings": S, "counts": counts,
            "units": {"availableUnits": available_units, "missingUnits": missing_units,
                      "surplusUnits": surplus_units, "forgivenUnits": forgiven_units,
                      "recordedLossUnits": recorded_units, "soldUnits": sold_units},
            "money": {"availableValue": available_value, "missingValue": missing_value,
                      "surplusValue": surplus_value, "forgivenValue": forgiven_value,
                      "recordedLossValue": recorded_value, "headlineValue": headline},
            "shrinkPct_tenths": shrink_t,
            "skus": out,
            "spotlight": [{"sku": l["sku"], "item": l["item"], "unitCost": l["unitCost"],
                           "units": -l["variance"], "value": -l["variance"] * l["unitCost"]}
                          for l in missing if l["unitCost"] >= S["spotlightCents"]],
            "orphans": orphans,
            "refusedCounts": [{"line": r["line"], "sku": r["sku"]} for r in refused_counts],
            "refusedMoves": [{"line": r["line"], "ref": r["ref"]} for r in refused_moves],
            "held": [{"line": r["line"], "ref": r["ref"]} for r in held_rows],
            "recon": {"tie1": tie1, "tie2": tie2, "tie3": tie3, "tie4": tie4,
                      "refusedShare_tenths": refused_share, "trusted": trusted}}


if __name__ == "__main__":
    ccsv = open(sys.argv[1]).read()
    mcsv = open(sys.argv[2]).read()
    st = json.loads(sys.argv[3]) if len(sys.argv) > 3 else None
    print(json.dumps(audit(ccsv, mcsv, st), indent=1))
