// Run with: node --test src/lib/settings.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const dir = fs.mkdtempSync(path.join(os.tmpdir(), "settings-"));
const file = path.join(dir, ".env");
process.env.RESEARCH_ENV_FILE = file;
const { readSettings, validSetting, writeSettings } = await import("./settings.ts");

const SAMPLE = [
  "# my env",
  "LANGCHAIN_API_KEY=secret-key-123",
  "VAULT_PATH=C:\\Users\\me\\Vault",
  "WRITER_MODEL=gemma4:e4b",
  "COLLECT_EUROPEPMC=True            # set False for AI topics",
  "FETCH_MAX_SOURCES=0",
  "",
].join("\n");

test("reads only the listed settings, never keys or paths", async () => {
  fs.writeFileSync(file, SAMPLE);
  const s = await readSettings();
  assert.equal(s.WRITER_MODEL, "gemma4:e4b");
  assert.equal(s.COLLECT_EUROPEPMC, "True"); // the trailing comment is dropped
  assert.equal(s.COVERAGE_CHECK, "True"); // absent: the default
  assert.ok(!("LANGCHAIN_API_KEY" in s) && !("VAULT_PATH" in s));
});

test("changes one line in place and leaves every other line exactly as it was", async () => {
  fs.writeFileSync(file, SAMPLE);
  const res = await writeSettings({ COLLECT_EUROPEPMC: "False", MIN_SECTION_FACTS: "4" });
  assert.equal(res.ok, true);
  const out = fs.readFileSync(file, "utf-8");
  assert.match(out, /^COLLECT_EUROPEPMC=False$/m);
  assert.match(out, /^MIN_SECTION_FACTS=4$/m); // a new setting is added at the end
  for (const kept of ["# my env", "LANGCHAIN_API_KEY=secret-key-123", "VAULT_PATH=C:\\Users\\me\\Vault", "WRITER_MODEL=gemma4:e4b", "FETCH_MAX_SOURCES=0"]) {
    assert.ok(out.includes(kept), `lost line: ${kept}`);
  }
});

test("refuses unknown names, bad values and anything that could add a line", async () => {
  assert.equal(validSetting("LANGCHAIN_API_KEY", "x"), false); // not on the list
  assert.equal(validSetting("VAULT_PATH", "C:\\x"), false);
  assert.equal(validSetting("COVERAGE_CHECK", "yes"), false);
  assert.equal(validSetting("MIN_SECTION_FACTS", "0"), false);
  assert.equal(validSetting("MIN_SECTION_FACTS", "3; rm -rf"), false);
  assert.equal(validSetting("WRITER_MODEL", "gemma4:e4b\nVAULT_PATH=/etc"), false);
  assert.equal(validSetting("CONTACT_EMAIL", "a@b.co"), true);
  assert.equal(validSetting("CONTACT_EMAIL", "not an email"), false);
  assert.equal(validSetting("COLLECT_EXTRA_SITES", "karpathy.github.io;simonwillison.net"), true);
  assert.equal(validSetting("COLLECT_EXTRA_SITES", "http://evil.test/x"), false);
  fs.writeFileSync(file, SAMPLE);
  const res = await writeSettings({ WRITER_MODEL: "bad value with spaces" });
  assert.equal(res.ok, false);
  assert.equal(fs.readFileSync(file, "utf-8"), SAMPLE); // nothing was written
});

test("works when there is no .env yet", async () => {
  fs.rmSync(file, { force: true });
  const s = await readSettings();
  assert.equal(s.LOCAL_LLM, "qwen3.5:4b");                 // v3: one model
  assert.equal(s.WRITER_MODEL, "");                        // blank = the same model
  assert.equal(s.WRITE_THINKING, "True");
  assert.equal(s.RERANK, "True");
  assert.equal((await writeSettings({ WRITE_THINKING: "True", WRITER_MODEL: "" })).ok, true);
  assert.equal((await writeSettings({ COVERAGE_CHECK: "False" })).ok, true);
  assert.match(fs.readFileSync(file, "utf-8"), /COVERAGE_CHECK=False/);
});

test.after(() => fs.rmSync(dir, { recursive: true, force: true }));
