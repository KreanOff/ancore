import WidgetCatalog from '../shared/WidgetCatalog';
import GadgetCard from './Gadget';
import type { DetailData, Gadget } from './types';

// Catalog samples use the real gadget renderer, with explicit example values.
const progressSample: Gadget = {
  id: 0,
  kind: 'progress',
  label: 'Postęp pracy',
  icon: 'chart-no-axes-combined',
  edit_url: '',
  delete_url: '',
  unavailable: false,
  count: 20,
  closed_count: 8,
  percent: 40,
  caption: 'Zadania we wszystkich przestrzeniach Workspace',
  statuses: [
    { key: 'new', label: 'Nowe', count: 6 },
    { key: 'in_progress', label: 'Realizowane', count: 4 },
    { key: 'resolved', label: 'Rozwiązane', count: 2 },
    { key: 'closed', label: 'Zamknięte', count: 8 },
    { key: 'reopened', label: 'Ponownie otwarte', count: 0 },
  ],
};

export default function Catalog({
  data,
  busy,
  count,
  add,
  close,
}: {
  data: DetailData;
  busy: boolean;
  count: number;
  add: (kind: string) => void;
  close: () => void;
}) {
  return (
    <WidgetCatalog
      items={data.gadget_catalog.map((entry) => ({
        id: entry.kind,
        label: entry.name,
        description: entry.description,
        previewWidth: 480,
        previewHeight: 420,
        previewCaption: 'Przykładowe dane',
        preview: (
          <div className="dashboard-overview pulpits-page">
            <GadgetCard data={progressSample} />
          </div>
        ),
      }))}
      onAdd={add}
      onClose={close}
      disabled={busy}
      limitMessage={
        count >= data.max_gadgets
          ? `Osiągnięto limit ${data.max_gadgets} gadżetów. Usuń jeden, aby dodać kolejny.`
          : ''
      }
    />
  );
}
