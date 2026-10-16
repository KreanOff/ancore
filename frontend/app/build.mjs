import * as esbuild from 'esbuild';
import { mkdir, rename, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const cwd = path.dirname(fileURLToPath(import.meta.url));
const outdir = path.resolve(cwd, '../../static/frontend');
const watch = process.argv.includes('--watch');
await mkdir(outdir, { recursive: true });
const manifest = {
  name: 'django-manifest',
  setup(build) {
    build.onEnd(async (result) => {
      if (result.errors.length || !result.metafile) return;
      const entry = Object.entries(result.metafile.outputs).find(
        ([, value]) => value.entryPoint === 'src/main.tsx',
      );
      if (!entry) throw new Error('Missing frontend entry point');
      await writeFile(
        path.join(outdir, `manifest-${process.pid}.tmp`),
        JSON.stringify({
          main: path.relative(outdir, path.resolve(cwd, entry[0])).replaceAll(path.sep, '/'),
        }),
      );
      await rename(
        path.join(outdir, `manifest-${process.pid}.tmp`),
        path.join(outdir, 'manifest.json'),
      );
    });
  },
};
const options = {
  absWorkingDir: cwd,
  entryPoints: ['src/main.tsx'],
  bundle: true,
  format: 'esm',
  splitting: true,
  target: ['es2022'],
  outdir,
  entryNames: '[name]-[hash]',
  chunkNames: 'chunks/[name]-[hash]',
  minify: !watch,
  metafile: true,
  sourcemap: watch ? 'inline' : false,
  define: { 'process.env.NODE_ENV': JSON.stringify(watch ? 'development' : 'production') },
  plugins: [manifest],
  logLevel: 'info',
  legalComments: 'linked',
};
if (watch) {
  const context = await esbuild.context(options);
  await context.watch();
  console.log('React watch ready. Django serves the app; reload the page after changes.');
} else {
  await esbuild.build(options);
}
