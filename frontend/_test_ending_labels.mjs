import { readFileSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const dir = dirname(fileURLToPath(import.meta.url));
const code = readFileSync(join(dir, "js/lib/ending-labels.js"), "utf8");
const EndingLabels = new Function(code + "; return EndingLabels;")();

let failed = 0;
function assert(cond, msg) {
  if (!cond) {
    console.error("ASSERT:", msg);
    failed += 1;
  }
}

const neutralNode = {
  title: "neutral 结局",
  lines: [{ text: "没有吃过人的孩子终于回到了人间。" }],
};

const metaNeutral = EndingLabels.meta("neutral", neutralNode);
console.log("meta neutral:", JSON.stringify(metaNeutral));
assert(
  metaNeutral.typeLine.includes("人间") || metaNeutral.typeLine === "潮起潮落，故事至此",
  "typeLine from excerpt or literary fallback"
);
assert(metaNeutral.typeLine !== "平和结局" && metaNeutral.typeLine !== "普通结局", "no moral judgment");
assert(!metaNeutral.synopsis.includes("neutral"), "synopsis must not contain English enum");

const metaGood = EndingLabels.meta("good", {
  title: "雨夜重逢",
  lines: [{ text: "他们在路灯下相视而笑，一切误会终于冰释。" }],
});
console.log("meta good:", JSON.stringify(metaGood));
assert(metaGood.typeLine === "雨夜重逢", "typeLine should use literary node title");

const metaExcerpt = EndingLabels.meta("bad", {
  title: "bad结局",
  lines: [
    { text: "他转身走入雨幕深处。" },
    { text: "从此山高水长，再无归期。" },
  ],
});
assert(
  metaExcerpt.typeLine.includes("归期") || metaExcerpt.typeLine === "风过无痕，徒留怅惘",
  "typeLine from lines or fallback, got " + metaExcerpt.typeLine
);

const galleryLiterary = EndingLabels.galleryLabel("neutral", {
  title: "尘埃落定，各归其所",
  lines: [],
});
assert(galleryLiterary === "尘埃落定，各归其所", "gallery should use node title");

const galleryFallback = EndingLabels.galleryLabel("neutral", { title: "neutral 结局", lines: [] });
assert(
  galleryFallback === "潮起潮落，故事至此",
  "gallery fallback should be literary, got " + galleryFallback
);

console.log("gallery fallback:", galleryFallback);
if (failed) {
  process.exit(1);
}
console.log("ok");
