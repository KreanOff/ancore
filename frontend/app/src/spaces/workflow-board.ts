import type { ConfigurationData, ConfigurationGroup } from './ConfigurationPage';
import { configurationFieldName } from './configuration-form';
import type { Field } from '../forms/FormDialog';
import { configurationColor } from './configuration-appearance';

export const NODE_WIDTH = 220;
export const NODE_HEIGHT = 88;
export interface Position {
  x: number;
  y: number;
}
export interface WorkflowNode extends Position {
  key: string;
  label: string;
  index: number;
  category: string;
  icon?: string;
  color?: string;
  stage: string;
  stageLabel: string;
  limit: string;
  policy: string;
  transitions: string[];
}
const scalar = (field?: Field) =>
  String(Array.isArray(field?.value) ? (field.value[0] ?? '') : (field?.value ?? ''));

export function workflowNodes(group: ConfigurationGroup): WorkflowNode[] {
  return group.forms.flatMap((schema, index) => {
    const fields = Object.fromEntries(
      schema.fields.map((field) => [configurationFieldName(field), field]),
    );
    const key = scalar(fields.key);
    if (!key || fields.DELETE?.checked) return [];
    const category = scalar(fields.category);
    const stage =
      scalar(fields.flow_stage) || { new: 'queue', closed: 'done' }[category] || 'active';
    return [
      {
        key,
        index,
        label: scalar(fields.label) || key,
        category,
        color: configurationColor(fields.color),
        icon: scalar(fields.icon)
          ? fields.icon?.choices?.find((choice) => choice.value === scalar(fields.icon))?.icon
          : undefined,
        stage,
        stageLabel:
          fields.flow_stage?.choices?.find((choice) => choice.value === stage)?.label ||
          { queue: 'Kolejka', active: 'Praca w toku', done: 'Zakończone' }[stage] ||
          stage,
        limit: scalar(fields.wip_limit),
        policy: scalar(fields.policy),
        transitions: Array.isArray(fields.transitions?.value) ? fields.transitions.value : [],
        x: scalar(fields.position_x) !== '' ? Number(scalar(fields.position_x)) : 48 + index * 300,
        y: scalar(fields.position_y) !== '' ? Number(scalar(fields.position_y)) : 160,
      },
    ];
  });
}

export function updateWorkflow(
  data: ConfigurationData,
  changes: Map<string, Record<string, string | string[]>>,
): ConfigurationData {
  return {
    ...data,
    errors: [],
    sets: data.sets.map((group) =>
      group.key !== 'statuses'
        ? group
        : {
            ...group,
            errors: [],
            forms: group.forms.map((schema) => {
              const key = scalar(
                schema.fields.find((field) => configurationFieldName(field) === 'key'),
              );
              const values = changes.get(key);
              return !values
                ? schema
                : {
                    ...schema,
                    errors: [],
                    fields: schema.fields.map((field) => {
                      const value = values[configurationFieldName(field)];
                      return value === undefined ? field : { ...field, value, errors: [] };
                    }),
                  };
            }),
          },
    ),
  };
}

export function moveWorkflowNode(data: ConfigurationData, key: string, point: Position) {
  if (!Number.isFinite(point.x) || !Number.isFinite(point.y)) return data;
  return updateWorkflow(
    data,
    new Map([
      [
        key,
        {
          position_x: String(Math.max(-1000000, Math.min(1000000, Math.round(point.x)))),
          position_y: String(Math.max(-1000000, Math.min(1000000, Math.round(point.y)))),
        },
      ],
    ]),
  );
}

export function connectWorkflow(
  data: ConfigurationData,
  source: string,
  target: string,
  remove = false,
) {
  const group = data.sets.find((group) => group.key === 'statuses');
  if (!group || source === target) return data;
  const nodes = workflowNodes(group);
  const node = nodes.find((node) => node.key === source);
  if (!node || !nodes.some((node) => node.key === target)) return data;
  if (node.transitions.includes(target) !== remove) return data;
  const transitions = node.transitions.filter((key) => key !== target);
  if (!remove) transitions.push(target);
  return updateWorkflow(data, new Map([[source, { transitions }]]));
}

