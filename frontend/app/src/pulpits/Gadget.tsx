import { Icon } from '../shared/Icon';
import type { Gadget as GadgetData } from './types';
export default function Gadget({ data, preview = false }: { data: GadgetData; preview?: boolean }) {
  return (
    <article className="dashboard-panel pulpit-gadget" data-gadget-id={data.id || undefined}>
      <header className="dashboard-panel-header pulpit-gadget-header">
        <h2>{data.label}</h2>
        <Icon name={data.icon} />
      </header>
      {preview ? (
        <div className="pulpit-gadget-body pulpit-gadget-empty-state">
          <Icon name={data.icon} className="pulpit-gadget-empty-icon" />
          <p className="pulpit-gadget-empty">Dane pojawią się po zapisaniu układu.</p>
        </div>
      ) : data.unavailable ? (
        <div className="pulpit-gadget-body">
          <div className="pulpit-gadget-empty-state">
            <Icon name="lock" className="pulpit-gadget-empty-icon" />
            <p className="pulpit-gadget-empty">
              Nie masz dostępu do źródłowej przestrzeni tego gadżetu.
            </p>
          </div>
        </div>
      ) : (
        <div className="dashboard-overview-progress">
          <div className="dashboard-overview-progress-total">
            <strong>
              {data.percent}
              <span>%</span>
            </strong>
            <span>
              Zamknięte: {data.closed_count} z {data.count}
            </span>
          </div>
          <progress max={100} value={data.percent} aria-label="Odsetek zamkniętych zadań">
            {data.percent}%
          </progress>
          <p className="dashboard-overview-caption">{data.caption}</p>
          <dl className="dashboard-overview-statuses">
            {data.statuses?.map((status) => (
              <div key={status.key}>
                <dt>
                  <span className={`status-indicator status-${status.key}`} aria-hidden="true" />
                  {status.label}
                </dt>
                <dd>{status.count}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}
    </article>
  );
}
