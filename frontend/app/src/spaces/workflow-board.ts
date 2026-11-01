import type { ConfigurationData, ConfigurationGroup } from './ConfigurationPage';
import { configurationFieldName } from './configuration-form';
import type { Field } from '../forms/FormDialog';

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
  return updateWorkflow(
    data,
    new Map([
      [
        key,
        {
          position_x: String(Math.max(0, Math.min(20000, Math.round(point.x)))),
          position_y: String(Math.max(0, Math.min(20000, Math.round(point.y)))),
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
  const transitions = node.transitions.filter((key) => key !== target);
  if (!remove) transitions.push(target);
  return updateWorkflow(data, new Map([[source, { transitions }]]));
}

export function arrangeWorkflow(data: ConfigurationData, connect = false) {
  const group = data.sets.find((group) => group.key === 'statuses');
  if (!group) return data;
  const nodes = workflowNodes(group);
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
  const top = Math.max(12, Math.min(source.y, target.y) - 48 - (lane % 5) * 20);
  return `M ${sx + 24} ${source.y} C ${sx + 24} ${top}, ${tx - 24} ${top}, ${tx - 24} ${target.y}`;
}
