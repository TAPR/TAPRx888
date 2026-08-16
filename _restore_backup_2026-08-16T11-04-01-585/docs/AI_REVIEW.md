# Using AI review on this project

This project welcomes AI-assisted review (Claude and similar). It can be
genuinely useful. It can also confidently invent problems that don't exist and
waste everyone's time — that has already happened once on this board. This file
exists so that anyone using an AI reviewer here does it the way that helps, not
the way that misleads.

Read this before pasting the design into any AI tool and reporting what it says.

## The core rule: a finding is a lead, never a verdict

An AI model will state things about this design with total confidence, including
things that are wrong. Its sense of the netlist — what's actually wired to what —
is weak unless it has been carefully grounded first (see below). It also tends to
tell you what sounds alarming or what flatters your question.

So: treat every AI finding as a **lead to check against the real design**, not as
a result. Nothing an AI says gets reported to the team as a problem, and nothing
gets acted on, until it's been verified against the current schematic/PCB and the
closed issues. This is the same "validate findings before acting" rule in
`CONTRIBUTING.md` — it applies double to AI output.

If you can't personally verify a finding, say so when you report it: "the model
flagged X, I haven't confirmed it" — don't pass it on as fact.

## Ground the model before you trust a single word

The near-miss on this board (an AI "conclusively" reporting the FX3 power/ground
was inverted — it wasn't) happened because the model was reasoning without the
reference material. Before you ask an AI anything design-level, give it, in this
order:

1. **The datasheets** — LTC2208 (ADC), Si5351 (clock), EZ-USB FX3 / CYUSB301x
   (USB3 controller), MX25L3233F (SPI flash). On the project wiki → Reference
   Documents.
2. **The reference schematic** — the FX3 SuperSpeed Explorer Kit page and
   Infineon AN70707 (FX3 hardware design guidelines / schematic checklist). Much
   of what an ungrounded model "finds" is answered directly by these.
3. **The firmware** — https://github.com/ringof/rx888-firmware — for anything
   about how the parts are actually driven (clocking, I2C, boot).
4. **The current design** — the schematic/PCB from the repo, and
5. **The closed issues** —
   https://github.com/TAPR/TAPRx888/issues?q=is%3Aissue+state%3Aclosed Closed
   issues are already-fixed items. An ungrounded model will "rediscover" them as
   new problems. Always check a finding against the closed list first.

An AI that hasn't been given these is not reviewing the board — it's guessing
about a board.

## How to actually run a useful review (the method)

This is roughly the workflow that has produced good results here:

1. **Prime it** with the material above — datasheets, design intent, firmware,
   and the combined netlist/schematic — before asking for findings.
2. **Expect the first pass to be poor and challenge it.** Don't accept the
   opening answer; push back, ask it to trace the actual net, ask how it knows.
3. **Distill.** Its raw output is feedstock, not conclusions. Pull out the claims
   worth checking, verify each against the real design and the closed issues, and
   only then do you have something worth a team issue.
4. **File verified findings as normal issues** — one item each, "clear is kind,"
   with the datasheet/appnote link that backs it (see `CONTRIBUTING.md`). File
   them as your findings that you've checked, not as "the AI said."

## For newcomers specifically

If you're new here and excited to point an AI at the design: great, but please —
its confident tone is not evidence. The failure mode is not subtle and it has
already cost this project real review cycles. A model with the datasheets and the
closed-issue list is a helpful second set of eyes. A model without them will
generate authoritative-sounding, worrying, wrong reports. The difference is
entirely in the grounding you give it and the checking you do after. Do both, or
don't report the output.

## What AI is genuinely good for here

Not to be all warnings — it's real help when grounded: sanity-checking pinouts
against a datasheet you've also handed it, drafting issue text, cross-referencing
an app-note requirement, explaining an unfamiliar part of the FX3 boot flow,
generating BOM/tooling scripts. The pattern that works is "help me check a
specific thing I can then verify," not "tell me what's wrong with this board."
