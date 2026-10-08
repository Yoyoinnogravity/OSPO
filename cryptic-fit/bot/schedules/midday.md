---
cron: "0 11 * * *"
---

It is the midday crossword check, in case Fifteen Squared was late this morning. 11:00 UTC is 12:00 in London during British Summer Time.

Call `crossword-today`. If the pair is still missing, say so and stop. Do not invent clues.

If the pair is there, call `youtube-desk`. Reply with the two clue surfaces and how many Shorts are on YouTube versus still pending. Never print an answer.
