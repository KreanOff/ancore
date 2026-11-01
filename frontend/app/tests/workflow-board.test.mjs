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
const {
  workflowNodes,
  connectWorkflow,
  moveWorkflowNode,
  arrangeWorkflow,
  workflowIssues,
  transitionPath,
  NODE_WIDTH,
  NODE_HEIGHT,
} = module.exports;
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
function graphFixture(stages) {
  const data = fixture();
  const fields = data.sets[0].forms[0].fields;
  data.sets[0].forms = stages.map((stage, index) => ({
    fields: fields.map((field) => ({
      ...field,
      name: `statuses-${index}-${field.field_name}`,
      value:
        {
          key: stage.key,
          label: stage.label || stage.key,
          flow_stage: [stage.stage || 'active'],
          transitions: stage.transitions || [],
        }[field.field_name] ?? field.value,
    })),
  }));
  return data;
}
const indexed = (data) => Object.fromEntries(nodes(data).map((node) => [node.key, node]));
function assertNoOverlaps(data) {
  const cards = nodes(data);
  cards.forEach((card, index) => {
    assert.ok(Number.isFinite(card.x) && Number.isFinite(card.y));
    assert.ok(card.x >= 0 && card.y >= 0);
    cards.slice(index + 1).forEach((other) => {
      assert.ok(
        Math.abs(card.x - other.x) >= NODE_WIDTH || Math.abs(card.y - other.y) >= NODE_HEIGHT,
        `${card.key} overlaps ${other.key}`,
      );
    });
  });
}

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
  assert.strictEqual(connectWorkflow(original, 'new', 'closed'), original);
  assert.strictEqual(connectWorkflow(disconnected, 'new', 'closed', true), disconnected);
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

test('moving supports signed map coordinates while preserving workflow rules', () => {
  const original = fixture();
  const changed = moveWorkflowNode(original, 'in_progress', { x: -40.4, y: 22000.8 });
  assert.equal(nodes(changed)[1].x, -40);
  assert.equal(nodes(changed)[1].y, 22001);
  assert.deepEqual(plain(nodes(changed)[1].transitions), plain(nodes(original)[1].transitions));
  assert.equal(nodes(changed)[1].limit, '4');
  assert.equal(nodes(changed)[1].policy, 'Wymagane sprawdzenie');
  assert.strictEqual(changed.sets[1], original.sets[1]);
});

test('moving clamps both map axes to backend bounds and ignores nonfinite input', () => {
  const original = fixture();
  for (const point of [
    { x: -2000000, y: 2000000 },
    { x: 2000000, y: -2000000 },
  ]) {
    const changed = moveWorkflowNode(original, 'new', point);
    assert.equal(nodes(changed)[0].x, Math.sign(point.x) * 1000000);
    assert.equal(nodes(changed)[0].y, Math.sign(point.y) * 1000000);
  }
  for (const point of [
    { x: NaN, y: 0 },
    { x: 0, y: Infinity },
    { x: -Infinity, y: 0 },
  ])
    assert.strictEqual(moveWorkflowNode(original, 'new', point), original);
});

test('arranging preserves all transition rules', () => {
  const data = fixture();
  const changed = arrangeWorkflow(data);
  assert.deepEqual(
    plain(nodes(changed).map((node) => node.transitions)),
    plain(nodes(data).map((node) => node.transitions)),
  );
  assertNoOverlaps(changed);
  assert.deepEqual(
    plain(nodes(changed).map(({ x, y, ...node }) => node)),
    plain(nodes(data).map(({ x, y, ...node }) => node)),
  );
  assert.strictEqual(changed.sets[1], data.sets[1]);
});

