import { formatMonthLabel } from "../months.js";
import StanceBadge from "./StanceBadge.jsx";

function ProjectCard({ project, onSelectProject }) {
  return (
    <li className="project-card">
      <div className="project-top">
        <div>
          <button
            type="button"
            className="linkish project-link"
            onClick={() => onSelectProject(project.project_id)}
          >
            {project.name}
          </button>
          {project.code ? <span className="project-code">{project.code}</span> : null}
        </div>
        <span className={`stage stage-${project.stage}`}>{project.stage}</span>
      </div>
      <div className="project-meta">
        <span>{project.kind}</span>
        {project.data_center ? <span>data center</span> : null}
        {project.stage_as_of ? <span>as of {project.stage_as_of}</span> : null}
        {project.statement_count > 0 ? <span>{project.statement_count} views</span> : null}
      </div>
      {project.about ? <p className="project-about">{project.about}</p> : null}
      {project.signals?.length ? (
        <div className="signal-row">
          {project.signals.map((signal) => (
            <span key={signal} className="signal">
              {signal}
            </span>
          ))}
        </div>
      ) : null}
      {project.findings?.length ? (
        <ul className="finding-list">
          {project.findings.map((finding) => (
            <li key={finding.finding_id}>
              <div className="finding-top">
                <span className="finding-kind">{finding.kind}</span>
                {finding.finding_date ? <span>{finding.finding_date}</span> : null}
                {finding.stage ? <span>{finding.stage}</span> : null}
              </div>
              <p>{finding.excerpt || finding.body}</p>
            </li>
          ))}
        </ul>
      ) : null}
      <button
        type="button"
        className="text-btn"
        onClick={() => onSelectProject(project.project_id)}
      >
        Open project view →
      </button>
    </li>
  );
}

export default function SidePanel({
  location,
  month,
  projects,
  statements,
  loading,
  error,
  onClose,
  onSelectProject,
  onSelectPerson,
}) {
  if (!location) return null;

  return (
    <aside className="side-panel" aria-label={`${location.name} details`}>
      <div className="side-panel-header">
        <div>
          <p className="eyebrow">{formatMonthLabel(month)}</p>
          <h2>{location.name}</h2>
        </div>
        <button type="button" className="close-btn" onClick={onClose} aria-label="Close">
          ×
        </button>
      </div>

      {loading && <p className="panel-status">Loading details…</p>}
      {error && <p className="panel-status error">{error}</p>}

      {!loading && !error && (
        <>
          <section className="panel-section">
            <h3>Projects & policies</h3>
            {projects.length === 0 ? (
              <p className="panel-status">No projects linked for this month.</p>
            ) : (
              <ul className="project-list">
                {projects.map((project) => (
                  <ProjectCard
                    key={project.project_id}
                    project={project}
                    onSelectProject={onSelectProject}
                  />
                ))}
              </ul>
            )}
          </section>

          <section className="panel-section">
            <h3>People & views</h3>
            {statements.length === 0 ? (
              <p className="panel-status">No people spoke about data centers here this month.</p>
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
                      <StanceBadge stance={row.stance} />
                    </div>
                    <p className="statement-body">{row.excerpt || row.body}</p>
                    <div className="statement-meta">
                      {row.meeting_date ? <span>{row.meeting_date}</span> : null}
                      {row.project_id ? (
                        <button
                          type="button"
                          className="linkish"
                          onClick={() => onSelectProject(row.project_id)}
                        >
                          {row.project_name}
                        </button>
                      ) : row.project_name ? (
                        <span>{row.project_name}</span>
                      ) : null}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </aside>
  );
}
