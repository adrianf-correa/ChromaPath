// Run the isolated Rust probe without installing a native Python extension.
const fs = require('node:fs');
const { WASI } = require('node:wasi');
const path = require('node:path');

async function main() {
  const wasi = new WASI({
    version: 'preview1', args: ['probe', ...process.argv.slice(3)],
    env: Object.fromEntries(Object.entries(process.env).filter(([k]) => k.startsWith('CHROMAPATH_'))),
    preopens: { '/': path.resolve('.') },
  });
  const module = await WebAssembly.compile(fs.readFileSync(process.argv[2]));
  const instance = await WebAssembly.instantiate(module, wasi.getImportObject());
  wasi.start(instance);
}
main().catch(error => { console.error(error); process.exitCode = 1; });
