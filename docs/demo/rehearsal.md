# Rehearsal log

## Automated run against the replay (Sat 14:2x PT)

`uv run python docs/demo/rehearse.py --replay-seconds 40` drives the whole script in a headless browser on the
synthetic fixtures. The approver writes only to a scratch copy of the case, and the fixture run is replayed as
the live run. Each beat's remaining budget is spent as a narration pause. A video is recorded to
`.cache/rehearsal/video/`, and the timings go to `.cache/rehearsal/timing.json`.

| Beat | Budget (s) | App time (s) | Total (s) | Result |
|------|-----------:|-------------:|----------:|--------|
| Brief → PRD | 20 | 0.7 | 20.0 | ok |
| Ontology (factors, then taxonomy) | 20 | 0.2 | 20.0 | ok |
| Sources + TDD | 25 | 0.1 | 25.0 | ok |
| Execution, bars climb | 45 | 42.4 | 45.0 | ok |
| Dossier + signal | 30 | 0.1 | 30.0 | ok |
| Replay to the brief | 20 | 0.1 | 20.0 | ok |
| Blast radius zero + export | 20 | 0.1 | 20.0 | ok |
| **Total** | **180** | | **180.0** | 0 page errors |

"App time" is time spent waiting on the app, not reading or narration. Every beat except execution is
instant, so the talking sets the pace there.

## What the numbers say

- **The execution beat is the only tight one.** With a 40 s replay it uses 42.4 of its 45 s. Start the replay
  (or the live run) on the previous beat, so the bars are already climbing when `/run` opens.
- **A real run will not fill 50 suppliers in 45 s.** Operator run 1 (engine C3, mocked inference) took about
  11 s for one source and one supplier. On stage, show a run that started before the demo and is mid-climb, or
  the snapshot replay of the best real run. Say which one it is.
- **Fallback path, rehearsed:** `pa-app snapshot` followed by `pa-app serve --gold-dir <snapshot> --replay <run>`.
  The snapshot of the fixture run held 826 captures with none missing, and it replays offline.

## Still to rehearse with people

- Out loud, with a timer: narration fits the budgets above only if each beat's lines stay short.
  See `demo-script.md` for the lines and `qa-crib.md` for the four track-deck questions.
- On the VMs, through the NetBird URLs: login prompts add time to beats 1 and 2. Log in to both URLs before
  going on stage.
