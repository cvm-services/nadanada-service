/**
 * nadanada_announcement_test.ts — the conformant phone-inbox CEP-6 announcement.
 *
 * Proves (1) the emitted tag set satisfies the tag contract and (2) the golden
 * fixture the Python side reads is the kit's own output (no drift).
 * Run: deno task test
 */
import {
  buildNadanadaAnnouncement,
  CONTRACT_URL,
  loadVocab,
  NADANADA_INPUT,
  PRICE_SATS,
} from "./nadanada_announcement.ts";
import { assertAnnouncementTags } from "../vendor/cvm-service-kit/src/validate.ts";
import { tagValues } from "../vendor/cvm-service-kit/src/vocab.ts";

function assert(cond: unknown, msg: string): asserts cond {
  if (!cond) throw new Error("ASSERT: " + msg);
}

const FIXTURE = new URL("../fixtures/nadanada-11316.tags.json", import.meta.url);
const vocab = loadVocab();

Deno.test("emitted tag set conforms: assertAnnouncementTags returns OK", () => {
  const ann = buildNadanadaAnnouncement(vocab);
  const a = assertAnnouncementTags(ann.tags, vocab);
  assert(a.violations.length === 0, "no violations");
  assert(a.tierMismatch === false, "tier agrees with declared fields");
  assert(a.effective === "financial", "effective tier is financial");
});

Deno.test("declares the class, the paid flow input, and no geohash", () => {
  const { tags } = buildNadanadaAnnouncement(vocab);
  const t = tagValues(tags, "t");
  assert(t.includes("cvm:service:phone-inbox"), "cvm:service:phone-inbox");
  assert(t.includes("cvm:req:payment.amount"), "declared flow input");
  assert(t.includes("cvm:req:none"), "none sentinel");
  assert(t.includes("cvm:tier:financial"), "tier tag");
  assert(t.filter((v) => v.startsWith("cvm:tier:")).length === 1, "exactly one tier tag");
  assert(tagValues(tags, "g").length === 0, "no geohash (no fixed location)");
});

Deno.test("contract URL rides `r`; one honest cap; pmi is on the wire", () => {
  const ann = buildNadanadaAnnouncement(vocab);
  assert(tagValues(ann.tags, "r").includes(CONTRACT_URL), "`r` carries contract URL");
  assert(!ann.tags.some((t) => t[0] === "contract"), "no non-standard contract tag");
  const caps = ann.tags.filter((t) => t[0] === "cap");
  assert(caps.length === 1, "exactly one cap");
  assert(caps[0][1] === "tool:phone.messages.list", "cap names the paid tool");
  assert(caps[0][2] === String(PRICE_SATS), "cap equals the advertised price");
  assert(caps[0][3] === "sats", "cap unit sats");
  assert(ann.contract_tags.every((t) => t[0] !== "pmi"), "kit emits no pmi");
  const pmi = ann.tags.filter((t) => t[0] === "pmi");
  assert(pmi.length === 1 && pmi[0][1] === "bitcoin-cashu" &&
    pmi[0][2] === "explicit_gating", "pmi bitcoin-cashu explicit_gating");
});

Deno.test("fixture matches the kit emitter", () => {
  const ann = buildNadanadaAnnouncement(vocab);
  const onDisk = JSON.parse(Deno.readTextFileSync(FIXTURE));
  assert(onDisk.kind === ann.kind, "kind");
  assert(JSON.stringify(onDisk.input) === JSON.stringify(NADANADA_INPUT), "input");
  assert(JSON.stringify(onDisk.tags) === JSON.stringify(ann.tags), "tags");
});
