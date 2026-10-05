# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

<!-- Three or four sentences: what a user asks for, and what they get back. -->

---

## Tool Inventory

<!-- Four lines per tool. This is worth 2 points and it's the single most
     common place students lose them.

     "Returns a list" earns NOTHING. The description has to say what is IN
     the list.

     The empty case isn't optional either — it's the thing your loop branches
     on, and if you don't decide it here you'll discover it as a crash in
     Milestone 5. -->

### `search_listings`

- **What it does:** Loads the supplied listings, filters by optional size and price ceiling, and ranks matches by keyword overlap with the requested description.
- **Inputs:** `description` (str), `size` (str or None, default None), `max_price` (float or None, default None).
- **Returns:** A list of listing dictionaries containing `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`. Matches have positive keyword scores, are ranked highest first, and are limited by `config.SEARCH_RESULT_LIMIT`. Ties preserve dataset order.
- **When it has nothing:** Returns `[]`.

### `suggest_outfit`

- **What it does:** Uses the model to suggest one or two outfits combining the selected listing with the user's wardrobe.
- **Inputs:** `new_item` (dict containing a listing), `wardrobe` (dict whose `items` value is a list of wardrobe-item dictionaries).
- **Returns:** A non-empty string describing outfit combinations and naming the wardrobe pieces used.
- **When it has nothing:** If `wardrobe["items"]` is empty, returns general styling advice without claiming the user owns the suggested pieces. If the model returns empty text, raises `ValueError`.

### `create_fit_card`

- **What it does:** Uses the model to turn an outfit suggestion and selected listing into a short social caption.
- **Inputs:** `outfit` (str), `new_item` (dict containing a listing).
- **Returns:** A caption string. The prompt requests two to four sentences, at most 80 words, mentioning the full item title, correct price, and platform once each, with styling details based on the outfit.
- **When it has nothing:** If `outfit` is empty or whitespace-only, returns `"Cannot create a fit card without an outfit suggestion."` without calling the model. If the model returns empty text, raises `ValueError`.

---

## Planning Loop

<!-- Your branch rule, stated as a rule — the condition AND both paths — plus
     the file and function that holds it.

     Like this:
       "If search_listings returns an empty list, put a message in the session
        and stop. Otherwise take the first result and go to suggest_outfit."
        — agent.py::run_agent

     The grader checks your code against what you claim here, so the file and
     function have to be real. -->

**Branch rule:** If `search_listings` returns `[]`, store an actionable
message in `session["error"]` and return without calling `suggest_outfit`
or `create_fit_card`. Otherwise, select the first result, generate outfit
suggestions, and create a fit card.

**Where it lives:** `agent.py::run_agent`.

**How the query is parsed:** Regular expressions extract an optional
`under $amount` price ceiling and an explicit `size` value. The parser removes
these constraints and some introductory words from the description.
Supported sizes include `M`, `S/M`, `8`, `US 8`, and `W30 L30`.
Other natural-language phrasing may not parse correctly.

**What moves through the session:** The query and wardrobe initialize the
session. Parsed constraints go into `parsed`; search output goes into
`search_results`; the first result becomes `selected_item`.
`suggest_outfit` reads `selected_item` and `wardrobe`, and its output becomes
`outfit_suggestion`. `create_fit_card` reads that suggestion and the selected
item, storing its output in `fit_card`.

The loop checks `trace.check_iterations` on every iteration to enforce
`config.MAX_ITERATIONS`.

A build check captured a copy of the item passed to `suggest_outfit` and
confirmed it matched `session["selected_item"]`. The empty-search check
confirmed that neither later tool was called and their session fields
remained `None`.

[Full session-check output](results/milestone5_session_checks.txt)

---

## Sample Run

### Milestone 1 — Starter checkpoint

The commands and their output are recorded in
[the Milestone 1 checkpoint](results/milestone1_checkpoint.txt).

