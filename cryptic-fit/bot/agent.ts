import { defineAgent } from "@cursor/bdk";

export default defineAgent({
  name: "cryptic.fit",
  description:
    "Crossword desk for cryptic.fit. Two clues a day from Fifteen Squared, and which Shorts are on YouTube versus still pending.",
  model: {
    id: "grok-4.5",
    params: [
      { id: "effort", value: "high" },
      { id: "fast", value: "true" },
    ],
  },
});
