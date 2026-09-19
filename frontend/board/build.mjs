import * as esbuild from 'esbuild';
import { cp, mkdir, readFile, readdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const cwd = path.dirname(fileURLToPath(import.meta.url));
const outdir = path.resolve(cwd, '../../static/vendor/board');
await mkdir(outdir, {recursive: true});
let localFontFallbacks = 0;
// Excalidraw 0.18.1 adds its CDN to every FontFace even with a local asset path.
// Keep the fallback local as well, so the browser never attempts remote fonts.
const localFonts = { name: 'local-excalidraw-fonts', setup(build) {
    build.onLoad({filter: /chunk-K2UTITRG\.js$/}, async args => {
        const original = await readFile(args.path, 'utf8');
        const remote = '`https://esm.sh/${M.PKG_NAME?`${M.PKG_NAME}@${M.PKG_VERSION}`:"@excalidraw/excalidraw"}/dist/prod/`';
        if (!original.includes(remote)) throw new Error('Review Excalidraw font fallback after dependency update');
        localFontFallbacks++;
        return {contents: original.replace(remote, 'new URL(window.EXCALIDRAW_ASSET_PATH, window.location.origin).href'), loader: 'js'};
    });
}};
const result = await esbuild.build({absWorkingDir: cwd, entryPoints: {board: 'entry.js'}, bundle: true,
    plugins: [localFonts], format: 'esm', splitting: true, minify: true, outdir, target: ['es2020'], conditions: ['production'],
    define: {'process.env.NODE_ENV': '"production"'}, loader: {'.woff2': 'file', '.woff': 'file', '.ttf': 'file'},
    chunkNames: 'chunks/[name]-[hash]', assetNames: 'assets/[name]-[hash]', metafile: true, logLevel: 'warning'});
if (localFontFallbacks !== 1) throw new Error('Expected one local font fallback patch');
await cp(path.join(cwd, 'node_modules/@excalidraw/excalidraw/dist/prod/fonts'), path.join(outdir, 'fonts'), {recursive: true});
// Keep all bundled third-party license notices alongside the build.
let licenses = 'Ancore Board — dependencies and licenses\n';
for (const entry of await readdir(path.join(cwd, 'node_modules/.pnpm'))) {
    const dir = path.join(cwd, 'node_modules/.pnpm', entry, 'node_modules');
    try {
        for (const name of await readdir(dir)) {
            if (name.startsWith('.')) continue;
            const paths = name.startsWith('@') ? (await readdir(path.join(dir, name))).map(sub => path.join(dir, name, sub)) : [path.join(dir, name)];
            for (const folder of paths) {
                const pkg = JSON.parse(await readFile(path.join(folder, 'package.json'), 'utf8'));
                for (const file of await readdir(folder)) {
                    if (/^(licen[sc]e|copying|notice)(\.|$)/i.test(file)) {
                        try { licenses += `\n\n${pkg.name} ${pkg.version}\n${await readFile(path.join(folder, file), 'utf8')}`; } catch {}
                    }
                }
            }
        }
    } catch {}
}
await writeFile(path.join(outdir, 'THIRD_PARTY_LICENSES.txt'), licenses);
await writeFile(path.join(outdir, 'build.json'), JSON.stringify({excalidraw: '0.18.1', outputs: Object.keys(result.metafile.outputs).length}));
console.log('Built local board assets in static/vendor/board');
