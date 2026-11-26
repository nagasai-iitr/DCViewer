import { useEffect, useMemo, useState } from "react";
import {
  fetchDefaultMonth,
  fetchLocationProjects,
  fetchLocationStatements,
  fetchPerson,
  fetchPersonStatements,
  fetchProject,
  fetchProjectFindings,
  fetchProjectStatements,
  fetchSentiment,
} from "./api.js";
import CorpusRunPanel from "./components/CorpusRunPanel.jsx";
import LocationList from "./components/LocationList.jsx";
import MonthScrubber from "./components/MonthScrubber.jsx";
import PersonView from "./components/PersonView.jsx";
import ProjectView from "./components/ProjectView.jsx";
import SidePanel from "./components/SidePanel.jsx";
import { buildMonths } from "./months.js";

export default function App() {
  const months = useMemo(() => buildMonths(), []);
  const [month, setMonth] = useState(months[months.length - 1]);
  const [locations, setLocations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(null);
  const [projects, setProjects] = useState([]);
  const [statements, setStatements] = useState([]);
  const [panelLoading, setPanelLoading] = useState(false);
  const [panelError, setPanelError] = useState("");

  const [view, setView] = useState("locations"); // locations | project | person
  const [projectId, setProjectId] = useState(null);
  const [personId, setPersonId] = useState(null);
  const [returnView, setReturnView] = useState("locations");

  const [project, setProject] = useState(null);
  const [projectFindings, setProjectFindings] = useState([]);
  const [projectStatements, setProjectStatements] = useState([]);
  const [projectLoading, setProjectLoading] = useState(false);
  const [projectError, setProjectError] = useState("");

  const [person, setPerson] = useState(null);
  const [personStatements, setPersonStatements] = useState([]);
  const [personLoading, setPersonLoading] = useState(false);
  const [personError, setPersonError] = useState("");

  useEffect(() => {
    let cancelled = false;
    fetchDefaultMonth()
      .then((data) => {
        if (!cancelled && data.month && months.includes(data.month)) {
          setMonth(data.month);
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [months]);

  useEffect(() => {
    if (view !== "locations") return undefined;
    let cancelled = false;
    setLoading(true);
    setError("");
    fetchSentiment(month)
      .then((rows) => {
        if (!cancelled) {
          setLocations(rows);
          setSelected((current) => {
            if (!current) return null;
            return rows.find((row) => row.location_id === current.location_id) || current;
          });
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message || "Failed to load locations");
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [month, view]);

  useEffect(() => {
    if (view !== "locations" || !selected) {
      if (!selected) {
        setProjects([]);
        setStatements([]);
        setPanelError("");
      }
      return undefined;
    }
    let cancelled = false;
    setPanelLoading(true);
    setPanelError("");
    Promise.all([
      fetchLocationProjects(selected.location_id, month),
      fetchLocationStatements(selected.location_id, month),
    ])
      .then(([projectRows, statementRows]) => {
        if (!cancelled) {
          setProjects(projectRows);
          setStatements(statementRows);
          setPanelLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setPanelError(err.message || "Failed to load location details");
          setPanelLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selected, month, view]);

  useEffect(() => {
    if (view !== "project" || !projectId) return undefined;
    let cancelled = false;
    setProjectLoading(true);
    setProjectError("");
    Promise.all([
      fetchProject(projectId),
      fetchProjectFindings(projectId),
      fetchProjectStatements(projectId),
    ])
      .then(([projectRow, findings, statementRows]) => {
        if (!cancelled) {
          setProject(projectRow);
          setProjectFindings(findings);
          setProjectStatements(statementRows);
          setProjectLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setProjectError(err.message || "Failed to load project");
          setProjectLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [view, projectId]);

  useEffect(() => {
    if (view !== "person" || !personId) return undefined;
    let cancelled = false;
    setPersonLoading(true);
    setPersonError("");
    Promise.all([fetchPerson(personId), fetchPersonStatements(personId)])
      .then(([personRow, statementRows]) => {
        if (!cancelled) {
          setPerson(personRow);
          setPersonStatements(statementRows);
          setPersonLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setPersonError(err.message || "Failed to load person");
          setPersonLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [view, personId]);

  function openProject(id) {
    setReturnView(view);
    setProjectId(id);
    setView("project");
  }

  function openPerson(id) {
    setReturnView(view);
    setPersonId(id);
    setView("person");
  }

  function backFromProject() {
    if (returnView === "person" && personId) {
      setView("person");
    } else {
      setView("locations");
    }
  }

  function backFromPerson() {
    if (returnView === "project" && projectId) {
      setView("project");
    } else {
      setView("locations");
    }
  }

  if (view === "project") {
    return (
      <div className="app">
        <ProjectView
          project={project}
          findings={projectFindings}
          statements={projectStatements}
          loading={projectLoading}
          error={projectError}
          onBack={backFromProject}
          onSelectPerson={openPerson}
        />
      </div>
    );
  }

  if (view === "person") {
    return (
      <div className="app">
        <PersonView
          person={person}
          statements={personStatements}
          loading={personLoading}
          error={personError}
          onBack={backFromPerson}
          onSelectProject={openProject}
        />
      </div>
    );
  }

  return (
    <div className={`app${selected ? " panel-open" : ""}`}>
      <header className="top">
        <div>
          <p className="eyebrow">DCViewer</p>
          <h1>Data center views</h1>
          <p className="subtitle">Community stance by location, month by month.</p>
        </div>
        <MonthScrubber months={months} value={month} onChange={setMonth} />
      </header>

      <ul className="legend" aria-label="Tile color meaning">
        <li>
          <span className="legend-swatch tone-oppose" aria-hidden="true" />
          Mostly oppose (≥70%)
        </li>
        <li>
          <span className="legend-swatch tone-support" aria-hidden="true" />
          Mostly support (≥70%)
        </li>
        <li>
          <span className="legend-swatch tone-mixed" aria-hidden="true" />
          Mixed views
        </li>
        <li>
          <span className="legend-swatch tone-none" aria-hidden="true" />
          No views this month
        </li>
      </ul>

      <CorpusRunPanel />

      <main className="main">
        <section className="locations">
          {loading && <p className="empty">Loading locations…</p>}
          {error && <p className="empty error">{error}</p>}
          {!loading && !error && (
            <LocationList
              locations={locations}
              selectedId={selected?.location_id}
              onSelect={setSelected}
            />
          )}
        </section>

        <SidePanel
          location={selected}
          month={month}
          projects={projects}
          statements={statements}
          loading={panelLoading}
          error={panelError}
          onClose={() => setSelected(null)}
          onSelectProject={openProject}
          onSelectPerson={openPerson}
        />
      </main>
    </div>
  );
}
