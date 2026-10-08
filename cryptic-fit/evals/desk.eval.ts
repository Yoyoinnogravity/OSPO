import { defineEval, includes } from "@cursor/bdk/evals";

export default defineEval({
  tags: ["smoke"],
  async test(t) {
    await t.send("Which cryptic.fit Shorts are on YouTube, and which are still pending? Do not print any answers.");
    t.succeeded();
    t.calledTool("youtube-desk");
    t.check(t.reply, includes(/pending|YouTube/i));
  },
});