export function arrangeWorkflow(data: ConfigurationData, connect = false) {
  const group = data.sets.find((group) => group.key === 'statuses');
  if (!group) return data;
  const nodes = workflowNodes(group);
  if (!connect) {
    const positions = workflowPositions(nodes);
    const changes = new Map<string, Record<string, string>>();
    nodes.forEach((node) => {
      const point = positions.get(node.key)!;
      if (node.x !== point.x || node.y !== point.y)
        changes.set(node.key, { position_x: String(point.x), position_y: String(point.y) });
    });
    return changes.size ? updateWorkflow(data, changes) : data;
  }
  const main = nodes.filter((node) => !['on_hold', 'onhold'].includes(node.key));
  const progress =
    main.find((node) => node.key === 'in_progress') || main.find((node) => node.stage === 'active');
  const changes = new Map<string, Record<string, string | string[]>>();
  main.forEach((node, index) => {
    const values: Record<string, string | string[]> = {
      position_x: String(48 + index * 300),
      position_y: '160',
    };
    if (connect)
      values.transitions = main[index + 1]
        ? [main[index + 1].key]
        : node.key === 'reopened' && progress
          ? [progress.key]
          : [];
    changes.set(node.key, values);
  });
  nodes
    .filter((node) => !main.includes(node))
    .forEach((node, index) => {
      const values: Record<string, string | string[]> = {
        position_x: String(48 + Math.max(0, main.indexOf(progress!)) * 300),
        position_y: String(340 + index * 150),
      };
      if (connect) {
        values.transitions = progress ? [progress.key] : [];
        if (progress) (changes.get(progress.key)!.transitions as string[]).push(node.key);
      }
      changes.set(node.key, values);
    });
  return updateWorkflow(data, changes);
}

function workflowGraph(nodes: WorkflowNode[]) {
  const keys = new Set(nodes.map((node) => node.key));
  const outgoing = new Map(
    nodes.map((node) => [
      node.key,
      [...new Set(node.transitions)].filter((key) => keys.has(key) && key !== node.key),
    ]),
  );
  const incoming = new Map(nodes.map((node) => [node.key, [] as string[]]));
  outgoing.forEach((targets, source) => targets.forEach((key) => incoming.get(key)!.push(source)));
  return { outgoing, incoming };
}

/** Layout follows the graph; feedback edges remain transitions but do not advance a column. */
function workflowPositions(nodes: WorkflowNode[]): Map<string, Position> {
  const positions = new Map<string, Position>();
  if (!nodes.length) return positions;
  const { outgoing, incoming } = workflowGraph(nodes);
  const initial = nodes.find((node) => node.stage === 'queue') || nodes[0];
  const order = new Map(nodes.map((node, index) => [node.key, index]));
  const sorted = (keys: string[]) => [...keys].sort((a, b) => order.get(a)! - order.get(b)!);
  const neighbors = (key: string) => [...new Set([...outgoing.get(key)!, ...incoming.get(key)!])];
  const remaining = new Set(nodes.map((node) => node.key));
  let top = 160;

  for (const root of [initial, ...nodes.filter((node) => node !== initial)]) {
    if (!remaining.has(root.key)) continue;
    // Separate disconnected components without letting their cards overlap the main process.
    const component = new Set<string>();
    const collect = (key: string) => {
      if (component.has(key)) return;
      component.add(key);
      remaining.delete(key);
      neighbors(key).forEach(collect);
    };
    collect(root.key);
    const members = sorted([...component]);
    const start =
      root === initial
        ? root.key
        : members.find((key) => nodes[order.get(key)!].stage === 'queue') ||
          members.find((key) => !incoming.get(key)!.length) ||
          root.key;
    // A reversible, single-neighbor branch (e.g. pause) belongs below its parent.
    const satellites = new Map<string, string>();
    members.forEach((key) => {
      const targets = outgoing.get(key)!;
      if (
        key !== start &&
        nodes[order.get(key)!].stage !== 'done' &&
        targets.length === 1 &&
        incoming.get(key)!.length === 1 &&
        incoming.get(key)![0] === targets[0] &&
        neighbors(targets[0]).length > 1
      )
        satellites.set(key, targets[0]);
    });
    const main = [start, ...members.filter((key) => key !== start && !satellites.has(key))];
    const state = new Map<string, number>();
    const forward = new Map(main.map((key) => [key, [] as string[]]));
    const finished: string[] = [];
    const visit = (key: string) => {
      if (state.has(key)) return;
      state.set(key, 1);
      sorted(outgoing.get(key)!).forEach((target) => {
        if (target === start || satellites.has(target) || state.get(target) === 1) return;
        forward.get(key)!.push(target);
        visit(target);
      });
      state.set(key, 2);
      finished.push(key);
    };
    visit(start);
    main.forEach(visit);
    const ranks = new Map(main.map((key) => [key, 0]));
    finished
      .reverse()
      .forEach((key) =>
        forward
          .get(key)!
          .forEach((target) =>
            ranks.set(target, Math.max(ranks.get(target)!, ranks.get(key)! + 1)),
          ),
      );
    satellites.forEach((parent, key) => ranks.set(key, ranks.get(parent)!));
    const rows = new Map<number, number>();
    // Keep branches together, with a stable order independent of previous coordinates.
    [...main, ...satellites.keys()].forEach((key) => {
      const rank = ranks.get(key)!;
      const row = rows.get(rank) || 0;
      positions.set(key, { x: 48 + rank * 300, y: top + row * 152 });
      rows.set(rank, row + 1);
    });
    top += Math.max(...rows.values()) * 152 + 96;
  }
  return positions;
}

