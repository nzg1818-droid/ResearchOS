import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Checkbox,
  FormControlLabel,
  MenuItem,
  Stack,
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import { api, openLink } from "./api";
type Connection = {
  id: number;
  mode: string;
  library_type: string;
  library_id: string;
  enabled: boolean;
  configured: boolean;
  endpoint: string;
};
type RemoteCollection = {
  key: string;
  data: { name: string; parentCollection?: string };
};
type State = {
  id: number;
  work_id: number;
  title: string;
  status: string;
  item_key: string;
  error?: string;
  remote_snapshot: { version: number };
  conflicts: Record<string, { local: unknown; remote: unknown; base: unknown }>;
};
type Mapping = {
  id: number;
  remote_name: string;
  remote_key: string;
  parent_key: string | null;
  collection_id: number;
  mirror: boolean;
};
export default function Zotero({
  initialWorkIds = [],
}: {
  initialWorkIds?: number[];
}) {
  const [tab, setTab] = useState("Connection"),
    [connections, setConnections] = useState<Connection[]>([]),
    [connection, setConnection] = useState("");
  const [mode, setMode] = useState("web"),
    [libraryType, setLibraryType] = useState("user"),
    [libraryId, setLibraryId] = useState(""),
    [endpoint, setEndpoint] = useState("http://127.0.0.1:23119/api"),
    [key, setKey] = useState(""),
    [enabled, setEnabled] = useState(true);
  const [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false),
    [collections, setCollections] = useState<RemoteCollection[]>([]),
    [selected, setSelected] = useState<string[]>([]);
  const [preview, setPreview] = useState<{
      summary: Record<string, number>;
      items: { key: string; title: string; action: string }[];
    } | null>(null),
    [states, setStates] = useState<State[]>([]),
    [maps, setMaps] = useState<Mapping[]>([]),
    [localCollections, setLocalCollections] = useState<
      { id: number; name: string }[]
    >([]);
  const [ids, setIds] = useState(initialWorkIds.join(",")),
    [destination, setDestination] = useState(""),
    [sendNote, setSendNote] = useState(false),
    [sendPdf, setSendPdf] = useState(false);
  const run = async (action: () => Promise<void>) => {
    setBusy(true);
    setError("");
    try {
      await action();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };
  const load = async () => {
    const result = await api<Connection[]>("/zotero/connections");
    setConnections(result);
    if (!connection && result.length) setConnection(String(result[0].id));
  };
  const loadStates = async () => {
    setStates(await api<State[]>(`/zotero/${connection}/states`));
    setMaps(await api<Mapping[]>(`/zotero/${connection}/mappings`));
    setLocalCollections(
      await api<{ id: number; name: string }[]>("/collections"),
    );
  };
  useEffect(() => {
    void run(load);
  }, []);
  useEffect(() => {
    setPreview(null);
    setCollections([]);
    setSelected([]);
    if (connection) void run(loadStates);
  }, [connection]);
  const current = connections.find((c) => String(c.id) === connection);
  return (
    <section>
      <Typography variant="h4">Zotero</Typography>
      <p>
        Connect a library, preview imports, and review changes before resolving
        conflicts.
      </p>
      {error && <Alert severity="error">{error}</Alert>}
      {message && <Alert severity="info">{message}</Alert>}
      <Stack direction="row" gap={2} my={2}>
        <TextField
          select
          label="Connection"
          value={connection}
          onChange={(e) => setConnection(e.target.value)}
          sx={{ minWidth: 300 }}
        >
          <MenuItem value="">Choose connection</MenuItem>
          {connections.map((c) => (
            <MenuItem key={c.id} value={String(c.id)}>
              {c.mode} · {c.library_type} {c.library_id}{" "}
              {c.enabled ? "" : "(disabled)"}
            </MenuItem>
          ))}
        </TextField>
        <Button
          disabled={!connection || busy}
          onClick={() =>
            void run(async () => {
              const result = await api<{ message: string }>(
                `/zotero/${connection}/test`,
                "POST",
              );
              setMessage(result.message);
            })
          }
        >
          Test connection
        </Button>
      </Stack>
      <Tabs value={tab} onChange={(_, v) => setTab(v)} variant="scrollable">
        {[
          "Connection",
          "Import",
          "Sync",
          "Conflicts",
          "Collection mappings",
        ].map((t) => (
          <Tab key={t} value={t} label={t} />
        ))}
      </Tabs>
      {tab === "Connection" && (
        <Stack gap={2} sx={{ maxWidth: 650, mt: 2 }}>
          <FormControlLabel
            control={
              <Checkbox
                checked={enabled}
                onChange={(e) => setEnabled(e.target.checked)}
              />
            }
            label="Enable Zotero"
          />
          <TextField
            select
            label="Mode"
            value={mode}
            onChange={(e) => setMode(e.target.value)}
          >
            <MenuItem value="local">Local API</MenuItem>
            <MenuItem value="web">Web API v3</MenuItem>
          </TextField>
          {mode === "local" && (
            <TextField
              label="Local endpoint"
              value={endpoint}
              onChange={(e) => setEndpoint(e.target.value)}
            />
          )}
          <TextField
            select
            label="Library type"
            value={libraryType}
            onChange={(e) => setLibraryType(e.target.value)}
          >
            <MenuItem value="user">User</MenuItem>
            <MenuItem value="group">Group</MenuItem>
          </TextField>
          <TextField
            label="Library ID"
            helperText={
              mode === "local"
                ? "Use 0 for the local personal library"
                : "Find your user ID in Zotero API key settings"
            }
            value={libraryId}
            onChange={(e) => setLibraryId(e.target.value)}
          />
          <TextField
            type="password"
            autoComplete="off"
            label={
              mode === "web" ? "Web API key" : "Local API key (if required)"
            }
            value={key}
            onChange={(e) => setKey(e.target.value)}
            helperText="Saved only in the OS credential store. Leave blank to retain an existing key."
          />
          <Button
            disabled={busy}
            variant="contained"
            onClick={() =>
              void run(async () => {
                const result = await api<Connection>(
                  "/zotero/connections",
                  "POST",
                  {
                    mode,
                    enabled,
                    library_type: libraryType,
                    library_id: libraryId || "0",
                    endpoint,
                    ...(key ? { key } : {}),
                  },
                );
                setKey("");
                setConnection(String(result.id));
                await load();
                setMessage("Connection saved. Test it before importing.");
              })
            }
          >
            Save connection securely
          </Button>
          <Button
            disabled={!connection || busy}
            onClick={() =>
              void run(async () => {
                const result = await api<{ message: string }>(
                  `/zotero/${connection}/clear-credentials`,
                  "POST",
                );
                setKey("");
                await load();
                setMessage(result.message);
              })
            }
          >
            Clear credentials and disable
          </Button>
          {current?.mode === "local" && (
            <Button
              disabled={busy}
              onClick={() =>
                void run(async () => {
                  await api(`/zotero/${connection}/authorize-local`, "POST");
                  setMessage("Authorization stored securely");
                  await load();
                })
              }
            >
              Request Local API write access
            </Button>
          )}
          <Button
            onClick={() =>
              void openLink("https://www.zotero.org/settings/keys")
            }
          >
            Manage or revoke keys at Zotero
          </Button>
          <p>
            Local API write support depends on your Zotero version. Unsupported
            operations report an error; Zotero databases are never edited
            directly.
          </p>
        </Stack>
      )}
      {tab === "Import" && (
        <Stack gap={2} mt={2}>
          <Button
            disabled={!connection || busy}
            onClick={() =>
              void run(async () =>
                setCollections(
                  await api<RemoteCollection[]>(
                    `/zotero/${connection}/collections`,
                  ),
                ),
              )
            }
          >
            Load remote collections
          </Button>
          <p>
            No selected collection means the entire connected library. Use a
            dedicated test collection for acceptance.
          </p>
          {collections.map((c) => (
            <FormControlLabel
              key={c.key}
              label={`${c.data.name}${c.data.parentCollection ? " (parent " + c.data.parentCollection + ")" : ""}`}
              control={
                <Checkbox
                  checked={selected.includes(c.key)}
                  onChange={(e) => {
                    setPreview(null);
                    setSelected(
                      e.target.checked
                        ? [...selected, c.key]
                        : selected.filter((k) => k !== c.key),
                    );
                  }}
                />
              }
            />
          ))}
          <Button
            disabled={!connection || busy}
            onClick={() =>
              void run(async () =>
                setPreview(
                  await api(`/zotero/${connection}/preview`, "POST", {
                    collections: selected,
                  }),
                ),
              )
            }
          >
            Preview import
          </Button>
          {preview && (
            <>
              <p>
                {Object.entries(preview.summary)
                  .map(([k, v]) => `${k}: ${v}`)
                  .join(" · ")}
              </p>
              {preview.items.slice(0, 100).map((i) => (
                <div key={i.key}>
                  {i.action} · {i.title}
                </div>
              ))}
              {preview.items.length > 100 && (
                <p>
                  Showing first 100 of {preview.items.length} preview items.
                </p>
              )}
              <Button
                disabled={busy}
                variant="contained"
                onClick={() =>
                  void run(async () => {
                    const result = await api(
                      `/zotero/${connection}/import`,
                      "POST",
                      { collections: selected },
                    );
                    setMessage("Import summary: " + JSON.stringify(result));
                    setPreview(null);
                    await loadStates();
                  })
                }
              >
                Import previewed scope
              </Button>
            </>
          )}
        </Stack>
      )}
      {tab === "Sync" && (
        <Stack gap={2} mt={2}>
          <Button
            disabled={!connection || busy}
            variant="contained"
            onClick={() =>
              void run(async () => {
                await api(`/zotero/${connection}/sync`, "POST");
                await loadStates();
                setMessage(
                  "Sync checked. Review Conflict and Error states below.",
                );
              })
            }
          >
            Synchronize linked works
          </Button>
          <TextField
            label="Work IDs to push (comma separated)"
            value={ids}
            onChange={(e) => setIds(e.target.value)}
          />
          <Button
            disabled={!connection || busy}
            onClick={() =>
              void run(async () =>
                setCollections(
                  await api<RemoteCollection[]>(
                    `/zotero/${connection}/collections`,
                  ),
                ),
              )
            }
          >
            Load destination collections
          </Button>
          <TextField
            select
            label="Destination collection"
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
          >
            <MenuItem value="">Library root</MenuItem>
            {collections.map((c) => (
              <MenuItem key={c.key} value={c.key}>
                {c.data.name}
              </MenuItem>
            ))}
          </TextField>
          <FormControlLabel
            control={
              <Checkbox
                checked={sendNote}
                onChange={(e) => setSendNote(e.target.checked)}
              />
            }
            label="Include named ResearchOS note"
          />
          <FormControlLabel
            control={
              <Checkbox
                checked={sendPdf}
                onChange={(e) => setSendPdf(e.target.checked)}
              />
            }
            label="Upload my managed PDFs (I have permission to share these files)"
          />
          <Button
            disabled={!connection || busy || !ids.trim()}
            onClick={() =>
              void run(async () => {
                const work_ids = ids.split(",").map((x) => Number(x.trim()));
                if (work_ids.some((x) => !Number.isInteger(x) || x < 1))
                  throw new Error("Enter valid Work IDs");
                await api(`/zotero/${connection}/push`, "POST", {
                  work_ids,
                  collection: destination || null,
                  note: sendNote,
                  pdf: sendPdf,
                });
                await loadStates();
                setMessage("Push finished. Review status below.");
              })
            }
          >
            Push selected works
          </Button>
          {states.map((s) => (
            <div key={s.id}>
              <strong>
                #{s.work_id} {s.title}
              </strong>{" "}
              · {s.status} · {s.item_key}
              {s.error && <Alert severity="warning">{s.error}</Alert>}
            </div>
          ))}
        </Stack>
      )}
      {tab === "Conflicts" && (
        <Stack gap={2} mt={2}>
          {states
            .filter((s) => s.status === "Conflict")
            .map((s) => (
              <Conflict
                key={s.id}
                state={s}
                busy={busy}
                resolve={(fields) =>
                  void run(async () => {
                    await api(`/zotero/conflicts/${s.id}/resolve`, "POST", {
                      version: s.remote_snapshot.version,
                      fields,
                    });
                    await loadStates();
                  })
                }
              />
            ))}
          {!states.some((s) => s.status === "Conflict") && (
            <p>No unresolved conflicts.</p>
          )}
        </Stack>
      )}
      {tab === "Collection mappings" && (
        <Stack gap={2} mt={2}>
          {maps.map((m) => (
            <Stack key={m.id} direction="row" gap={2} alignItems="center">
              <span>
                {m.remote_name} · {m.remote_key}{" "}
                {m.parent_key && `(parent ${m.parent_key})`}
              </span>
              <TextField
                select
                label="ResearchOS collection"
                value={m.collection_id}
                onChange={(e) =>
                  void run(async () => {
                    await api(`/zotero/mappings/${m.id}`, "PATCH", {
                      collection_id: Number(e.target.value),
                      mirror: m.mirror,
                    });
                    await loadStates();
                  })
                }
              >
                {localCollections.map((c) => (
                  <MenuItem key={c.id} value={c.id}>
                    {c.name}
                  </MenuItem>
                ))}
              </TextField>
              <FormControlLabel
                label="Mirror membership"
                control={
                  <Checkbox
                    checked={m.mirror}
                    onChange={(e) =>
                      void run(async () => {
                        await api(`/zotero/mappings/${m.id}`, "PATCH", {
                          collection_id: m.collection_id,
                          mirror: e.target.checked,
                        });
                        await loadStates();
                      })
                    }
                  />
                }
              />
            </Stack>
          ))}
          <p>
            Remote parent keys are preserved. ResearchOS collections remain
            flat; mirror applies to membership, not hierarchy or remote
            deletion.
          </p>
        </Stack>
      )}
    </section>
  );
}
function Conflict({
  state,
  busy,
  resolve,
}: {
  state: State;
  busy: boolean;
  resolve: (fields: Record<string, string>) => void;
}) {
  const [fields, setFields] = useState<Record<string, string>>({});
  const names = Object.keys(state.conflicts);
  return (
    <section className="conflict-card">
      <h3>{state.title}</h3>
      <Alert severity="warning">
        {state.error}. DOI changes require an explicit choice.
      </Alert>
      <Button
        onClick={() =>
          setFields(Object.fromEntries(names.map((n) => [n, "local"])))
        }
      >
        Keep ResearchOS
      </Button>
      <Button
        onClick={() =>
          setFields(Object.fromEntries(names.map((n) => [n, "remote"])))
        }
      >
        Keep Zotero
      </Button>
      <Button
        onClick={() =>
          setFields((f) => ({
            ...f,
            ...Object.fromEntries(
              names
                .filter((n) => ["tags", "collections"].includes(n))
                .map((n) => [n, "merge"]),
            ),
          }))
        }
      >
        Merge safe lists
      </Button>
      <table>
        <thead>
          <tr>
            <th>Field</th>
            <th>ResearchOS</th>
            <th>Zotero</th>
            <th>Resolution</th>
          </tr>
        </thead>
        <tbody>
          {names.map((name) => (
            <tr key={name}>
              <th>{name}</th>
              <td>{JSON.stringify(state.conflicts[name].local)}</td>
              <td>{JSON.stringify(state.conflicts[name].remote)}</td>
              <td>
                <select
                  aria-label={`Resolve ${name}`}
                  value={fields[name] || ""}
                  onChange={(e) =>
                    setFields({ ...fields, [name]: e.target.value })
                  }
                >
                  <option value="">Choose</option>
                  <option value="local">ResearchOS</option>
                  <option value="remote">Zotero</option>
                  {["tags", "collections"].includes(name) && (
                    <option value="merge">Merge</option>
                  )}
                </select>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <Button
        disabled={busy || names.some((n) => !fields[n])}
        onClick={() => resolve(fields)}
      >
        Apply field choices and sync
      </Button>
    </section>
  );
}