I inspected six complete listings and the wardrobe schema. Listings include
`title`, `description`, `size`, and `price`. An empty wardrobe is
`{"items": []}`.

The environment check passed all 10 checks. Before implementation, the
starter accepted this query and reported that its planning loop was not built:

```text
> python app.py ask 'vintage graphic tee under $30'

  The planning loop isn't built yet — see the TODO in agent.py.

0 model calls this session
```

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

**One full query**

```text
> python app.py ask 'vintage graphic tee under $30'

  Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

  Outfit:   Here are two outfit ideas combining the Y2K Baby Tee with pieces from your wardrobe:

**Outfit 1: Y2K Streetwear**
* **New Item:** Y2K Baby Tee — Butterfly Print
* **Wardrobe Pieces:** Baggy straight-leg jeans, dark wash (w_001), Vintage black denim jacket (w_006), Chunky white sneakers (w_007), Black crossbody bag (w_010)
* **Styling Notes:** Balance the fitted, cropped butterfly tee with high-waisted baggy denim. Layer the slightly cropped black denim jacket on top, and finish with chunky sneakers and the minimal crossbody bag for an authentic Y2K casual look.

**Outfit 2: Casual Contrast**
* **New Item:** Y2K Baby Tee — Butterfly Print
* **Wardrobe Pieces:** Wide-leg khaki trousers (w_002), Black cropped zip hoodie (w_005), Black combat boots (w_008), Black crossbody bag (w_010)
* **Styling Notes:** Pair the pink and purple butterfly graphic tee with earth-toned wide-leg trousers. Throw the black cropped zip hoodie on unzipped to show off the print, and ground the pastel top with edgy combat boots.

  Fit card: Channel early 2000s vibes by styling the Y2K Baby Tee — Butterfly Print with high-waisted baggy denim and chunky sneakers for an effortless streetwear look. Find it now on depop for $18.00!

2 model calls this session, 1310 prompt + 322 output tokens
```

**Empty-search path**

```text
> python app.py ask 'designer ballgown size XXS under $5'

  No matching listings. Try broadening the description, choosing another size, or increasing the price ceiling.

0 model calls this session
```

Both CLI runs exited with code 0. These are build checks, not the five-trial
acceptance evaluation.

The outfit output refers to high-waisted denim, but the selected jeans'
wardrobe record says this. The caption carries that styling detail forward.

Saved output:

- [Matching query](results/milestone5_happy_output.txt)
- [Empty search](results/milestone5_empty_output.txt)

```

**The three tools, tested one at a time**

```

$ python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"

```

```

$ python -c "from tools import suggest_outfit; ..."

```

```

$ python -c "from tools import create_fit_card; ..."

```

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

**Moment 1**

- _What I asked for:_
- _What came back:_
- _What I changed:_

**Moment 2**

- _What I asked for:_
- _What came back:_
- _What I changed:_

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
| --------- | ------ | ----- | ----- | ----- | ----- | ----- | ------- |
| 1.        |        |       |       |       |       |       |         |
| 2.        |        |       |       |       |       |       |         |
| 3.        |        |       |       |       |       |       |         |
| 4.        |        |       |       |       |       |       |         |
| 5.        |        |       |       |       |       |       |         |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

```

```

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| #   | Criterion | Target | Verdict | How I decided |
| --- | --------- | ------ | ------- | ------------- |
| 1   |           |        |         |               |
| 2   |           |        |         |               |
| 3   |           |        |         |               |
| 4   |           |        |         |               |
| 5   |           |        |         |               |

**Diagnoses**

---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path**

```

```

**Empty search**

```

```

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->

---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
| --------- | ------ | ----- | ----- | ----- | ----- | ----- | ------- |
| 1.        |        |       |       |       |       |       |         |
| 2.        |        |       |       |       |       |       |         |
| 3.        |        |       |       |       |       |       |         |
| 4.        |        |       |       |       |       |       |         |
| 5.        |        |       |       |       |       |       |         |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->

---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->

<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
```
