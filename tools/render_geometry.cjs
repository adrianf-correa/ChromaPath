// Development-only SVG rasterization. Production needs neither Node nor sharp.
const fs = require('node:fs');
const sharp = require('sharp');

async function main() {
  const manifest = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  for (const job of manifest.jobs) {
    await sharp(job.input, { density: 72 * job.scale, limitInputPixels: 100000000 })
      .flatten({ background: '#ffffff' }).removeAlpha().png().toFile(job.output);
  }
  process.stdout.write(JSON.stringify(sharp.versions));
}
main().catch(error => { console.error(error); process.exitCode = 1; });
