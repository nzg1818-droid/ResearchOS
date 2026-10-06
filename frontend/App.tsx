import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  LinearProgress,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { api, openLink } from "./api";
import Reader from "./Reader";
import type { Attachment, Job, Location, Material, Work } from "./types";
const sections = [
  "Search",
  "Library",
  "Reader",
  "Knowledge",
  "Tasks",
  "Settings",
];
type Collection = { id: number; name: string };
export default function App() {
  const [view, setView] = useState("Search"),
    [query, setQuery] = useState("NiFe LDH alkaline water electrolysis"),
    [mode, setMode] = useState("keyword"),
    [start, setStart] = useState("2020-01-01"),
    [end, setEnd] = useState("2026-10-06"),
    [works, setWorks] = useState<Work[]>([]),
    [resultIds, setResultIds] = useState<number[] | null>(null),
    [jobs, setJobs] = useState<Job[]>([]),
    [activeJob, setActiveJob] = useState<number>(),
    [collections, setCollections] = useState<Collection[]>([]),
    [collection, setCollection] = useState(""),
    [newCollection, setNewCollection] = useState(""),
    [localQuery, setLocalQuery] = useState(""),
    [materials, setMaterials] = useState<Material[]>([]),
    [selected, setSelected] = useState<Work | null>(null),
    [reader, setReader] = useState<{
      file: Attachment;
      page: number;
      focusId?: number;
    }>(),
    [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [oa, setOA] = useState<Location[] | null>(null),
    [apiKey, setAPIKey] = useState(""),
    [dataDir, setDataDir] = useState(""),
    [oaBusy, setOABusy] = useState(false);
  const fail = (e: unknown) =>
    setError(e instanceof Error ? e.message : String(e));
  const refresh = useCallback(async () => {
    try {
      setCollections(await api<Collection[]>("/collections"));
      setMaterials(await api<Material[]>("/materials"));
      if (view === "Library")
        setWorks(
          await api<Work[]>(
            `/works?library=true&q=${encodeURIComponent(localQuery)}${collection ? "&collection=" + collection : ""}`,
          ),
        );
      else if (view === "Search" && resultIds !== null)
        setWorks(
          resultIds.length
            ? await api<Work[]>("/works?ids=" + resultIds.join(","))
            : [],
        );
    } catch (e) {
      fail(e);
    }
  }, [view, resultIds, collection, localQuery]);
  useEffect(() => {
    void refresh();
  }, [refresh]);
  useEffect(() => {
    api<{ data_dir: string }>("/health")
      .then((h) => setDataDir(h.data_dir))
      .catch(fail);
  }, []);
  useEffect(() => {
    let stopped = false;
    const poll = async () => {
      try {
        const all = await api<Job[]>("/jobs");
        if (stopped) return;
        setJobs(all);
        const job = all.find((j) => j.id === activeJob);
        if (job && !["queued", "running"].includes(job.state)) {
          setActiveJob(undefined);
          if (job.kind === "search") {
            setResultIds(job.result.work_ids || []);
            setView("Search");
          } else void refresh();
          if (job.error) setError(job.error);
          if (job.result.errors && Object.keys(job.result.errors).length)
            setError(JSON.stringify(job.result.errors));
          setMessage(`${job.kind}: ${job.state}`);
        }
      } catch (e) {
        if (!stopped) fail(e);
      }
    };
    void poll();
    const timer = setInterval(poll, 1000);
    return () => {
      stopped = true;
      clearInterval(timer);
    };
  }, [activeJob, refresh]);
  const search = async () => {
    setError("");
    setMessage("");
    try {
      const j = await api<{ job_id: number }>("/search", "POST", {
        query,
        mode,
        start: start || null,
        end: end || null,
      });
      setActiveJob(j.job_id);
    } catch (e) {
      fail(e);
    }
  };
  const patch = async (w: Work, values: Partial<Work>) => {
    try {
      const updated = await api<Work>(`/works/${w.id}`, "PATCH", values);
      setWorks((prev) => prev.map((x) => (x.id === w.id ? updated : x)));
      if (selected?.id === w.id) setSelected(updated);
    } catch (e) {
      fail(e);
    }
  };
  const importFiles = async (folder = false, work?: Work) => {
    try {
      if (!window.desktop)
        throw new Error("Use the Windows desktop app to choose local files.");
      const paths = await window.desktop.pickPDFs(folder);
      if (!paths.length) return;
      const j = await api<{ job_id: number }>("/imports", "POST", {
        paths,
        work_id: work?.id,
      });
      setActiveJob(j.job_id);
      setSelected(null);
      setView("Tasks");
    } catch (e) {
      fail(e);
    }
  };
  const discover = async (w: Work) => {
    setOABusy(true);
    setError("");
    try {
      const found = await api<{
        locations: Location[];
        errors: Record<string, string>;
      }>(`/works/${w.id}/oa`, "POST");
      setOA(found.locations);
      if (Object.keys(found.errors).length)
        setError(JSON.stringify(found.errors));
    } catch (e) {
      fail(e);
    } finally {
      setOABusy(false);
    }
  };
  const link = (url: string) => {
    void openLink(url).catch(fail);
  };
  const openFile = (file: Attachment, page = 1, focusId?: number) => {
    setReader({ file, page, focusId });
    setSelected(null);
    setView("Reader");
  };
  const backlink = async (m: Material) => {
    try {
      const w = await api<Work>(`/works/${m.annotation.work_id}`);
      const f = w.files.find((f) => f.id === m.annotation.file_id);
      if (!f) throw new Error("Source PDF is missing");
      openFile(f, m.annotation.page, m.annotation.id);
    } catch (e) {
      fail(e);
    }
  };
  const addCollection = async () => {
    if (!newCollection.trim()) return;
    try {
      await api("/collections", "POST", { name: newCollection });
      setNewCollection("");
      void refresh();
    } catch (e) {
      fail(e);
    }
  };
  const running = jobs.filter((j) => ["queued", "running"].includes(j.state));
  return (
    <div className="app-shell">
      <nav className="sidebar">
        <div className="brand">
          <span className="brand-symbol">R</span>
          <div>
            <strong>ResearchOS</strong>
            <small>YOUR RESEARCH, CONNECTED</small>
          </div>
        </div>
        <div className="workspace-label">WORKSPACE</div>
        {sections.map((s, i) => (
          <button
            key={s}
            className={`nav-item ${view === s ? "active" : ""}`}
            onClick={() => {
              setView(s);
              setError("");
            }}
          >
            <span className="nav-number">0{i + 1}</span>
            {s}
            {s === "Tasks" && running.length > 0 && (
              <Chip size="small" label={running.length} />
            )}
          </button>
        ))}
        <div className="sidebar-foot">
          <span className="status-dot" />
          Local-first workspace
          <small>Phase 1 · Evidence stays with its source</small>
        </div>
      </nav>
      <main>
        <header className="topbar">
          <span>
            Research workspace <span className="slash">/</span> {view}
          </span>
          <Chip variant="outlined" size="small" label="LOCAL LIBRARY" />
        </header>
        <div className="page-content">
          {error && (
            <Alert
              severity="error"
              onClose={() => setError("")}
              sx={{ mb: 2, wordBreak: "break-word" }}
            >
              {error}
            </Alert>
          )}
          {message && (
            <Alert
              severity="info"
              onClose={() => setMessage("")}
              sx={{ mb: 2 }}
            >
              {message}
            </Alert>
          )}
          {view === "Search" && (
            <>
              <div className="page-title">
                <div>
                  <Typography variant="overline">DISCOVER & CONNECT</Typography>
                  <Typography variant="h4">Start with a question.</Typography>
                  <Typography color="text.secondary">
                    Search OpenAlex and Crossref. Keep one canonical record for
                    every paper.
                  </Typography>
                </div>
                <Chip
                  label="2 live sources"
                  color="primary"
                  variant="outlined"
                />
              </div>
              <Card variant="outlined" className="search-card">
                <CardContent>
                  <Stack direction="row" gap={2}>
                    <TextField
                      select
                      label="Search by"
                      value={mode}
                      onChange={(e) => setMode(e.target.value)}
                      sx={{ minWidth: 160 }}
                    >
                      {[
                        ["keyword", "Keyword"],
                        ["title", "Exact title"],
                        ["author", "Author"],
                        ["doi", "DOI"],
                      ].map(([v, l]) => (
                        <MenuItem value={v} key={v}>
                          {l}
                        </MenuItem>
                      ))}
                    </TextField>
                    <TextField
                      label="Search literature"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") void search();
                      }}
                      fullWidth
                    />
                    <Button
                      variant="contained"
                      disabled={!!activeJob || !query.trim()}
                      onClick={search}
                      sx={{ minWidth: 110 }}
                    >
                      Search
                    </Button>
                  </Stack>
                  <Stack direction="row" gap={2} mt={2} alignItems="center">
                    <TextField
                      size="small"
                      type="date"
                      label="From date"
                      slotProps={{ inputLabel: { shrink: true } }}
                      value={start}
                      onChange={(e) => setStart(e.target.value)}
                    />
                    <TextField
                      size="small"
                      type="date"
                      label="To date"
                      slotProps={{ inputLabel: { shrink: true } }}
                      value={end}
                      onChange={(e) => setEnd(e.target.value)}
                    />
                    <Typography variant="body2" color="text.secondary">
                      Exact-title mode filters normalized titles. Clear dates to
                      search all years.
                    </Typography>
                  </Stack>
                </CardContent>
                {activeJob && <LinearProgress />}
              </Card>
              <Typography variant="h6" sx={{ my: 3 }}>
                {resultIds === null
                  ? "Your next reference starts here"
                  : `${works.length} canonical works`}
              </Typography>
              {resultIds === null && (
                <div className="empty-state">
                  <Typography variant="h5">
                    From discovery to evidence.
                  </Typography>
                  <Typography color="text.secondary">
                    Search → save to Library → attach a PDF → highlight →
                    revisit the source.
                  </Typography>
                </div>
              )}
            </>
          )}
          {view === "Library" && (
            <>
              <div className="page-title">
                <div>
                  <Typography variant="overline">
                    PERSONAL COLLECTION
                  </Typography>
                  <Typography variant="h4">Your reading, organized.</Typography>
                </div>
                <Stack direction="row" gap={1}>
                  <Button variant="outlined" onClick={() => importFiles(true)}>
                    Import folder
                  </Button>
                  <Button variant="contained" onClick={() => importFiles()}>
                    Import PDFs
                  </Button>
                </Stack>
              </div>
              <Stack direction="row" gap={2} sx={{ mb: 3 }}>
                <TextField
                  label="Search local titles and notes"
                  size="small"
                  value={localQuery}
                  onChange={(e) => setLocalQuery(e.target.value)}
                  sx={{ flex: 1 }}
                />
                <TextField
                  label="Collection"
                  select
                  size="small"
                  value={collection}
                  onChange={(e) => setCollection(e.target.value)}
                  sx={{ minWidth: 180 }}
                >
                  <MenuItem value="">All collections</MenuItem>
                  {collections.map((c) => (
                    <MenuItem key={c.id} value={c.id}>
                      {c.name}
                    </MenuItem>
                  ))}
                </TextField>
                <TextField
                  size="small"
                  label="New collection"
                  value={newCollection}
                  onChange={(e) => setNewCollection(e.target.value)}
                />
                <Button onClick={addCollection}>Create</Button>
              </Stack>
              {!works.length && (
                <div className="empty-state">
                  Save search results or import PDFs to start your library.
                </div>
              )}
            </>
          )}
          {["Search", "Library"].includes(view) &&
            works.map((w) => (
              <Card key={w.id} variant="outlined" className="work-card">
                <CardContent>
                  <div className="work-heading">
                    <div>
                      <Stack direction="row" gap={1} mb={1}>
                        {w.sources.map((s) => (
                          <Chip
                            key={s}
                            size="small"
                            variant="outlined"
                            label={s}
                          />
                        ))}
                        {w.oa_locations.length > 0 && (
                          <Chip
                            size="small"
                            color="success"
                            label="Open access"
                          />
                        )}
                        <Typography variant="body2" color="text.secondary">
                          {w.year || "Year unknown"} · {w.citations ?? "—"}{" "}
                          citations
                        </Typography>
                      </Stack>
                      <Typography
                        variant="h6"
                        component="button"
                        className="title-button"
                        onClick={() => setSelected(w)}
                      >
                        {w.title}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {w.authors.slice(0, 4).join(", ")}
                        {w.authors.length > 4 ? " et al." : ""}
                      </Typography>
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        sx={{ mt: 0.5 }}
                      >
                        {w.journal || "Source unknown"} {w.doi && `· ${w.doi}`}
                      </Typography>
                    </div>
                    <Button
                      aria-label={w.starred ? "Unstar paper" : "Star paper"}
                      onClick={() => patch(w, { starred: !w.starred })}
                    >
                      {w.starred ? "★" : "☆"}
                    </Button>
                  </div>
                  <Stack direction="row" flexWrap="wrap" gap={1} mt={2}>
                    <Button
                      size="small"
                      variant={w.in_library ? "outlined" : "contained"}
                      onClick={() => patch(w, { in_library: !w.in_library })}
                    >
                      {w.in_library ? "Remove from Library" : "Save to Library"}
                    </Button>
                    <Button
                      size="small"
                      disabled={!w.doi}
                      onClick={() => link("https://doi.org/" + w.doi)}
                    >
                      Open DOI
                    </Button>
                    <Button
                      size="small"
                      disabled={!w.publisher_url}
                      onClick={() => link(w.publisher_url!)}
                    >
                      Open publisher
                    </Button>
                    <Button
                      size="small"
                      disabled={oaBusy}
                      onClick={() => discover(w)}
                    >
                      Find OA copy
                    </Button>
                    <Button size="small" onClick={() => importFiles(false, w)}>
                      Attach PDF
                    </Button>
                    {w.files.map((f) => (
                      <Button
                        size="small"
                        key={f.id}
                        onClick={() => openFile(f)}
                      >
                        Read PDF · {f.pages}p
                      </Button>
                    ))}
                    <Button size="small" onClick={() => setSelected(w)}>
                      Details & notes
                    </Button>
                  </Stack>
                </CardContent>
              </Card>
            ))}
          {view === "Reader" &&
            (reader ? (
              <Reader
                key={`${reader.file.id}-${reader.page}-${reader.focusId}`}
                {...reader}
                file={reader.file}
                initialPage={reader.page}
                onSaved={() => {
                  void refresh();
                  setMessage("Annotation saved to local library");
                }}
              />
            ) : (
              <div className="empty-state">
                <Typography variant="h4">
                  Read with the source in view.
                </Typography>
                <Typography>
                  Attach a PDF from Search or Library, then choose Read PDF.
                </Typography>
                <Button onClick={() => setView("Library")}>Open Library</Button>
              </div>
            ))}
          {view === "Knowledge" && (
            <>
              <div className="page-title">
                <div>
                  <Typography variant="overline">
                    KNOWLEDGE / MATERIAL BANK
                  </Typography>
                  <Typography variant="h4">
                    Evidence you can return to.
                  </Typography>
                  <Typography color="text.secondary">
                    Every material opens its original PDF, page and highlight.
                  </Typography>
                </div>
                <Chip label={`${materials.length} materials`} />
              </div>
              {!materials.length && (
                <div className="empty-state">
                  Select text in the Reader and save it as evidence or writing
                  material.
                </div>
              )}
              <div className="material-grid">
                {materials.map((m) => (
                  <Card key={m.id} variant="outlined">
                    <CardContent>
                      <Chip size="small" label={m.kind} />
                      <blockquote>{m.annotation.text}</blockquote>
                      <Typography variant="body2">
                        {m.annotation.note}
                      </Typography>
                      <Divider sx={{ my: 2 }} />
                      <Typography variant="subtitle2">
                        {m.provenance.title}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {m.provenance.authors.slice(0, 2).join(", ")} ·{" "}
                        {m.provenance.year || "Unknown year"} · p.{" "}
                        {m.annotation.page}
                      </Typography>
                      <Typography variant="caption" display="block">
                        {m.provenance.doi}
                      </Typography>
                      <Stack direction="row" gap={1} mt={1}>
                        {m.annotation.tags.map((t) => (
                          <Chip size="small" key={t} label={t} />
                        ))}
                      </Stack>
                      <Button sx={{ mt: 2 }} onClick={() => backlink(m)}>
                        Open source · page {m.annotation.page}
                      </Button>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </>
          )}
          {view === "Tasks" && (
            <>
              <div className="page-title">
                <div>
                  <Typography variant="overline">
                    BACKGROUND ACTIVITY
                  </Typography>
                  <Typography variant="h4">
                    Every task, accounted for.
                  </Typography>
                </div>
              </div>
              {jobs.map((j) => (
                <Card variant="outlined" key={j.id} sx={{ mb: 2 }}>
                  <CardContent>
                    <Stack direction="row" justifyContent="space-between">
                      <Typography variant="h6">
                        #{j.id} · {j.kind}
                      </Typography>
                      <Chip
                        label={j.state}
                        color={
                          j.state === "completed"
                            ? "success"
                            : j.state === "failed"
                              ? "error"
                              : "default"
                        }
                      />
                    </Stack>
                    {["running", "queued"].includes(j.state) && (
                      <LinearProgress
                        variant={
                          j.kind === "import" ? "determinate" : "indeterminate"
                        }
                        value={j.progress}
                      />
                    )}
                    <Typography variant="body2">
                      {j.result.source_counts &&
                        Object.entries(j.result.source_counts)
                          .map(([s, c]) => `${s}: ${c}`)
                          .join(" · ")}
                      {j.result.imports &&
                        `${j.result.imports.length} PDFs processed`}
                    </Typography>
                    {j.error && <Alert severity="error">{j.error}</Alert>}
                    {j.result.errors &&
                      Object.keys(j.result.errors).length > 0 && (
                        <pre className="error-details">
                          {JSON.stringify(j.result.errors, null, 2)}
                        </pre>
                      )}
                    {!["running", "queued"].includes(j.state) && (
                      <Button
                        onClick={async () => {
                          try {
                            const r = await api<{ job_id: number }>(
                              `/jobs/${j.id}/retry`,
                              "POST",
                            );
                            setActiveJob(r.job_id);
                          } catch (e) {
                            fail(e);
                          }
                        }}
                      >
                        Retry task
                      </Button>
                    )}
                  </CardContent>
                </Card>
              ))}
              {!jobs.length && (
                <div className="empty-state">
                  Search and import activity will appear here.
                </div>
              )}
            </>
          )}
          {view === "Settings" && (
            <>
              <div className="page-title">
                <div>
                  <Typography variant="overline">LOCAL WORKSPACE</Typography>
                  <Typography variant="h4">Settings & storage</Typography>
                </div>
              </div>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="h6">OpenAlex access</Typography>
                  <Typography color="text.secondary" sx={{ mb: 2 }}>
                    Basic requests work without a key. An optional API key is
                    saved in Windows Credential Manager.
                  </Typography>
                  <TextField
                    label="OpenAlex API key"
                    type="password"
                    value={apiKey}
                    onChange={(e) => setAPIKey(e.target.value)}
                    fullWidth
                  />
                  <Button
                    sx={{ mt: 2 }}
                    variant="contained"
                    onClick={async () => {
                      try {
                        await api("/settings/openalex", "POST", {
                          key: apiKey,
                        });
                        setAPIKey("");
                        setMessage("API key saved in the OS credential store");
                      } catch (e) {
                        fail(e);
                      }
                    }}
                  >
                    Save key securely
                  </Button>
                  <Divider sx={{ my: 3 }} />
                  <Typography variant="h6">Library location</Typography>
                  <Typography sx={{ wordBreak: "break-all" }}>
                    {dataDir}
                  </Typography>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mt: 2 }}
                  >
                    Close ResearchOS before copying this folder for backup. It
                    contains the SQLite database, managed PDFs and debug logs.
                    Removing a paper from Library preserves source-linked
                    annotations.
                  </Typography>
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </main>
      <Dialog
        open={!!selected}
        onClose={() => setSelected(null)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>{selected?.title}</DialogTitle>
        <DialogContent>
          {selected && (
            <Stack gap={2} pt={1}>
              <Typography>{selected.doi}</Typography>
              <TextField
                select
                label="Reading status"
                value={selected.status}
                onChange={(e) =>
                  setSelected({ ...selected, status: e.target.value })
                }
              >
                {["unread", "reading", "completed"].map((s) => (
                  <MenuItem value={s} key={s}>
                    {s}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                label="Tags (comma separated)"
                value={selected.tags.join(",")}
                onChange={(e) =>
                  setSelected({ ...selected, tags: e.target.value.split(",") })
                }
              />
              <TextField
                multiline
                minRows={5}
                label="Paper notes"
                value={selected.notes}
                onChange={(e) =>
                  setSelected({ ...selected, notes: e.target.value })
                }
              />
              <Typography variant="subtitle2">Collections</Typography>
              <Stack direction="row" gap={1} flexWrap="wrap">
                {collections.map((c) => (
                  <Chip
                    key={c.id}
                    label={c.name}
                    color={
                      selected.collections.includes(c.id)
                        ? "primary"
                        : "default"
                    }
                    onClick={async () => {
                      try {
                        await api(
                          `/collections/${c.id}/works/${selected.id}`,
                          selected.collections.includes(c.id)
                            ? "DELETE"
                            : "POST",
                        );
                        setSelected(await api<Work>(`/works/${selected.id}`));
                      } catch (e) {
                        fail(e);
                      }
                    }}
                  />
                ))}
              </Stack>
              <Typography variant="subtitle2">Attachments</Typography>
              {selected.files.map((f) => (
                <Button key={f.id} onClick={() => openFile(f)}>
                  {f.name} · {f.pages} pages · {f.sha256.slice(0, 12)}
                </Button>
              ))}
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSelected(null)}>Close</Button>
          <Button
            variant="contained"
            onClick={async () => {
              if (selected) {
                await patch(selected, {
                  status: selected.status,
                  tags: selected.tags.map((t) => t.trim()).filter(Boolean),
                  notes: selected.notes,
                });
                setMessage("Library details saved");
              }
            }}
          >
            Save details
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog
        open={oa !== null}
        onClose={() => setOA(null)}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>Lawful open-access locations</DialogTitle>
        <DialogContent>
          {oa?.length ? (
            oa.map((l, i) => (
              <Box key={i} sx={{ mb: 2 }}>
                <Typography>
                  {l.source || "Open-access repository"} ·{" "}
                  {l.license || "License not supplied"}
                </Typography>
                {l.pdf_url && (
                  <Button onClick={() => link(l.pdf_url!)}>Open OA PDF</Button>
                )}
                {l.url && (
                  <Button onClick={() => link(l.url!)}>
                    Open landing page
                  </Button>
                )}
              </Box>
            ))
          ) : (
            <Typography>
              No verified OA location was returned. Use your own lawful browser
              access and attach a downloaded PDF.
            </Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOA(null)}>Close</Button>
        </DialogActions>
      </Dialog>
    </div>
  );
}
