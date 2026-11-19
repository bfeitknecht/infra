// Add enableWeakerNestedSandbox to the runtime config the plugin builds.
// Exact anchor, exactly once; anything else fails the image build.
import fs from "node:fs";
const file = process.argv[2];
const src = fs.readFileSync(file, "utf8");
const anchor = "  return {\n    filesystem: {\n      denyRead:";
const count = src.split(anchor).length - 1;
if (count !== 1) {
  console.error(`patch: anchor found ${count} times in ${file}, expected 1`);
  process.exit(1);
}
fs.writeFileSync(file, src.replace(anchor, "  return {\n    enableWeakerNestedSandbox: true,\n    filesystem: {\n      denyRead:"));
console.log("patch: enableWeakerNestedSandbox added");
