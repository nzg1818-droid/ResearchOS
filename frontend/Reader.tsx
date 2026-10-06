import { useEffect, useRef, useState } from "react";
import {
  Alert,
  Button,
  Chip,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import * as pdfjs from "pdfjs-dist";
import worker from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import "pdfjs-dist/web/pdf_viewer.css";
import { api, config } from "./api";
import type { Annotation, Attachment, Rect } from "./types";
pdfjs.GlobalWorkerOptions.workerSrc = worker;
export default function Reader({
  file,
  initialPage = 1,
  focusId,
  onSaved,
}: {
  file: Attachment;
  initialPage?: number;
  focusId?: number;
  onSaved: () => void;
}) {
  const canvas = useRef<HTMLCanvasElement>(null),
    textLayer = useRef<HTMLDivElement>(null),
    pageEl = useRef<HTMLDivElement>(null);
  const [doc, setDoc] = useState<pdfjs.PDFDocumentProxy>(),
    [page, setPage] = useState(initialPage),
    [scale, setScale] = useState(
      () => Number(localStorage.getItem("researchos.pdf.zoom")) || 1,
    ),
    [annotations, setAnnotations] = useState<Annotation[]>([]),
    [selected, setSelected] = useState<{
      text: string;
      rects: Rect[];
      context: string;
    } | null>(null),
    [note, setNote] = useState(""),
    [tags, setTags] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [rendering, setRendering] = useState(false);
  useEffect(() => {
    let disposed = false;
    let task: pdfjs.PDFDocumentLoadingTask | undefined;
    setDoc(undefined);
    setPage(initialPage);
    setSelected(null);
    config()
      .then((c) => {
        if (disposed) return;
        task = pdfjs.getDocument({
          url: c.base + `/files/${file.id}/content`,
          httpHeaders: { "X-ResearchOS-Token": c.token },
        });
        return task.promise;
      })
      .then((d) => {
        if (!disposed && d) setDoc(d);
      })
      .catch((e) => {
        if (!disposed) setError(String(e));
      });
    api<Annotation[]>(`/files/${file.id}/annotations`)
      .then(setAnnotations)
      .catch((e) => setError(e.message));
    return () => {
      disposed = true;
      void task?.destroy();
    };
  }, [file.id, initialPage]);
  useEffect(() => {
    if (!doc) return;
    let cancelled = false;
    let render: pdfjs.RenderTask | undefined;
    let layer: pdfjs.TextLayer | undefined;
    setRendering(true);
    setSelected(null);
    (async () => {
      const pdfPage = await doc.getPage(page);
      if (cancelled) return;
      const viewport = pdfPage.getViewport({ scale });
      const cv = canvas.current!;
      cv.width = viewport.width;
      cv.height = viewport.height;
      const host = pageEl.current!;
      host.style.width = `${viewport.width}px`;
      host.style.height = `${viewport.height}px`;
      host.style.setProperty("--scale-factor", String(scale));
      host.style.setProperty("--total-scale-factor", String(scale));
      textLayer.current!.replaceChildren();
      render = pdfPage.render({ canvas: cv, viewport });
      await render.promise;
      if (cancelled) return;
      const content = await pdfPage.getTextContent();
      if (cancelled) return;
      layer = new pdfjs.TextLayer({
        textContentSource: content,
        container: textLayer.current!,
        viewport,
      });
      await layer.render();
      if (!cancelled) setRendering(false);
    })().catch((e) => {
      if (!cancelled) {
        setError(String(e));
        setRendering(false);
      }
    });
    return () => {
      cancelled = true;
      render?.cancel();
      layer?.cancel();
    };
  }, [doc, page, scale]);
  const select = () => {
    const selection = window.getSelection();
    if (
      !selection ||
      selection.isCollapsed ||
      !selection.rangeCount ||
      !pageEl.current
    )
      return;
    const range = selection.getRangeAt(0);
    if (!textLayer.current?.contains(range.commonAncestorContainer)) return;
    const bounds = pageEl.current.getBoundingClientRect();
    const rects = Array.from(range.getClientRects())
      .filter((r) => r.width > 0 && r.height > 0)
      .map((r) => ({
        x: Math.max(0, (r.left - bounds.left) / bounds.width),
        y: Math.max(0, (r.top - bounds.top) / bounds.height),
        width: Math.min(1, r.width / bounds.width),
        height: Math.min(1, r.height / bounds.height),
      }));
    setSelected({
      text: selection.toString().trim(),
      rects,
      context: textLayer.current.innerText.slice(0, 12000),
    });
  };
  useEffect(() => {
    localStorage.setItem("researchos.pdf.zoom", String(scale));
  }, [scale]);
  useEffect(() => {
    if (!rendering && focusId)
      pageEl.current
        ?.querySelector(".highlight.focused")
        ?.scrollIntoView({ block: "center", inline: "center" });
  }, [rendering, focusId, annotations]);
  const save = async (kind: string) => {
    if (!selected) return;
    setBusy(true);
    try {
      const annotation = await api<Annotation>("/annotations", "POST", {
        file_id: file.id,
        page,
        ...selected,
        note,
        tags: tags
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
        kind,
      });
      setAnnotations([...annotations, annotation]);
      setSelected(null);
      setNote("");
      onSaved();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div>
      <Stack
        direction="row"
        gap={2}
        alignItems="center"
        className="reader-toolbar"
      >
        <Typography variant="h6" sx={{ flex: 1 }}>
          {file.name}
        </Typography>
        <Button
          disabled={page <= 1 || rendering}
          onClick={() => setPage(page - 1)}
        >
          Previous
        </Button>
        <TextField
          size="small"
          label="Page"
          type="number"
          value={page}
          onChange={(e) =>
            setPage(
              Math.min(
                doc?.numPages || file.pages,
                Math.max(1, Number(e.target.value) || 1),
              ),
            )
          }
          sx={{ width: 90 }}
        />
        <Typography>/ {doc?.numPages || file.pages}</Typography>
        <Button
          disabled={page >= (doc?.numPages || file.pages) || rendering}
          onClick={() => setPage(page + 1)}
        >
          Next
        </Button>
        <TextField
          select
          size="small"
          label="Zoom"
          value={scale}
          onChange={(e) => setScale(Number(e.target.value))}
        >
          {[0.75, 1, 1.25, 1.5, 2].map((s) => (
            <MenuItem key={s} value={s}>
              {s * 100}%
            </MenuItem>
          ))}
        </TextField>
      </Stack>
      {error && <Alert severity="error">{error}</Alert>}
      <div className="reader-layout">
        <div className="pdf-scroll">
          <div
            ref={pageEl}
            className="pdf-page"
            onMouseUp={select}
            data-testid="pdf-page"
            data-page={page}
            data-ready={!rendering && !!doc}
          >
            <canvas ref={canvas} />
            <div ref={textLayer} className="textLayer" />
            {annotations
              .filter((a) => a.page === page)
              .flatMap((a) =>
                a.rects.map((r, i) => (
                  <div
                    key={`${a.id}-${i}`}
                    data-testid={`highlight-${a.id}`}
                    className={`highlight ${a.id === focusId ? "focused" : ""}`}
                    style={{
                      left: `${r.x * 100}%`,
                      top: `${r.y * 100}%`,
                      width: `${r.width * 100}%`,
                      height: `${r.height * 100}%`,
                    }}
                  />
                )),
              )}
          </div>
        </div>
        <aside className="evidence-panel">
          <Typography variant="overline">SOURCE & EVIDENCE</Typography>
          <Typography variant="h6">Keep the original in reach</Typography>
          <Typography color="text.secondary" variant="body2">
            Select text on the page to highlight it or save a source-linked
            material.
          </Typography>
          {selected && (
            <>
              <blockquote>{selected.text}</blockquote>
              <TextField
                fullWidth
                multiline
                minRows={3}
                label="Annotation note"
                value={note}
                onChange={(e) => setNote(e.target.value)}
              />
              <TextField
                fullWidth
                label="Annotation tags"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                sx={{ my: 2 }}
              />
              <Stack gap={1}>
                <Button
                  disabled={busy}
                  variant="outlined"
                  onClick={() => save("highlight")}
                >
                  Save highlight
                </Button>
                <Button
                  disabled={busy}
                  variant="contained"
                  onClick={() => save("evidence")}
                >
                  Save as evidence
                </Button>
                <Button disabled={busy} onClick={() => save("writing")}>
                  Save as writing material
                </Button>
              </Stack>
            </>
          )}
          <Typography variant="overline" sx={{ display: "block", mt: 3 }}>
            ON THIS PAGE
          </Typography>
          {annotations
            .filter((a) => a.page === page)
            .map((a) => (
              <div className="annotation-card" key={a.id}>
                <Typography variant="body2">{a.text}</Typography>
                <Typography color="text.secondary" variant="body2">
                  {a.note}
                </Typography>
                {a.tags.map((t) => (
                  <Chip key={t} size="small" label={t} />
                ))}
              </div>
            ))}
        </aside>
      </div>
    </div>
  );
}
