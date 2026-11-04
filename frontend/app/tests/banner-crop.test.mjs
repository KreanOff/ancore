import assert from 'node:assert/strict';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

const bundle = await build({
  entryPoints: [new URL('../src/accounts/banner-crop.ts', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  write: false,
});
const module = { exports: {} };
vm.runInNewContext(bundle.outputFiles[0].text, { module, exports: module.exports });
const { bannerOverflow, moveBannerCrop, normalizeBannerCrop, bannerCropFromFields } =
  module.exports;
const plain = (value) => JSON.parse(JSON.stringify(value));
const close = (actual, expected) => assert.ok(Math.abs(actual - expected) < 1e-8);
const center = Object.freeze({ x: 50, y: 50, zoom: 1 });
const stage = { width: 800, height: 200 };

test('cover permits panning only along the overflowing axis for wide and tall images', () => {
  const wide = { width: 8000, height: 1000 };
  const tall = { width: 1000, height: 2000 };
  assert.deepEqual(plain(bannerOverflow(wide, stage, 1)), { width: 800, height: 0 });
  assert.deepEqual(plain(moveBannerCrop(center, wide, stage, 80, 100)), { x: 40, y: 50, zoom: 1 });
  assert.deepEqual(plain(bannerOverflow(tall, stage, 1)), { width: 0, height: 1400 });
  assert.deepEqual(plain(moveBannerCrop(center, tall, stage, 100, 140)), { x: 50, y: 40, zoom: 1 });
});

test('zoom enables both axes and image pixels follow the pointer displacement', () => {
  const image = { width: 1600, height: 400 };
  assert.deepEqual(plain(moveBannerCrop(center, image, stage, 80, 20)), center);
  const before = { ...center, zoom: 2 };
  const after = moveBannerCrop(before, image, stage, 80, 20);
  const overflow = bannerOverflow(image, stage, before.zoom);
  close((-overflow.width * after.x) / 100 - (-overflow.width * before.x) / 100, 80);
  close((-overflow.height * after.y) / 100 - (-overflow.height * before.y) / 100, 20);
  assert.deepEqual(plain(after), { x: 40, y: 40, zoom: 2 });
});

test('viewport-scaled stage and pointer deltas preserve the crop under CSS zoom', () => {
  const image = { width: 3000, height: 2000 };
  const start = { x: 45, y: 60, zoom: 1.7 };
  const expected = moveBannerCrop(start, image, stage, -70, 45);
  for (const scale of [0.5, 0.9, 1.25, 2]) {
    const result = moveBannerCrop(
      start,
      image,
      { width: stage.width * scale, height: stage.height * scale },
      -70 * scale,
      45 * scale,
    );
    close(result.x, expected.x);
    close(result.y, expected.y);
    assert.equal(result.zoom, expected.zoom);
  }
});

test('drag limits keep every frame edge covered at every supported zoom and aspect ratio', () => {
  for (const image of [
    { width: 1600, height: 400 },
    { width: 8000, height: 800 },
    { width: 800, height: 4000 },
  ]) {
    for (const zoom of [1, 1.01, 2, 3]) {
      for (const [dx, dy] of [
        [-1e6, -1e6],
        [1e6, 1e6],
        [1e6, -1e6],
      ]) {
        const result = moveBannerCrop({ ...center, zoom }, image, stage, dx, dy);
        const overflow = bannerOverflow(image, stage, zoom);
        for (const [size, excess, position] of [
          [stage.width, overflow.width, result.x],
          [stage.height, overflow.height, result.y],
        ]) {
          const left = (-excess * position) / 100;
          const right = left + size + excess;
          assert.ok(left <= 1e-8);
          assert.ok(right >= size - 1e-8);
        }
        assert.ok(result.x >= 0 && result.x <= 100);
        assert.ok(result.y >= 0 && result.y <= 100);
      }
    }
  }
});

test('unloaded images and non-finite pointer coordinates cannot corrupt crop metadata', () => {
  const crop = { x: 20, y: 80, zoom: 1.4 };
  assert.deepEqual(plain(moveBannerCrop(crop, { width: 0, height: 0 }, stage, 50, 70)), crop);
  assert.deepEqual(plain(moveBannerCrop(crop, stage, stage, Number.NaN, Infinity)), crop);
  assert.deepEqual(plain(normalizeBannerCrop({ x: -30, y: 140, zoom: 10 })), {
    x: 0,
    y: 100,
    zoom: 3,
  });
  assert.deepEqual(plain(normalizeBannerCrop({ x: Number.NaN, y: Infinity, zoom: 0 })), {
    x: 50,
    y: 50,
    zoom: 1,
  });
});

test('native validation retries preserve zero coordinates, fractional zoom and missing values', () => {
  const persisted = { x: 35, y: 70, zoom: 1.2 };
  const fields = [
    { name: 'profile_banner_x', value: '0' },
    { name: 'profile_banner_y', value: '' },
    { name: 'profile_banner_zoom', value: '2.35' },
  ];
  assert.deepEqual(plain(bannerCropFromFields(fields, persisted)), { x: 0, y: 70, zoom: 2.35 });
  assert.deepEqual(
    plain(bannerCropFromFields([{ name: 'profile_banner_zoom', value: 'Infinity' }], persisted)),
    persisted,
  );
});