/** Advisory checks only: returning to earlier stages is a valid part of a workflow. */
export function workflowIssues(nodes: WorkflowNode[]): Array<{ key: string; message: string }> {
  const issues: Array<{ key: string; message: string }> = [];
  const initial = nodes.find((node) => node.stage === 'queue');
  const completed = nodes.filter((node) => node.stage === 'done');
  if (!initial)
    issues.push({
      key: '',
      message: 'Dodaj etap z grupy „Kolejka”, aby określić początek procesu.',
    });
  if (!nodes.some((node) => node.stage === 'active'))
    issues.push({
      key: '',
      message: 'Dodaj etap z grupy „Praca w toku”, aby określić, gdzie trwa realizacja zadania.',
    });
  if (!completed.length)
    issues.push({
      key: '',
      message: 'Dodaj etap z grupy „Zakończone”, aby zadania mogły zakończyć proces.',
    });
  if (!nodes.length) return issues;
  const { outgoing, incoming } = workflowGraph(nodes);
  const reachable = (starts: string[], graph: Map<string, string[]>) => {
    const found = new Set<string>();
    const visit = (key: string) => {
      if (found.has(key)) return;
      found.add(key);
      graph.get(key)!.forEach(visit);
    };
    starts.forEach(visit);
    return found;
  };
  const fromStart = reachable([(initial || nodes[0]).key], outgoing);
  const toDone = reachable(
    completed.map((node) => node.key),
    incoming,
  );
  nodes.forEach((node) => {
    let message = '';
    if (!fromStart.has(node.key))
      message = `Etap „${node.label}” jest nieosiągalny od początku procesu.`;
    else if (node.stage !== 'done' && !outgoing.get(node.key)!.length)
      message = `Etap „${node.label}” nie ma przejścia dalej.`;
    else if (node.stage !== 'done' && completed.length && !toDone.has(node.key))
      message = `Z etapu „${node.label}” nie można dojść do zakończenia.`;
    if (message) issues.push({ key: node.key, message });
  });
  return issues;
}

export function transitionPath(source: Position, target: Position, lane: number) {
  const sx = source.x + NODE_WIDTH / 2,
    tx = target.x + NODE_WIDTH / 2;
  if (Math.abs(source.y - target.y) > NODE_HEIGHT + 24) {
    const down = target.y > source.y;
    const offset = down ? -22 : 22;
    const start = source.y + (down ? NODE_HEIGHT : 0),
      end = target.y + (down ? 0 : NODE_HEIGHT);
    const middle = (start + end) / 2;
    return `M ${sx + offset} ${start} C ${sx + offset} ${middle}, ${tx + offset} ${middle}, ${tx + offset} ${end}`;
  }
  if (target.x > source.x + NODE_WIDTH && target.x - source.x < NODE_WIDTH * 2) {
    const start = source.x + NODE_WIDTH,
      end = target.x;
    return `M ${start} ${source.y + NODE_HEIGHT / 2} C ${(start + end) / 2} ${source.y + NODE_HEIGHT / 2}, ${(start + end) / 2} ${target.y + NODE_HEIGHT / 2}, ${end} ${target.y + NODE_HEIGHT / 2}`;
  }
  const clearance = 48 + (lane % 5) * 20;
  const start = source.y;
  const end = target.y;
  const bend = Math.min(start, end) - clearance;
  return `M ${sx + 24} ${start} C ${sx + 24} ${bend}, ${tx - 24} ${bend}, ${tx - 24} ${end}`;
}
