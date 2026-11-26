import { useEffect, useState } from "react";
import { fetchCorpusDefaultPath, fetchCorpusRun, startCorpusRun } from "../api.js";

export default function CorpusRunPanel() {
  const [path, setPath] = useState("/data/corpus");
  const [limit, setLimit] = useState(4);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [run, setRun] = useState(null);

  useEffect(() => {
    fetchCorpusDefaultPath()
      .then((data) => {
        if (data.corpus_path) setPath(data.corpus_path);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!run?.run_id) return undefined;
    if (["completed", "failed", "queued"].includes(run.status) && run.status !== "running") {
      // keep polling jobs indirectly by refreshing run once more after queue settles
    }
    const id = setInterval(() => {
      fetchCorpusRun(run.run_id)
        .then(setRun)
        .catch(() => {});
    }, 5000);
    return () => clearInterval(id);
  }, [run?.run_id, run?.status]);

  async function onRun(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const created = await startCorpusRun({
        corpus_path: path,
        limit: Number(limit) || 1,
        skip_existing: true,
      });
      setRun(created);
    } catch (err) {
      setError(err.message || "Failed to start corpus run");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="corpus-panel">
      <div>
        <p className="eyebrow">Corpus ingest</p>
        <h2>Run from folder</h2>
        <p className="corpus-help">
          Unzip the assignment corpus into this project as{" "}
          <code>data_center_candidate_transcripts_2025-11-04_to_2026-11-04/</code> (with{" "}
          <code>manifest.json</code>). Compose mounts it at <code>/data/corpus</code> in the API.
          Leave that path below unless you mounted a different folder.
        </p>
      </div>

      <form className="corpus-form" onSubmit={onRun}>
        <label>
          Corpus path (in API container)
          <input value={path} onChange={(e) => setPath(e.target.value)} required />
        </label>
        <label>
          Max new transcripts
          <input
            type="number"
            min={1}
            max={500}
            value={limit}
            onChange={(e) => setLimit(e.target.value)}
          />
        </label>
        <button type="submit" disabled={busy}>
          {busy ? "Queuing…" : "Run"}
        </button>
      </form>

      {error ? <p className="panel-status error">{error}</p> : null}

      {run ? (
        <div className="corpus-status">
          <p>
            <strong>Run</strong> {run.run_id}
          </p>
          <p>
            status <code>{run.status}</code> · queued {run.queued} · skipped existing{" "}
            {run.skipped_existing} · missing files {run.skipped_missing_file}
          </p>
          {run.detail ? <p className="panel-status">{run.detail}</p> : null}
          <p className="panel-status">
            The worker processes queued jobs one at a time. Watch{" "}
            <code>/api/jobs</code> or wait for location tiles to update.
          </p>
        </div>
      ) : null}
    </section>
  );
}