test('arrangement follows branches and merges with arbitrary keys and form order', () => {
  const original = graphFixture([
    { key: 'verify', transitions: ['archive'] },
    { key: 'write', transitions: ['verify'] },
    { key: 'entry', stage: 'queue', transitions: ['write', 'translate', 'archive'] },
    { key: 'translate', transitions: ['verify'] },
    { key: 'archive', stage: 'done' },
  ]);
  const changed = arrangeWorkflow(original);
  const cards = indexed(changed);
  for (const [source, targets] of Object.entries({
    entry: ['write', 'translate'],
    write: ['verify'],
    translate: ['verify'],
    verify: ['archive'],
  }))
    targets.forEach((target) => assert.ok(cards[source].x < cards[target].x));
  assert.equal(cards.entry.x, 48);
  assert.equal(cards.write.x, cards.translate.x);
  assert.notEqual(cards.write.y, cards.translate.y);
  assertNoOverlaps(changed);
});

test('arrangement keeps reopening cycles and custom reversible branches readable', () => {
  const original = graphFixture([
    { key: 'received', stage: 'queue', transitions: ['working'] },
    { key: 'working', transitions: ['review', 'waiting'] },
    { key: 'review', transitions: ['finished'] },
    { key: 'finished', stage: 'done', transitions: ['again'] },
    { key: 'again', transitions: ['working'] },
    { key: 'waiting', transitions: ['working'] },
  ]);
  const changed = arrangeWorkflow(original);
  const cards = indexed(changed);
  assert.ok(cards.received.x < cards.working.x);
  assert.ok(cards.working.x < cards.review.x);
  assert.ok(cards.review.x < cards.finished.x);
  assert.ok(cards.finished.x < cards.again.x);
  assert.equal(cards.waiting.x, cards.working.x);
  assert.ok(cards.waiting.y > cards.working.y);
  assert.deepEqual(plain(cards.again.transitions), ['working']);
  assert.deepEqual(plain(cards.working.transitions), ['review', 'waiting']);
  assertNoOverlaps(changed);
  assert.deepEqual(plain(workflowIssues(nodes(changed))), []);
});

test('disconnected components, cycles and dangling targets arrange deterministically without overlaps', () => {
  const original = graphFixture([
    { key: 'first', stage: 'queue', transitions: ['second', 'deleted'] },
    { key: 'second', transitions: ['last'] },
    { key: 'last', stage: 'done' },
    { key: 'isolated' },
    { key: 'cycle-a', transitions: ['cycle-b'] },
    { key: 'cycle-b', transitions: ['cycle-a'] },
    { key: 'another-queue', stage: 'queue', transitions: ['another-end'] },
    { key: 'another-end', stage: 'done' },
  ]);
  const changed = arrangeWorkflow(original);
  assertNoOverlaps(changed);
  assert.strictEqual(arrangeWorkflow(changed), changed);
  assert.deepEqual(plain(arrangeWorkflow(original)), plain(changed));
  const moved = moveWorkflowNode(original, 'second', { x: 12000, y: 12000 });
  assert.deepEqual(plain(nodes(arrangeWorkflow(moved))), plain(nodes(changed)));
  assert.deepEqual(plain(indexed(changed).first.transitions), ['second', 'deleted']);
});

test('advisories distinguish unreachable stages, dead ends and a cycle without a way to completion', () => {
  const data = graphFixture([
    { key: 'begin', stage: 'queue', transitions: ['dead-end', 'loop-a', 'complete'] },
    { key: 'dead-end', transitions: ['missing', 'dead-end'] },
    { key: 'loop-a', transitions: ['loop-b'] },
    { key: 'loop-b', transitions: ['loop-a'] },
    { key: 'complete', stage: 'done' },
    { key: 'unreachable', transitions: ['complete'] },
  ]);
  const issues = plain(workflowIssues(nodes(data)));
  assert.deepEqual(
    issues.map((issue) => issue.key),
    ['dead-end', 'loop-a', 'loop-b', 'unreachable'],
  );
  assert.match(issues[0].message, /nie ma przejścia dalej/);
  assert.match(issues[1].message, /nie można dojść do zakończenia/);
  assert.match(issues[3].message, /nieosiągalny/);
});

