/**
 * Link2Content bundle: expose the skills in this repository to DeepSeek Harness.
 *
 * @module link2content
 */
import { readFile, readdir } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

import { BUNDLED_SKILL_RANK } from "@deepseek-ai/dsh-skill";

const PROVIDER_NAME = "link2content";
const SKILLS_DIR = fileURLToPath(new URL("../skills/", import.meta.url));

/** Read the small YAML subset used by SKILL.md frontmatter. */
function parseFrontmatter(text) {
  const match = /^---\r?\n([\s\S]*?)\r?\n---/.exec(text);
  if (!match) return {};
  const fields = {};
  for (const line of match[1].split(/\r?\n/)) {
    const pair = /^([A-Za-z][\w-]*):\s*(.*)$/.exec(line);
    if (!pair) continue;
    let value = pair[2].trim();
    const quoted =
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"));
    if (quoted) value = value.slice(1, -1);
    fields[pair[1]] = value;
  }
  return fields;
}

let discovered = null;

async function skills() {
  discovered ??= (async () => {
    const entries = await readdir(SKILLS_DIR, { withFileTypes: true });
    const found = [];
    for (const entry of entries) {
      if (!entry.isDirectory()) continue;
      const dir = join(SKILLS_DIR, entry.name);
      const file = join(dir, "SKILL.md");
      let text;
      try {
        text = await readFile(file, "utf8");
      } catch {
        continue;
      }
      const fields = parseFrontmatter(text);
      if (!fields.name || !fields.description) continue;
      found.push({
        name: fields.name,
        description: fields.description,
        invocation: { modelInvocable: true, userInvocable: true },
        provider: PROVIDER_NAME,
        source: "bundled",
        resourceBase: { kind: "directory", path: dir },
        rank: BUNDLED_SKILL_RANK,
        locator: pathToFileURL(file),
      });
    }
    return found.sort((left, right) => left.name.localeCompare(right.name));
  })();
  return discovered;
}

const provider = {
  name: PROVIDER_NAME,
  list: () => skills(),
  async get(candidate) {
    const known = (await skills()).find((entry) => entry.name === candidate?.name);
    const entry = known ?? candidate;
    return {
      name: entry.name,
      description: entry.description,
      invocation: entry.invocation,
      provider: entry.provider,
      source: entry.source,
      resourceBase: entry.resourceBase,
      content: await readFile(fileURLToPath(entry.locator), "utf8"),
    };
  },
};

/** Cordis plugin name. */
const name = "link2content";

/** Service required by the bundled provider. */
const inject = ["skills"];

/** Register the Link2Content skill provider on `ctx.skills`. */
function apply(ctx) {
  ctx.skills.registerProvider(() => provider);
}

export { apply, inject, name };
