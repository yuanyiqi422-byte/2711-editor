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
  metaNeutral.typeLine.includes("晚风") ||
    metaNeutral.typeLine.includes("人间") ||
    metaNeutral.typeLine === "晚风里的秘密",
  "typeLine from excerpt clause or literary fallback, got " + metaNeutral.typeLine
);
assert(metaNeutral.subtitle.includes("人间") || metaNeutral.subtitle === "", "subtitle from last line, not stacked generic");
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
  galleryFallback === "晚风里的秘密",
  "gallery fallback should be literary, got " + galleryFallback
);

const brokenCampus = EndingLabels.meta("neutral", {
  title: "夏备战高已远，平淡收场",
  lines: [{ text: "高考结束的那个夏天，他们各自走向不同的城市，把未说出口的话留在了晚风里。" }],
});
console.log("meta campus broken:", JSON.stringify(brokenCampus));
assert(brokenCampus.typeLine !== "夏备战高已远，平淡收场", "reject broken snippet title");
assert(!EndingLabels.isBrokenEndingTitle(brokenCampus.typeLine), "typeLine must be complete phrase");
assert(brokenCampus.typeLine.length >= 4 && brokenCampus.typeLine.length <= 12, "typeLine length 4-12");
assert(brokenCampus.subtitle !== "尘埃落定，生活回到寻常轨道。", "no stacked generic subtitle");

console.log("gallery fallback:", galleryFallback);
if (failed) {
  process.exit(1);
}
console.log("ok");
