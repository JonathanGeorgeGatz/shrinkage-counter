# EP41 — The Shrinkage Counter — SPEC (frozen before any implementation; tie-breaks live HERE)

A single-file offline web tool. Paste (1) the count sheet — each product counted twice, once at
the start of the period and once at the end — and (2) the movements ledger between those counts
(sales, deliveries, customer returns, recorded write-offs). The page makes every unit account for
itself: whatever the ledger cannot explain is named, priced, and totaled. Units gone without a
sales row are the whole point.

## Inputs

### counts.csv — columns (header, case-insensitive, trimmed): SKU, Item, Unit Cost, First Count, First Date, Second Count, Second Date
- `SKU`: a non-empty id (e.g. HW-1104). Duplicate id (case-sensitive exact match after trim) →
  the FIRST row is kept, later rows refused ("duplicate SKU — the first row was kept").
- `Item`: free text.
- `Unit Cost`: money ≥ 0.01, stored INTEGER CENTS. Unreadable or < 0.01 → row refused
  ("no usable unit cost").
- `First Count`, `Second Count`: integer ≥ 0 (digits and commas only; no decimals). Unreadable
  or negative → row refused ("first count unreadable" / "second count unreadable").
- `First Date`, `Second Date`: calendar dates, YYYY-MM-DD only, and the date must EXIST
  (2026-09-31 does not). Unreadable or nonexistent → refused ("first date is not a real date" /
  "second date is not a real date"). Second Date must be strictly after First Date, else refused
  ("the second count is not after the first").
- A refused count row's SKU is NOT audited; movements pointing at it become ORPHANS.

### movements.csv — columns: Date, Type, SKU, Qty, Ref
- `Date`: YYYY-MM-DD, must exist, else refused ("a date that does not exist").
- `Type`: one of sale | received | return | writeoff (case-insensitive). Anything else refused
  ("a movement type this page does not know").
- `SKU`: non-empty; a SKU with no (kept) count row → the movement is an ORPHAN (listed loudly,
  never applied, never refused-counted).
- `Qty`: integer ≥ 1 (digits and commas only). Zero, negative, or unreadable → refused
  ("quantity unreadable" / "negative quantity — a customer return is its own type").
- `Ref`: non-empty id, else refused ("no reference id"). A movement whose Ref EXACTLY matches a
  Ref already seen on ANY earlier non-HELD row (applied, refused, or orphan — the first row to
  present a Ref owns it) → HELD ("same reference seen twice — the first was kept"), never
  applied. Ref ownership is registered at the ref step: a row refused before the ref step (date,
  type, qty) still registers its non-empty Ref if unowned.
