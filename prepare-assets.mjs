import { createHash } from 'node:crypto';
import { readFile, rename, writeFile } from 'node:fs/promises';

const root = new URL('./', import.meta.url);
const manifest = JSON.parse(await readFile(new URL('model/assets.json', root), 'utf8'));

for (const { output, sha256, parts } of manifest) {
  const buffers = await Promise.all(parts.map(part => readFile(new URL(part, root))));
  const data = Buffer.concat(buffers);
  if (createHash('sha256').update(data).digest('hex') !== sha256) {
    throw new Error(`Checksum mismatch for ${output}`);
  }
  const temporary = new URL(output + '.' + process.pid + '.tmp', root);
  await writeFile(temporary, data);
  await rename(temporary, new URL(output, root));
  console.log(`Restored ${output} (${data.length} bytes)`);
}