test('advisories use the first queue as start and fall back to the first node', () => {
  const data = graphFixture([
    { key: 'working', transitions: ['done'] },
    { key: 'begin', stage: 'queue', transitions: ['working'] },
    { key: 'later', stage: 'queue', transitions: ['done'] },
    { key: 'done', stage: 'done' },
  ]);
  assert.deepEqual(
    plain(workflowIssues(nodes(data))).map((issue) => issue.key),
    ['later'],
  );
  const noQueue = graphFixture([
    { key: 'working', transitions: ['done'] },
    { key: 'done', stage: 'done' },
  ]);
  const issues = plain(workflowIssues(nodes(noQueue)));
  assert.equal(issues.length, 1);
  assert.equal(issues[0].key, '');
  assert.match(issues[0].message, /Kolejka/);
});

test('missing required stage groups are global advisories without redundant completion warnings', () => {
  const data = graphFixture([
    { key: 'one', transitions: ['two'] },
    { key: 'two', transitions: ['one'] },
  ]);
  const issues = plain(workflowIssues(nodes(data)));
  assert.equal(issues.length, 2);
  assert.ok(issues.every((issue) => issue.key === ''));
  assert.match(issues[0].message, /Kolejka/);
  assert.match(issues[1].message, /Zakończone/);
  assert.equal(workflowIssues([]).length, 3);
  const empty = graphFixture([]);
  assert.strictEqual(arrangeWorkflow(empty), empty);
});

test('a direct queue-to-completion process is missing the required active group', () => {
  const data = graphFixture([
    { key: 'begin', stage: 'queue', transitions: ['done'] },
    { key: 'done', stage: 'done' },
  ]);
  const issues = plain(workflowIssues(nodes(data)));
  assert.equal(issues.length, 1);
  assert.equal(issues[0].key, '');
  assert.match(issues[0].message, /Praca w toku/);
});

test('dense cyclic graphs arrange without overlaps or changes to their transitions', () => {
  let seed = 30417;
  const random = () => {
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
    return seed / 4294967296;
  };
  for (let sample = 0; sample < 25; sample++) {
    const keys = Array.from({ length: 30 }, (_, index) => `step-${index}`);
    const data = graphFixture(
      keys.map((key, index) => ({
        key,
        stage: index === 10 ? 'queue' : index === 29 ? 'done' : 'active',
        transitions: keys.filter((other) => other !== key && random() < 0.3),
      })),
    );
    const arranged = arrangeWorkflow(data);
    assertNoOverlaps(arranged);
    assert.equal(indexed(arranged)['step-10'].x, 48);
    assert.strictEqual(arrangeWorkflow(arranged), arranged);
    assert.deepEqual(
      plain(nodes(arranged).map((node) => node.transitions)),
      plain(nodes(data).map((node) => node.transitions)),
    );
  }
});

test('opposing adjacent arrows use separate horizontal and vertical routes', () => {
  const first = { x: 48, y: 160 };
  const right = { x: 348, y: 160 };
  const below = { x: 48, y: 312 };
  assert.match(transitionPath(first, right, 0), /^M 268 204 /);
  assert.match(transitionPath(right, first, 1), /^M 482 160 /);
  assert.match(transitionPath(first, below, 0), /^M 136 248 /);
  assert.match(transitionPath(below, first, 1), /^M 180 312 /);
});

test('return arrows keep their shape across the world origin', () => {
  const path = transitionPath({ x: 348, y: 0 }, { x: 48, y: 0 }, 0);
  const coordinates = path.match(/-?\d+(?:\.\d+)?/g).map(Number);
  const vertical = coordinates.filter((_, index) => index % 2 === 1);
  assert.ok(vertical.every((y) => y <= 0));
  assert.ok(vertical.some((y) => y < 0));
  const translated = transitionPath({ x: -652, y: -800 }, { x: -952, y: -800 }, 0)
    .match(/-?\d+(?:\.\d+)?/g)
    .map(Number);
  assert.deepEqual(
    translated,
    coordinates.map((value, index) => value - (index % 2 ? 800 : 1000)),
  );
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
