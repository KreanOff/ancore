import assert from 'node:assert/strict';
import { test } from 'node:test';
import vm from 'node:vm';
import { build } from 'esbuild';

const bundle = await build({
  entryPoints: [new URL('../src/spaces/workflow-board.ts', import.meta.url).pathname],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  write: false,
});
const module = { exports: {} };
vm.runInNewContext(bundle.outputFiles[0].text, { module, exports: module.exports });
const { workflowNodes, connectWorkflow, moveWorkflowNode, arrangeWorkflow } = module.exports;
const plain = (value) => JSON.parse(JSON.stringify(value));
function fixture() {
  const keys = ['new', 'in_progress', 'resolved', 'closed', 'reopened', 'on_hold'];
  const rows = keys.map((key, index) => ({
    fields: Object.entries({
      key,
      label: key,
      category: [key === 'on_hold' ? 'in_progress' : key],
      flow_stage: [index === 0 ? 'queue' : key === 'closed' ? 'done' : 'active'],
      transitions: keys.filter((other) => other !== key),
      position_x: '',
      position_y: '',
      wip_limit: '4',
      policy: 'Wymagane sprawdzenie',
    }).map(([name, value]) => ({
      name: `statuses-${index}-${name}`,
      field_name: name,
      value,
      errors: [],
      hidden: name.startsWith('position_'),
    })),
  }));
  return {
    revision: 'rev-4',
    errors: [],
    sets: [
      { key: 'statuses', forms: rows },
      { key: 'types', forms: [{ fields: [{ name: 'types-0-key', value: 'task' }] }] },
    ],
  };
}
const nodes = (data) => workflowNodes(data.sets[0]);

test('graph reads single-select arrays, zero coordinates and excludes deleted rows', () => {
  const data = moveWorkflowNode(fixture(), 'new', { x: 0, y: 0 });
  data.sets[0].forms[5].fields.push({
    name: 'statuses-5-DELETE',
    field_name: 'DELETE',
    checked: true,
  });
  assert.equal(nodes(data).length, 5);
  assert.equal(nodes(data)[0].category, 'new');
  assert.equal(nodes(data)[0].stage, 'queue');
  assert.equal(nodes(data)[0].x, 0);
  assert.equal(nodes(data)[0].y, 0);
  data.sets[0].forms[0].fields.find((field) => field.field_name === 'position_x').value = 0;
  data.sets[0].forms[0].fields.find((field) => field.field_name === 'position_y').value = 0;
  assert.equal(nodes(data)[0].x, 0);
  assert.equal(nodes(data)[0].y, 0);
});

test('connecting is directional, idempotent and preserves other configuration', () => {
  const original = fixture();
  const disconnected = connectWorkflow(original, 'new', 'closed', true);
  const changed = connectWorkflow(connectWorkflow(disconnected, 'new', 'closed'), 'new', 'closed');
  assert.equal(nodes(changed)[0].transitions.filter((key) => key === 'closed').length, 1);
  assert.deepEqual(plain(nodes(changed)[3].transitions), plain(nodes(original)[3].transitions));
  assert.strictEqual(changed.sets[1], original.sets[1]);
  assert.equal(changed.revision, original.revision);
  assert.ok(nodes(original)[0].transitions.includes('closed'));
});

test('self edges and nonexistent endpoints leave the draft untouched', () => {
  const data = fixture();
  for (const [source, target] of [
    ['new', 'new'],
    ['missing', 'closed'],
    ['new', 'missing'],
  ])
    assert.strictEqual(connectWorkflow(data, source, target), data);
});

test('moving only changes layout and keeps valid bounded integer coordinates', () => {
  const original = fixture();
  const changed = moveWorkflowNode(original, 'in_progress', { x: -40, y: 22000.8 });
  assert.equal(nodes(changed)[1].x, 0);
  assert.equal(nodes(changed)[1].y, 20000);
  assert.deepEqual(plain(nodes(changed)[1].transitions), plain(nodes(original)[1].transitions));
  assert.equal(nodes(changed)[1].limit, '4');
  assert.equal(nodes(changed)[1].policy, 'Wymagane sprawdzenie');
  assert.strictEqual(changed.sets[1], original.sets[1]);
});

test('arranging preserves all transition rules', () => {
  const data = fixture();
  const changed = arrangeWorkflow(data);
  assert.deepEqual(
    plain(nodes(changed).map((node) => node.transitions)),
    plain(nodes(data).map((node) => node.transitions)),
  );
  assert.equal(nodes(changed)[5].x, nodes(changed)[1].x);
  assert.ok(nodes(changed)[5].y > nodes(changed)[1].y);
});

test('sequential draft follows review, closure, reopening and pause branches', () => {
  const original = fixture();
  const changed = arrangeWorkflow(original, true);
  assert.deepEqual(
    plain(Object.fromEntries(nodes(changed).map((node) => [node.key, node.transitions]))),
    {
      new: ['in_progress'],
      in_progress: ['resolved', 'on_hold'],
      resolved: ['closed'],
      closed: ['reopened'],
      reopened: ['in_progress'],
      on_hold: ['in_progress'],
    },
  );
  assert.equal(nodes(original)[0].transitions.length, 5);
});