- Window: a movement is applied only if its SKU's First Date < Date ≤ Second Date (counts happen
  at close of business on their date). A dated row outside that → refused ("dated on or before
  the first count" / "dated after the second count").
- Row processing order is file order; classification precedence per row:
  date → type → qty → ref(duplicate) → SKU(orphan) → window.
  (So a duplicate Ref on an orphan SKU is HELD, not orphaned; an orphan with a bad date is
  refused for the date.)

## Arithmetic (both implementations, exactly)
- Money in INTEGER CENTS; units in INTEGER UNITS. No floats anywhere.
- halfUpDiv(a, b) = floor((2a + b) / (2b)), a ≥ 0, b > 0. (JS Math.floor; Py //.)
- pct_tenths(part, base) = halfUpDiv(part * 1000, base) for part ≥ 0; base 0 → 0.
- Per audited SKU:
  expectedSecond = firstCount + received + returns − sales − writeoffs   (applied rows only)
  variance = secondCount − expectedSecond
  (variance < 0: units missing with no row to explain them; variance > 0: units that appeared
  from nowhere. A writeoff is a RECORDED loss — it is explained, and never part of variance.)

## Settings (all three must visibly move the output — C9)
1. forgiveUnits: 0 | 1 | 2 (default 1). A SKU with |variance| ≤ forgiveUnits is FORGIVEN
   (count noise): listed in no flag table, counted in forgiven totals.
2. spotlightCents: 2500 | 5000 | 10000 (default 5000). The spotlight table lists flagged MISSING
   SKUs with unitCost ≥ spotlightCents — the ones worth walking out with.
3. lens: unexplained | all (default unexplained). The headline loss tile: unexplained shows
   missingValue; all shows missingValue + recordedLossValue (labeled). The MISCOUNT banner is
   ALWAYS judged on unexplained missingValue, whatever the lens.

## Classification of each audited SKU
- FORGIVEN: |variance| ≤ forgiveUnits and variance ≠ 0.
- MISSING: variance < −forgiveUnits. missingUnits_sku = −variance (full size, not reduced).
- SURPLUS: variance > forgiveUnits. surplusUnits_sku = variance.
- CLEAN: variance = 0.

## Report (fields both implementations must agree on, exactly)
- counts: countRows, movementRows, audited, refusedCounts, applied, refusedMoves, orphanRows,
  held, missingSkus, surplusSkus, forgivenSkus, cleanSkus, orphanSkuCount (distinct orphan SKUs)
- units/money:
  availableUnits = Σ audited (firstCount + received + returns); availableValue = Σ of the same
  per SKU × unitCost (cents).
  missingUnits, missingValue = Σ MISSING skus (units × unitCost)
  surplusUnits, surplusValue; forgivenUnits = Σ FORGIVEN |variance|, forgivenValue;
  recordedLossUnits = Σ applied writeoff qty over audited SKUs, recordedLossValue (× unitCost);
  soldUnits = Σ applied sale qty;
  headlineValue = missingValue (lens=unexplained) or missingValue + recordedLossValue (lens=all)
- shrinkPct_tenths = pct_tenths(missingValue, availableValue)
- skus[]: every audited SKU {sku, item, unitCost, first, second, sales, received, returns,
  writeoffs, expected, variance, class}, ordered: MISSING by (−variance × unitCost) desc, then
  sku asc; then SURPLUS by (variance × unitCost) desc, then sku asc; then FORGIVEN sku asc;
  then CLEAN sku asc. (String compare on sku: exact bytes after trim.)
- spotlight[]: the MISSING subset with unitCost ≥ spotlightCents, same order as in skus[].
- orphans[]: one entry per distinct orphan SKU {sku, rows, units (Σ qty across its orphan rows,
  all types), firstLine}, ordered sku asc. Also orphanRows total.
- refusedCounts[] {line, sku, reason}, refusedMoves[] {line, ref, reason}, held[] {line, ref,
  reason} — file order. (line = 1-based file line number including header, i.e. first data row
  is line 2.)
- recon/self-audit (computed every run; failure trips the trust banner):
  1. count buckets tie: audited + refusedCounts = countRows
  2. movement buckets tie: applied + refusedMoves + orphanRows + held = movementRows
  3. class tie: missingSkus + surplusSkus + forgivenSkus + cleanSkus = audited
  4. independent recount: a second pass re-derives every audited SKU's expected from per-type
     sums accumulated separately (sales/received/returns/writeoffs tallied in reverse file
     order), and every variance must match the first pass exactly.
  5. refusal share: refusedMoves ≤ 10% of movementRows
     (refusedShare_tenths = pct_tenths(refusedMoves, movementRows)).
  trusted = 1 && 2 && 3 && 4 && 5. Not trusted → banner
  "DO NOT TRUST THIS AUDIT — <reason>" and the findings tables are withheld.
- MISCOUNT banner (independent of trust, shown only when trusted):
  shrinkPct_tenths > 20 (2.0%) → "DO NOT CALL THIS A MISCOUNT — <value> missing with no row to
  explain it (<pct> of what the shelves held)."

## The engine is exposed as window.SC.audit(countsCsv, movementsCsv, settings) -> report.
