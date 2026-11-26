async function getJson(path) {
  const response = await fetch(path);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed (${response.status})`);
  }
  return response.json();
}

export function fetchDefaultMonth() {
  return getJson("/api/locations/default-month");
}

export function fetchSentiment(month) {
  return getJson(`/api/locations/sentiment?month=${encodeURIComponent(month)}`);
}

export function fetchLocationStatements(locationId, month) {
  return getJson(
    `/api/locations/${locationId}/statements?month=${encodeURIComponent(month)}`
  );
}

export function fetchLocationProjects(locationId, month) {
  return getJson(
    `/api/locations/${locationId}/projects?month=${encodeURIComponent(month)}`
  );
}

export function fetchProject(projectId) {
  return getJson(`/api/projects/${projectId}`);
}

export function fetchProjectFindings(projectId) {
  return getJson(`/api/projects/${projectId}/findings`);
}

export function fetchProjectStatements(projectId) {
  return getJson(`/api/projects/${projectId}/statements`);
}

export function fetchPerson(personId) {
  return getJson(`/api/people/${personId}`);
}

export function fetchPersonStatements(personId) {
  return getJson(`/api/people/${personId}/statements`);
}

export function fetchCorpusDefaultPath() {
  return getJson("/api/corpus/default-path");
}

export function startCorpusRun(body) {
  return fetch("/api/corpus/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then(async (response) => {
    if (!response.ok) {
      const detail = await response.text();
      throw new Error(detail || `Request failed (${response.status})`);
    }
    return response.json();
  });
}

export function fetchCorpusRun(runId) {
  return getJson(`/api/corpus/runs/${runId}`);
}
