import StanceBadge from "./StanceBadge.jsx";

export default function ProjectView({
  project,
  findings,
  statements,
  loading,
  error,
  onBack,
  onSelectPerson,
}) {
  return (
    <div className="detail-view">
      <button type="button" className="back-btn" onClick={onBack}>
        ← Back to locations
      </button>

      {loading && <p className="empty">Loading project…</p>}
      {error && <p className="empty error">{error}</p>}

      {!loading && !error && project && (
        <>
          <header className="detail-header">
            <p className="eyebrow">{project.kind}{project.location ? ` · ${project.location}` : ""}</p>
            <h1>{project.name}</h1>
            <div className="detail-meta">
              {project.code ? <span className="project-code">{project.code}</span> : null}
              <span className={`stage stage-${project.stage}`}>{project.stage}</span>
              {project.stage_as_of ? <span>as of {project.stage_as_of}</span> : null}
              {project.data_center ? <span>data center</span> : null}
            </div>
            {project.about ? <p className="detail-about">{project.about}</p> : null}
            {project.signals?.length ? (
              <div className="signal-row">
                {project.signals.map((signal) => (
                  <span key={signal} className="signal">
                    {signal}
                  </span>
                ))}
              </div>
            ) : null}
          </header>

          <section className="panel-section">
            <h3>Findings over time</h3>
            {findings.length === 0 ? (
              <p className="panel-status">No dated findings stored for this project.</p>
            ) : (
              <ul className="finding-list detail-findings">
                {findings.map((finding) => (
                  <li key={finding.finding_id}>
                    <div className="finding-top">
                      <span className="finding-kind">{finding.kind}</span>
                      {finding.finding_date ? <span>{finding.finding_date}</span> : null}
                      {finding.stage ? <span>{finding.stage}</span> : null}
                      {finding.prior_stage ? <span>from {finding.prior_stage}</span> : null}
                    </div>
                    <p>{finding.excerpt || finding.body}</p>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="panel-section">
            <h3>People&apos;s views</h3>
            {statements.length === 0 ? (
              <p className="panel-status">No linked statements on this project yet.</p>
            ) : (
              <ul className="statement-list">
                {statements.map((row) => (
                  <li key={row.fact_id} className="statement-card">
                    <div className="statement-top">
                      <div>
                        {row.person_id ? (
                          <button
                            type="button"
                            className="linkish"
                            onClick={() => onSelectPerson(row.person_id)}
                          >
                            {row.person_name || "Unidentified speaker"}
                          </button>
                        ) : (
                          <strong>{row.person_name || "Unidentified speaker"}</strong>
                        )}
                        {row.person_kind ? <span className="kind">{row.person_kind}</span> : null}
                      </div>
                      <div className="stance-stack">
                        {row.prior_stance && row.prior_stance !== row.stance ? (
                          <span className="stance-change">
                            was {row.prior_stance} →
                          </span>
                        ) : null}
                        <StanceBadge stance={row.stance} />
                      </div>
                    </div>
                    <p className="statement-body">{row.excerpt || row.body}</p>
                    <div className="statement-meta">
                      {row.meeting_date ? <span>{row.meeting_date}</span> : null}
                      {row.title ? <span>{row.title}</span> : null}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </div>
  );
}
