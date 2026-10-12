import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Checkbox,
  Chip,
  FormControlLabel,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { api } from "./api";
export type EvidenceAnchor = {
  id: number;
  file_id: number | null;
  work_id: number;
  page: number | null;
  quote: string;
  field_path: string;
  bboxes: { page: number; rect: number[] }[];
};
type Provider = {
  id: number;
  name: string;
  model: string;
  cloud: boolean;
  enabled: boolean;
  is_default: boolean;
  default_level?: string;
};
type FieldValue = {
  value: string | number | null;
  origin: string;
  confidence: number;
  evidence: unknown[];
};
type Extraction = {
  id: number;
  effective: Record<string, unknown>;
  field_states: Record<string, { status: string; issues: string[] }>;
  anchors: EvidenceAnchor[];
  run: { extraction_level: string };
};
type Overview = {
  documents: {
    id: number;
    parse_status: string;
    page_count: number;
    chunks: number;
    characters: number;
    error?: string;
  }[];
  extractions: Extraction[];
  questions: {
    id: number;
    text: string;
    answers: { id: number; text: string; anchors: EvidenceAnchor[] }[];
  }[];
};
export function flatten(value: unknown, prefix = ""): [string, FieldValue][] {
  if (!value || typeof value !== "object") return [];
  if ("value" in value && "evidence" in value)
    return [[prefix, value as FieldValue]];
  return Object.entries(value).flatMap(([k, v]) =>
    flatten(v, prefix ? `${prefix}.${k}` : k),
  );
}
export async function downloadIntelligence(ids: number[], format: string) {
  const result = await api<{ content: string; mime: string; filename: string }>(
    "/intelligence/export",
    "POST",
    { work_ids: ids, format },
  );
  const url = URL.createObjectURL(
    new Blob([result.content], { type: result.mime }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = result.filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export function BatchIntelligence({
  workIds,
  onStarted,
}: {
  workIds: number[];
  onStarted?: (jobId: number) => void;
}) {
  const [providers, setProviders] = useState<Provider[]>([]),
    [providerId, setProviderId] = useState("");
  const [action, setAction] = useState("parse"),
    [consent, setConsent] = useState(false),
    [large, setLarge] = useState(false),
    [force, setForce] = useState(false),
    [error, setError] = useState(""),
    [message, setMessage] = useState("");
  const [sizes, setSizes] = useState<{
    pages: number;
    chunks: number;
    characters: number;
  } | null>(null);
  useEffect(() => {
    api<Provider[]>("/intelligence/providers")
      .then((p) => {
        setProviders(p);
        setProviderId(String(p.find((c) => c.is_default)?.id || ""));
        if (p.find((c) => c.is_default)?.default_level)
          setAction(p.find((c) => c.is_default)!.default_level!);
      })
      .catch((e) => setError(String(e)));
  }, []);
  const selected = providers.find((p) => String(p.id) === providerId);
  useEffect(() => {
    setConsent(false);
    setSizes(null);
  }, [providerId, workIds.join(","), action]);
  const preview = async () => {
    try {
      const data = await Promise.all(
        workIds.map((id) => api<Overview>(`/intelligence/works/${id}`)),
      );
      setSizes(
        data.reduce(
          (a, o) => {
            const d = o.documents[0];
            return {
              pages: a.pages + (d?.page_count || 0),
              chunks: a.chunks + (d?.chunks || 0),
              characters: a.characters + (d?.characters || 0),
            };
          },
          { pages: 0, chunks: 0, characters: 0 },
        ),
      );
    } catch (e) {
      setError(String(e));
    }
  };
  return (
    <Stack gap={1} my={1}>
      <Typography variant="subtitle2">
        Paper processing · {workIds.length} selected
      </Typography>
      <TextField
        select
        label="Processing action"
        value={action}
        onChange={(e) => setAction(e.target.value)}
      >
        {[
          ["parse", "Parse documents"],
          ["metadata", "Extract metadata (offline)"],
          ["abstract", "Extract abstracts"],
          ["full_text", "Extract full text"],
        ].map(([v, t]) => (
          <MenuItem key={v} value={v}>
            {t}
          </MenuItem>
        ))}
      </TextField>
      <TextField
        select
        label="AI provider"
        value={providerId}
        onChange={(e) => setProviderId(e.target.value)}
      >
        <MenuItem value="">No AI provider</MenuItem>
        {providers
          .filter((p) => p.enabled)
          .map((p) => (
            <MenuItem key={p.id} value={String(p.id)}>
              {p.name} · {p.model} · {p.cloud ? "Cloud" : "Local"}
            </MenuItem>
          ))}
      </TextField>
      <FormControlLabel
        control={
          <Checkbox
            checked={force}
            onChange={(e) => setForce(e.target.checked)}
          />
        }
        label="Force new extraction (otherwise use cached result)"
      />
      {selected?.cloud && !["parse", "metadata"].includes(action) && (
        <>
          <Button onClick={() => void preview()}>
            Preview cloud input size
          </Button>
          {sizes && (
            <Alert severity="info">
              {selected.name} / {selected.model} · Cloud · {sizes.pages} pages,{" "}
              {sizes.chunks} chunks, approximately {sizes.characters}{" "}
              characters. Parse first for a full-text estimate.
            </Alert>
          )}
          <FormControlLabel
            control={
              <Checkbox
                checked={consent}
                disabled={!sizes}
                onChange={(e) => setConsent(e.target.checked)}
              />
            }
            label={`I consent to send source text for these ${workIds.length} selected papers to this cloud provider for this run`}
          />
        </>
      )}
      {workIds.length > 50 && (
        <FormControlLabel
          control={
            <Checkbox
              checked={large}
              onChange={(e) => setLarge(e.target.checked)}
            />
          }
          label="Confirm a batch larger than 50 papers"
        />
      )}
      <Button
        disabled={
          !workIds.length ||
          (selected?.cloud &&
            !["parse", "metadata"].includes(action) &&
            !consent)
        }
        onClick={async () => {
          setError("");
          try {
            const r = await api<{ job_id: number }>(
              "/intelligence/batches",
              "POST",
              {
                work_ids: workIds,
                action,
                provider_id: providerId ? Number(providerId) : null,
                cloud_consent: consent,
                confirm_large_batch: large,
                force,
              },
            );
            setMessage(
              `Task ${r.job_id} started. Progress and pause/retry controls are in Tasks.`,
            );
            setConsent(false);
            onStarted?.(r.job_id);
          } catch (e) {
            setError(String(e));
          }
        }}
      >
        Start selected processing
      </Button>
      <Stack direction="row">
        <Button
          disabled={!workIds.length}
          onClick={() =>
            void downloadIntelligence(workIds, "json").catch((e) =>
              setError(String(e)),
            )
          }
        >
          Export intelligence JSON
        </Button>
        <Button
          disabled={!workIds.length}
          onClick={() =>
            void downloadIntelligence(workIds, "csv").catch((e) =>
              setError(String(e)),
            )
          }
        >
          Export intelligence CSV
        </Button>
      </Stack>
      {message && <Alert severity="info">{message}</Alert>}
      {error && <Alert severity="error">{error}</Alert>}
    </Stack>
  );
}
export function IntelligenceTask({ id }: { id: number }) {
  const [consent, setConsent] = useState(false),
    [error, setError] = useState("");
  return (
    <Stack>
      <FormControlLabel
        control={
          <Checkbox
            checked={consent}
            onChange={(e) => setConsent(e.target.checked)}
          />
        }
        label="Renew cloud consent for this task's selected papers (only required for cloud tasks)"
      />
      <Stack direction="row">
        {["pause", "cancel", "resume", "retry"].map((action) => (
          <Button
            key={action}
            onClick={() =>
              api(`/intelligence/jobs/${id}/control`, "POST", {
                action,
                cloud_consent: consent,
              })
                .then(() => setError(""))
                .catch((e) => setError(String(e)))
            }
          >
            {action}
          </Button>
        ))}
      </Stack>
      {error && <Alert severity="error">{error}</Alert>}
    </Stack>
  );
}
export default function Intelligence({
  workId,
  askOnly = false,
  onEvidence,
  onSaved,
}: {
  workId: number;
  askOnly?: boolean;
  onEvidence: (a: EvidenceAnchor) => void;
  onSaved?: () => void;
}) {
  const [data, setData] = useState<Overview>({
      documents: [],
      extractions: [],
      questions: [],
    }),
    [error, setError] = useState(""),
    [question, setQuestion] = useState("");
  const [providers, setProviders] = useState<Provider[]>([]),
    [providerId, setProviderId] = useState(""),
    [consent, setConsent] = useState(false);
  const [editing, setEditing] = useState<string | null>(null),
    [editValue, setEditValue] = useState(""),
    [note, setNote] = useState("");
  const load = () =>
    api<Overview>(`/intelligence/works/${workId}`).then(setData);
  useEffect(() => {
    void load().catch((e) => setError(String(e)));
    const timer = setInterval(() => void load().catch(() => {}), 2000);
    return () => clearInterval(timer);
  }, [workId]);
  useEffect(() => {
    api<Provider[]>("/intelligence/providers")
      .then(setProviders)
      .catch((e) => setError(String(e)));
  }, []);
  const run = async (fn: () => Promise<unknown>) => {
    try {
      setError("");
      await fn();
      await load();
      onSaved?.();
    } catch (e) {
      setError(String(e));
    }
  };
  const extraction = data.extractions[0];
  const doc = data.documents[0];
  const selected = providers.find((p) => String(p.id) === providerId);
  const source = (a: EvidenceAnchor) => (
    <Button
      key={a.id}
      disabled={!a.file_id || !a.page}
      onClick={() => onEvidence(a)}
    >
      Show evidence {a.page ? `p. ${a.page}` : "(abstract)"}
    </Button>
  );
  return (
    <Stack gap={1}>
      <Typography variant="h6">
        {askOnly ? "Ask Paper" : "Intelligence"}
      </Typography>
      <Chip label={doc?.parse_status || "Not parsed"} />
      {doc?.error && <Alert severity="warning">{doc.error}</Alert>}
      {error && <Alert severity="error">{error}</Alert>}
      {!askOnly && (
        <>
          <BatchIntelligence workIds={[workId]} onStarted={() => void load()} />
          {extraction && (
            <>
              <Alert severity="info">
                {extraction.run.extraction_level === "abstract"
                  ? "Abstract-only analysis"
                  : extraction.run.extraction_level}
              </Alert>
              {Object.entries(extraction.effective).map(([section, value]) => (
                <section key={section}>
                  <Typography variant="h6">
                    {section.replaceAll("_", " ")}
                  </Typography>
                  {flatten(value, section).map(([path, field]) => (
                    <Stack
                      key={path}
                      gap={0.5}
                      sx={{ borderBottom: "1px solid #ddd", py: 1 }}
                    >
                      <strong>
                        {path.split(".").slice(1).join(" ") ||
                          section.replaceAll("_", " ")}
                      </strong>
                      <span>
                        {field.value === null ? "Unknown" : String(field.value)}
                      </span>
                      <Stack direction="row" flexWrap="wrap">
                        <Chip
                          size="small"
                          label={
                            extraction.field_states[path]?.status ||
                            "Unverified"
                          }
                        />
                        <Chip size="small" label={field.origin} />
                        <span>Confidence: {field.confidence}</span>
                      </Stack>
                      {extraction.field_states[path]?.issues.map((issue) => (
                        <small key={issue}>{issue}</small>
                      ))}
                      {extraction.anchors
                        .filter((a) => a.field_path === path)
                        .map((a) => (
                          <div key={a.id}>
                            {source(a)}
                            <blockquote>{a.quote}</blockquote>
                          </div>
                        ))}
                      {field.value !== null && (
                        <Stack direction="row" flexWrap="wrap">
                          <Button
                            onClick={() =>
                              void run(() =>
                                api(
                                  `/intelligence/extractions/${extraction.id}/verify`,
                                  "POST",
                                  { field_path: path, action: "accept", note },
                                ),
                              )
                            }
                          >
                            Verify
                          </Button>
                          <Button
                            onClick={() => {
                              setEditing(path);
                              setEditValue(String(field.value));
                            }}
                          >
                            Edit
                          </Button>
                          <Button
                            onClick={() =>
                              void run(() =>
                                api(
                                  `/intelligence/extractions/${extraction.id}/verify`,
                                  "POST",
                                  { field_path: path, action: "reject", note },
                                ),
                              )
                            }
                          >
                            Reject
                          </Button>
                          <Button
                            disabled={
                              !["User verified", "User corrected"].includes(
                                extraction.field_states[path]?.status,
                              )
                            }
                            onClick={() =>
                              void run(() =>
                                api(
                                  `/intelligence/extractions/${extraction.id}/knowledge`,
                                  "POST",
                                  { field_path: path, action: "accept" },
                                ),
                              )
                            }
                          >
                            Save to Knowledge
                          </Button>
                        </Stack>
                      )}
                      {editing === path && (
                        <>
                          <TextField
                            label="Corrected value"
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                          />
                          <Button
                            onClick={() =>
                              void run(async () => {
                                await api(
                                  `/intelligence/extractions/${extraction.id}/verify`,
                                  "POST",
                                  {
                                    field_path: path,
                                    action: "edit",
                                    value:
                                      typeof field.value === "number"
                                        ? Number(editValue)
                                        : editValue,
                                    note,
                                  },
                                );
                                setEditing(null);
                              })
                            }
                          >
                            Save correction
                          </Button>
                        </>
                      )}
                    </Stack>
                  ))}
                  {Array.isArray(value) && !value.length && (
                    <p>Unknown / not reported</p>
                  )}
                </section>
              ))}
              <TextField
                label="Verification note"
                value={note}
                onChange={(e) => setNote(e.target.value)}
              />
            </>
          )}
        </>
      )}
      {askOnly && (
        <>
          <Typography>
            Only this paper. Offline source excerpts are available without AI.
          </Typography>
          <TextField
            select
            label="Answer provider"
            value={providerId}
            onChange={(e) => {
              setProviderId(e.target.value);
              setConsent(false);
            }}
          >
            <MenuItem value="">Offline source excerpts</MenuItem>
            {providers
              .filter((p) => p.enabled)
              .map((p) => (
                <MenuItem key={p.id} value={String(p.id)}>
                  {p.name} / {p.model} · {p.cloud ? "Cloud" : "Local"}
                </MenuItem>
              ))}
          </TextField>
          {selected?.cloud && (
            <>
              <Alert severity="info">
                {selected.name} / {selected.model}: up to 6 relevant chunks from{" "}
                {doc?.page_count || 0} pages; approximately{" "}
                {Math.min(doc?.characters || 0, 10800)} input characters.
              </Alert>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={consent}
                    onChange={(e) => setConsent(e.target.checked)}
                  />
                }
                label="I consent to send this question and retrieved paper text to the selected cloud provider"
              />
            </>
          )}
          <TextField
            multiline
            label="Question about this paper"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          />
          <Button
            disabled={!question.trim() || Boolean(selected?.cloud && !consent)}
            onClick={() =>
              void run(async () => {
                await api(`/intelligence/works/${workId}/ask`, "POST", {
                  question,
                  provider_id: providerId ? Number(providerId) : null,
                  cloud_consent: consent,
                });
                setConsent(false);
              })
            }
          >
            Ask this paper
          </Button>
          {data.questions.map((q) => (
            <section key={q.id}>
              <h4>{q.text}</h4>
              {q.answers.map((a) => (
                <div key={a.id}>
                  <p>{a.text}</p>
                  {a.anchors.map((anchor) => (
                    <details key={anchor.id}>
                      <summary>Evidence p. {anchor.page ?? "abstract"}</summary>
                      {source(anchor)}
                      <blockquote>{anchor.quote}</blockquote>
                    </details>
                  ))}
                  <Button
                    disabled={!a.anchors.length}
                    onClick={() =>
                      void run(() =>
                        api(`/intelligence/answers/${a.id}/knowledge`, "POST"),
                      )
                    }
                  >
                    Save answer to Knowledge
                  </Button>
                </div>
              ))}
            </section>
          ))}
        </>
      )}
    </Stack>
  );
}
