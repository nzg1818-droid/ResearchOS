import { useState } from "react";
import { Button, MenuItem, Stack, TextField, Alert } from "@mui/material";
import { api } from "./api";
export default function ExportButton({
  workIds,
  collectionId,
}: {
  workIds?: number[];
  collectionId?: number;
}) {
  const [format, setFormat] = useState("ris"),
    [error, setError] = useState("");
  const save = async () => {
    try {
      const result = await api<{
        content: string;
        mime: string;
        filename: string;
      }>("/export", "POST", {
        format,
        work_ids: workIds,
        collection_id: collectionId,
      });
      const url = URL.createObjectURL(
        new Blob([result.content], { type: result.mime }),
      );
      const a = document.createElement("a");
      a.href = url;
      a.download = result.filename;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      setError(String(e));
    }
  };
  return (
    <Stack direction="row" gap={1} alignItems="center">
      <TextField
        select
        size="small"
        label="Export format"
        value={format}
        onChange={(e) => setFormat(e.target.value)}
      >
        {["ris", "bibtex", "csl-json"].map((f) => (
          <MenuItem key={f} value={f}>
            {f.toUpperCase()}
          </MenuItem>
        ))}
      </TextField>
      <Button onClick={() => void save()}>
        Export {workIds ? "selected" : collectionId ? "collection" : "library"}
      </Button>
      {error && <Alert severity="error">{error}</Alert>}
    </Stack>
  );
}
