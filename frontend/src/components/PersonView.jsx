import StanceBadge from "./StanceBadge.jsx";

export default function PersonView({
  person,
  statements,
  loading,
  error,
  onBack,
  onSelectProject,
}) {
  const changes = statements.filter(
    (row) => row.prior_stance && row.stance && row.prior_stance !== row.stance
  );

  return (
    <div className="detail-view">
      <button type="button" className="back-btn" onClick={onBack}>
        ← Back
      </button>

      {loading && <p className="empty">Loading person…</p>}
      {error && <p className="empty error">{error}</p>}

      {!loading && !error && person && (
        <>
          <header className="detail-header">
            <p className="eyebrow">
              {person.kind || "person"}
              {person.role ? ` · ${person.role}` : ""}
            </p>
            <h1>{person.name}</h1>
            <div className="detail-meta">
              {person.address ? <span>{person.address}</span> : null}
              {person.department ? <span>{person.department}</span> : null}
              <span>{statements.length} statements</span>
              {changes.length ? <span>{changes.length} stance changes</span> : null}
            </div>
          </header>

          <section className="panel-section">
            <h3>Views over time</h3>
            {statements.length === 0 ? (
              <p className="panel-status">No statements stored for this person.</p>
            ) : (
              <ol className="timeline">
                {statements.map((row) => {
                  const changed =
                    row.prior_stance && row.stance && row.prior_stance !== row.stance;
                  return (
                    <li key={row.fact_id} className={`timeline-item${changed ? " changed" : ""}`}>
                      <div className="timeline-rail" aria-hidden="true" />
                      <div className="statement-card">
                        <div className="statement-top">
                          <div>
                            <strong>{row.meeting_date || "Undated"}</strong>
                            {row.title ? <span className="kind">{row.title}</span> : null}
                          </div>
                          <div className="stance-stack">
                            {changed ? (
                              <span className="stance-change">
                                was {row.prior_stance} →
                              </span>
                            ) : null}
                            <StanceBadge stance={row.stance} />
                          </div>
                        </div>
                        <p className="statement-body">{row.excerpt || row.body}</p>
                        <div className="statement-meta">
                          {row.project_id ? (
                            <button
                              type="button"
                              className="linkish"
                              onClick={() => onSelectProject(row.project_id)}
                            >
                              {row.project}
                            </button>
                          ) : row.project ? (
                            <span>{row.project}</span>
                          ) : null}
                        </div>
                      </div>
                    </li>
                  );
                })}
              </ol>
            )}
          </section>
        </>
      )}
    </div>
  );
}
