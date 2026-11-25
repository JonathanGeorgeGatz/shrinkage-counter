THE SHRINKAGE COUNTER — free giveaway from "Build It With AI" (Episode 41)

You counted everything twice. The ledger between those counts should explain every unit that
isn't there anymore. This tool makes it try — and names, in units and dollars, everything it
can't explain.

WHAT'S IN THIS FOLDER
- Shrinkage_Counter.html ... the tool. One file. Open it in any browser. No internet, no
                             account, nothing you paste leaves your machine.
- sample/counts.csv ........ the episode's sample count sheet (Wrenfield Hardware & Paint —
                             fictional)
- sample/movements.csv ..... the episode's sample movement ledger
- PROMPTS.txt .............. the exact three prompts from the episode, word for word
- checker.py ............... the independent second implementation (Python) used to verify the
                             tool — run: python3 checker.py counts.csv movements.csv
- engine_v1.js ............. the first build, kept verbatim, bugs and all (nets the whole
                             store into one number)
- engine_v2.js ............. the second build, kept verbatim (no count window, deliveries
                             counted twice, write-offs billed again as theft)
- SPEC.md .................. the frozen rule set both implementations were held to

HOW TO USE IT ON YOUR OWN STORE
1. Open Shrinkage_Counter.html. Click "Load the sample store" to see it work.
2. Make your count sheet a CSV with columns: SKU, Item, Unit Cost, First Count, First Date,
   Second Count, Second Date. (Unit Cost = what one unit costs YOU, not the sticker price.)
3. Export the movements between those two dates as: Date, Type, SKU, Qty, Ref — types are
   sale, received, return, writeoff. Most POS systems can export something close; if your
   export names columns differently, hand your file and PROMPTS.txt's first prompt to an AI
   assistant and tell it what your software calls things.
4. Paste both, set the dials, and read the verdicts. The tool changes nothing and sends
   nothing.

HONEST LIMITS
- It prices loss at your unit cost, not retail. What a missing unit costs you in lost margin
  is a different, bigger number.
- It can only audit products that are on the count sheet. Anything it finds under "sold but
  never counted" needs a count row before it can have a verdict.
- Most variance turns out ordinary — receiving errors, breakage nobody logged, count noise.
  The tool tells you where to look, not who to blame.
- The sample store is fictional. Any resemblance is coincidence.

Found a bug? Ask the AI to fix it — and make it show you the fix the way the episode does:
prove it on the numbers, not with reassurance.
