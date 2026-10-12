import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Checkbox,
  FormControlLabel,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { api } from "./api";
type Config = {
  id?: number;
  name: string;
  provider_type: string;
  endpoint: string;
  model: string;
  max_output_tokens: number;
  timeout: number;
  concurrency: number;
  enabled: boolean;
  is_default: boolean;
  default_level: string;
};
const empty: Config = {
  name: "",
  provider_type: "openai-compatible",
  endpoint: "https://api.openai.com/v1",
  model: "",
  max_output_tokens: 4000,
  timeout: 60,
  concurrency: 2,
  enabled: true,
  is_default: false,
  default_level: "abstract",
};
export default function AISettings() {
  const [providers, setProviders] = useState<Config[]>([]),
    [form, setForm] = useState<Config>(empty),
    [key, setKey] = useState(""),
    [clearKey, setClearKey] = useState(false),
    [message, setMessage] = useState("");
  const load = () =>
    api<Config[]>("/intelligence/providers").then(setProviders);
  useEffect(() => {
    void load().catch((e) => setMessage(String(e)));
  }, []);
  const action = async (f: () => Promise<unknown>) => {
    try {
      const r = await f();
      setMessage(JSON.stringify(r));
      await load();
    } catch (e) {
      setMessage(String(e));
    }
  };
  return (
    <Stack gap={2} my={3}>
      <Typography variant="h5">AI settings</Typography>
      <Alert severity="info">
        Cloud processing always asks for explicit consent per paper/batch.
        Nothing is analyzed automatically. Credentials use the OS keyring.
      </Alert>
      {providers.map((p) => (
        <Stack direction="row" key={p.id}>
          <Button
            onClick={() => {
              setForm(p);
              setKey("");
              setClearKey(false);
            }}
          >
            {p.name} / {p.model} ·{" "}
            {p.provider_type === "openai-compatible" ? "Cloud" : "Local"}
          </Button>
          <Button
            onClick={() =>
              void action(() =>
                api(`/intelligence/providers/${p.id}/test`, "POST"),
              )
            }
          >
            Test connection
          </Button>
        </Stack>
      ))}
      <Button
        onClick={() => {
          setForm(empty);
          setKey("");
        }}
      >
        Add provider
      </Button>
      {["name", "endpoint", "model"].map((k) => (
        <TextField
          key={k}
          label={`Provider ${k}`}
          value={form[k as keyof Config] || ""}
          onChange={(e) => setForm({ ...form, [k]: e.target.value })}
        />
      ))}
      <TextField
        select
        label="Provider type"
        value={form.provider_type}
        onChange={(e) =>
          setForm({
            ...form,
            provider_type: e.target.value,
            endpoint:
              e.target.value === "ollama"
                ? "http://127.0.0.1:11434"
                : e.target.value === "mock"
                  ? ""
                  : "https://api.openai.com/v1",
          })
        }
      >
        {["openai-compatible", "ollama", "mock"].map((t) => (
          <MenuItem key={t} value={t}>
            {t} · {t === "openai-compatible" ? "Cloud" : "Local"}
          </MenuItem>
        ))}
      </TextField>
      <TextField
        label="Provider API key"
        type="password"
        autoComplete="off"
        value={key}
        onChange={(e) => setKey(e.target.value)}
        helperText="Never stored in the browser; blank retains the current key."
      />
      <FormControlLabel
        control={
          <Checkbox
            checked={clearKey}
            onChange={(e) => setClearKey(e.target.checked)}
          />
        }
        label="Clear saved key"
      />
      {["max_output_tokens", "timeout", "concurrency"].map((k) => (
        <TextField
          key={k}
          type="number"
          label={k.replaceAll("_", " ")}
          value={form[k as keyof Config]}
          onChange={(e) => setForm({ ...form, [k]: Number(e.target.value) })}
        />
      ))}
      <TextField
        select
        label="Default extraction level"
        value={form.default_level}
        onChange={(e) => setForm({ ...form, default_level: e.target.value })}
      >
        {["metadata", "abstract", "full_text"].map((v) => (
          <MenuItem key={v} value={v}>
            {v}
          </MenuItem>
        ))}
      </TextField>
      <FormControlLabel
        control={
          <Checkbox
            checked={form.enabled}
            onChange={(e) => setForm({ ...form, enabled: e.target.checked })}
          />
        }
        label="Enabled"
      />
      <FormControlLabel
        control={
          <Checkbox
            checked={form.is_default}
            onChange={(e) => setForm({ ...form, is_default: e.target.checked })}
          />
        }
        label="Default provider"
      />
      <Button
        onClick={() =>
          void action(async () => {
            const { id, ...body } = form;
            const result = await api(
              `/intelligence/providers${id ? `/${id}` : ""}`,
              id ? "PUT" : "POST",
              {
                ...body,
                ...(key || clearKey ? { key: clearKey ? "" : key } : {}),
              },
            );
            setKey("");
            setClearKey(false);
            return result;
          })
        }
      >
        Save AI provider securely
      </Button>
      <Button
        onClick={() =>
          void action(() => api("/intelligence/cache/clear", "POST"))
        }
      >
        Clear cache eligibility (preserve extraction history)
      </Button>
      {message && <Alert severity="info">{message}</Alert>}
    </Stack>
  );
}
