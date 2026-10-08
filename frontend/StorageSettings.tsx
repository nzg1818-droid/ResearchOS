import { useEffect, useState } from "react";
import { Alert, Button, Stack, TextField, Typography } from "@mui/material";
import { api } from "./api";
export default function StorageSettings() {
  const [diagnostics, setDiagnostics] = useState<Record<string, unknown>>({}),
    [backupPath, setBackupPath] = useState(""),
    [restorePath, setRestorePath] = useState(""),
    [destination, setDestination] = useState(""),
    [restored, setRestored] = useState(""),
    [message, setMessage] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };
  const refresh = async () => setDiagnostics(await api("/diagnostics"));
  useEffect(() => {
    void run(refresh);
  }, []);
  return (
    <Stack gap={2} mt={3}>
      <Typography variant="h5">Storage & Backup</Typography>
      {message && <Alert>{message}</Alert>}
      {error && <Alert severity="error">{error}</Alert>}
      <TextField
        label="New backup ZIP path"
        value={backupPath}
        onChange={(e) => setBackupPath(e.target.value)}
      />
      <Stack direction="row">
        <Button
          onClick={() =>
            void run(async () => {
              const path = await window.desktop?.choosePath("save-backup");
              if (path) setBackupPath(path);
            })
          }
        >
          Choose backup file
        </Button>
        <Button
          disabled={busy || !backupPath}
          onClick={() =>
            void run(async () => {
              await api("/storage/backup", "POST", { path: backupPath });
              setMessage("Backup created and checksums verified.");
              await refresh();
            })
          }
        >
          Create verified backup
        </Button>
      </Stack>
      <TextField
        label="Backup ZIP to restore"
        value={restorePath}
        onChange={(e) => setRestorePath(e.target.value)}
      />
      <Button
        onClick={() =>
          void run(async () => {
            const path = await window.desktop?.choosePath("open-backup");
            if (path) setRestorePath(path);
          })
        }
      >
        Choose backup to restore
      </Button>
      <TextField
        label="New restore folder (must not exist)"
        value={destination}
        onChange={(e) => setDestination(e.target.value)}
      />
      <Stack direction="row">
        <Button
          disabled={busy || !restorePath}
          onClick={() =>
            void run(async () => {
              await api("/storage/validate", "POST", { path: restorePath });
              setMessage("Backup manifest and all checksums are valid.");
            })
          }
        >
          Validate backup
        </Button>
        <Button
          disabled={busy || !restorePath || !destination}
          onClick={() =>
            void run(async () => {
              const result = await api<{ data_dir: string }>(
                "/storage/restore",
                "POST",
                { path: restorePath, destination },
              );
              setRestored(result.data_dir);
              setMessage("Restored into " + result.data_dir);
            })
          }
        >
          Restore into new folder
        </Button>
      </Stack>
      {restored && (
        <Button
          disabled={!window.desktop}
          onClick={() =>
            void run(async () => {
              await window.desktop?.useDataRoot(restored);
            })
          }
        >
          Restart ResearchOS with restored library
        </Button>
      )}
      <Typography variant="h5">Library diagnostics</Typography>
      <Button disabled={busy} onClick={() => void run(refresh)}>
        Refresh integrity scan
      </Button>
      <table>
        <tbody>
          {Object.entries(diagnostics).map(([key, value]) => (
            <tr key={key}>
              <th>{key.replaceAll("_", " ")}</th>
              <td>{JSON.stringify(value)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <Typography variant="h6">Integrations / Zotero</Typography>
      <p>
        Zotero connection, OS-backed credentials and conflict resolution are
        available in the Zotero top-level destination.
      </p>
      <Typography variant="h6">Appearance</Typography>
      <p>
        Reader panel widths, visibility and zoom are remembered on this device.
        Zen mode always exits on restart.
      </p>
    </Stack>
  );
}
