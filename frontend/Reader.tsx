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
import { readLayout, selectionContext, rotateRect } from "./reader-layout";
import type { Annotation, Attachment, Rect, Work, Material } from "./types";
pdfjs.GlobalWorkerOptions.workerSrc = worker;
export default function Reader({
  file,
  initialPage = 1,
  focusId,
  onSaved,
  onBack,
}: {
  file: Attachment;
  initialPage?: number;
  focusId?: number;
  onSaved: () => void;
  onBack?: () => void;
}) {
  const [activeFocus, setActiveFocus] = useState(focusId);
  const [layout, setLayout] = useState(readLayout),
    [zen, setZen] = useState(false),
    [toolbar, setToolbar] = useState(true);
  const [leftTab, setLeftTab] = useState("Outline"),
    [rightTab, setRightTab] = useState("Evidence");
  const [rotation, setRotation] = useState(0),
    [fit, setFit] = useState<"manual" | "width" | "page">("manual");
  const [find, setFind] = useState(""),
    [matches, setMatches] = useState<{ page: number; text: string }[]>([]),
    [matchIndex, setMatchIndex] = useState(0);
  const [outline, setOutline] = useState<{ title: string; page: number }[]>([]),
    [paper, setPaper] = useState<Work>(),
    [materials, setMaterials] = useState<Material[]>([]);
  const viewportEl = useRef<HTMLDivElement>(null),
    hideTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const reveal = () => {
    setToolbar(true);
    clearTimeout(hideTimer.current);
    if (zen) hideTimer.current = setTimeout(() => setToolbar(false), 2500);
  };
  const changeZen = async (enabled: boolean) => {
    try {
      if (window.desktop) await window.desktop.fullscreen(enabled);
      else if (enabled) await document.documentElement.requestFullscreen?.();
      else if (document.fullscreenElement) await document.exitFullscreen();
      setZen(enabled);
    } catch (e) {
      setError(String(e));
    }
  };
  useEffect(() => {
    localStorage.setItem("researchos.reader.layout", JSON.stringify(layout));
  }, [layout]);
  useEffect(() => {
    document.body.classList.toggle("reader-focus", layout.focus || zen);
    return () => document.body.classList.remove("reader-focus");
  }, [layout.focus, zen]);
  useEffect(() => {
    const command = (e: Event) => {
      const action = (e as CustomEvent).detail;
      setLayout((l) =>
        action === "left"
          ? { ...l, left: !l.left }
          : action === "right"
            ? { ...l, right: !l.right }
            : { ...l, focus: !l.focus },
      );
    };
    window.addEventListener("reader-command", command);
    return () => window.removeEventListener("reader-command", command);
  }, []);
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (zen) void changeZen(false);
        else if (layout.focus) setLayout((l) => ({ ...l, focus: false }));
      }
      if (e.key === "F11") {
        e.preventDefault();
        void changeZen(!zen);
      }
      if (e.key === "F6") {
        e.preventDefault();
        reveal();
      }
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "f") {
        e.preventDefault();
        setLayout((l) => ({ ...l, left: true, focus: false }));
        setLeftTab("Find in PDF");
      }
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [zen, layout.focus]);
  useEffect(
    () => () => {
      clearTimeout(hideTimer.current);
      void window.desktop?.fullscreen(false);
    },
    [],
  );
  useEffect(() => {
    api<Work>(`/works/${file.work_id}`)
      .then(setPaper)
      .catch((e) => setError(e.message));
    api<Material[]>("/materials")
      .then(setMaterials)
      .catch((e) => setError(e.message));
  }, [file.work_id]);
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
      const viewport = pdfPage.getViewport({ scale, rotation });
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
  }, [doc, page, scale, rotation]);
  useEffect(() => {
    if (!doc) return;
    let cancelled = false;
    (async () => {
      const entries = await doc.getOutline();
      const flattened: { title: string; page: number }[] = [];
      const walk = async (items: NonNullable<typeof entries>) => {
        for (const item of items) {
          const dest =
            typeof item.dest === "string"
              ? await doc.getDestination(item.dest)
              : item.dest;
          if (dest) {
            const first = dest[0];
            const index =
              typeof first === "number" ? first : await doc.getPageIndex(first);
            flattened.push({ title: item.title, page: index + 1 });
          }
          if (item.items.length) await walk(item.items);
        }
      };
      if (entries) await walk(entries);
      if (!cancelled) setOutline(flattened);
    })().catch((e) => setError(String(e)));
    return () => {
      cancelled = true;
    };
  }, [doc]);
  useEffect(() => {
    if (!doc || !find.trim()) {
      setMatches([]);
      return;
    }
    let cancelled = false;
    const timer = setTimeout(() => {
      void (async () => {
        const found: { page: number; text: string }[] = [];
        for (let p = 1; p <= doc.numPages; p++) {
          if (cancelled) return;
          const content = await (await doc.getPage(p)).getTextContent();
          const text = content.items
            .map((i) => ("str" in i ? i.str : ""))
            .join(" ");
          const lower = text.toLocaleLowerCase(),
            query = find.toLocaleLowerCase();
          let index = 0;
          while ((index = lower.indexOf(query, index)) >= 0) {
            found.push({
              page: p,
              text: text.slice(
                Math.max(0, index - 45),
                index + query.length + 65,
              ),
            });
            index += query.length;
          }
        }
        if (!cancelled) {
          setMatches(found);
          setMatchIndex(0);
          if (found.length) setPage(found[0].page);
        }
      })().catch((e) => setError(String(e)));
    }, 200);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [doc, find]);
  useEffect(() => {
    if (!doc || fit === "manual" || !viewportEl.current) return;
    let cancelled = false;
    const fitPage = async () => {
      const p = await doc.getPage(page);
      if (cancelled || !viewportEl.current) return;
      const v = p.getViewport({ scale: 1, rotation });
      const width = (viewportEl.current.clientWidth - 40) / v.width;
      const height = (viewportEl.current.clientHeight - 40) / v.height;
      setScale(
        Math.max(
          0.2,
          Math.min(4, fit === "width" ? width : Math.min(width, height)),
        ),
      );
    };
    const observer = new ResizeObserver(() => {
      void fitPage();
    });
    observer.observe(viewportEl.current);
    void fitPage();
    return () => {
      cancelled = true;
      observer.disconnect();
    };
  }, [doc, page, fit, rotation]);
  const jumpMatch = (delta: number) => {
    if (!matches.length) return;
    const i = (matchIndex + delta + matches.length) % matches.length;
    setMatchIndex(i);
    setPage(matches[i].page);
  };
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
    const prefix = range.cloneRange();
    prefix.selectNodeContents(textLayer.current);
    prefix.setEnd(range.startContainer, range.startOffset);
    const offset = prefix.toString().length;
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
      rects: rects.map((r) => rotateRect(r, 360 - rotation)),
      context: selectionContext(
        textLayer.current.textContent || "",
        selection.toString().trim(),
        offset,
      ),
    });
  };
  useEffect(() => {
    localStorage.setItem("researchos.pdf.zoom", String(scale));
  }, [scale]);
  useEffect(() => {
    if (!rendering && activeFocus)
      pageEl.current
        ?.querySelector(".highlight.focused")
        ?.scrollIntoView({ block: "center", inline: "center" });
  }, [rendering, activeFocus, annotations]);
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
    <div
      className={`reader-workspace ${zen ? "zen" : ""}`}
      onMouseMove={reveal}
    >
      <Stack
        direction="row"
        gap={2}
        alignItems="center"
        className={`reader-toolbar ${zen && !toolbar ? "auto-hidden" : ""}`}
      >
        <Button onClick={onBack}>Back</Button>
        <Typography
          title={paper?.title || file.name}
          noWrap
          sx={{ maxWidth: 200, flex: 1 }}
        >
          {paper?.title || file.name}
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
        <Button
          aria-label="Zoom out"
          onClick={() => {
            setFit("manual");
            setScale((s) => Math.max(0.25, s - 0.1));
          }}
        >
          −
        </Button>
        <span>{Math.round(scale * 100)}%</span>
        <Button
          aria-label="Zoom in"
          onClick={() => {
            setFit("manual");
            setScale((s) => Math.min(4, s + 0.1));
          }}
        >
          +
        </Button>
        <Button onClick={() => setFit("width")}>Fit width</Button>
        <Button onClick={() => setFit("page")}>Fit page</Button>
        <Button onClick={() => setRotation((r) => (r + 90) % 360)}>
          Rotate
        </Button>
        <Button
          onClick={() => {
            setLayout((l) => ({ ...l, left: true }));
            setLeftTab("Find in PDF");
          }}
        >
          Find
        </Button>
        <Chip
          size="small"
          label={selected ? "Text selected" : "Highlight ready"}
        />
        <Button
          aria-pressed={layout.left}
          onClick={() => setLayout((l) => ({ ...l, left: !l.left }))}
        >
          Left panel
        </Button>
        <Button
          aria-pressed={layout.right}
          onClick={() => setLayout((l) => ({ ...l, right: !l.right }))}
        >
          Right panel
        </Button>
        <Button
          aria-pressed={layout.focus}
          onClick={() => setLayout((l) => ({ ...l, focus: !l.focus }))}
        >
          {layout.focus ? "Exit Focus" : "Focus"}
        </Button>
        <Button onClick={() => void changeZen(!zen)}>
          {zen ? "Exit Zen (Esc)" : "Zen"}
        </Button>
      </Stack>
      {error && <Alert severity="error">{error}</Alert>}
      <div className="reader-layout">
        {layout.left && !layout.focus && !zen && (
          <aside
            className="reader-panel left-panel"
            style={{ width: layout.leftWidth }}
          >
            <label>
              Left panel width
              <input
                aria-label="Left panel width"
                type="range"
                min="220"
                max="420"
                value={layout.leftWidth}
                onChange={(e) =>
                  setLayout((l) => ({
                    ...l,
                    leftWidth: Number(e.target.value),
                  }))
                }
              />
            </label>
            <Stack direction="row" flexWrap="wrap">
              {["Outline", "Thumbnails", "Find in PDF"].map((t) => (
                <Button
                  key={t}
                  variant={leftTab === t ? "contained" : "text"}
                  onClick={() => setLeftTab(t)}
                >
                  {t}
                </Button>
              ))}
            </Stack>
            {leftTab === "Outline" &&
              (outline.length ? (
                outline.map((o, i) => (
                  <Button fullWidth key={i} onClick={() => setPage(o.page)}>
                    {o.title} · {o.page}
                  </Button>
                ))
              ) : (
                <p>No embedded outline</p>
              ))}
            {leftTab === "Thumbnails" &&
              doc &&
              Array.from({ length: doc.numPages }, (_, i) => (
                <Thumbnail
                  key={i}
                  doc={doc}
                  page={i + 1}
                  onClick={() => setPage(i + 1)}
                />
              ))}
            {leftTab === "Find in PDF" && (
              <>
                <TextField
                  label="Find in PDF"
                  value={find}
                  onChange={(e) => setFind(e.target.value)}
                />
                <p>
                  {matches.length ? matchIndex + 1 : 0} / {matches.length}{" "}
                  matches
                </p>
                <Button onClick={() => jumpMatch(-1)}>Previous match</Button>
                <Button onClick={() => jumpMatch(1)}>Next match</Button>
                {matches.map((m, i) => (
                  <Button
                    fullWidth
                    key={i}
                    onClick={() => {
                      setMatchIndex(i);
                      setPage(m.page);
                    }}
                  >
                    p.{m.page}: {m.text}
                  </Button>
                ))}
              </>
            )}
          </aside>
        )}
        <div className="pdf-scroll" ref={viewportEl}>
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
                a.rects.map((original, i) => {
                  const r = rotateRect(original, rotation);
                  return (
                    <div
                      key={`${a.id}-${i}`}
                      data-testid={`highlight-${a.id}`}
                      className={`highlight ${a.id === activeFocus ? "focused" : ""}`}
                      style={{
                        left: `${r.x * 100}%`,
                        top: `${r.y * 100}%`,
                        width: `${r.width * 100}%`,
                        height: `${r.height * 100}%`,
                      }}
                    />
                  );
                }),
              )}
          </div>
        </div>
        {layout.right && !layout.focus && !zen && (
          <aside
            className="evidence-panel reader-panel"
            style={{ width: layout.rightWidth }}
          >
            <label>
              Right panel width
              <input
                aria-label="Right panel width"
                type="range"
                min="240"
                max="440"
                value={layout.rightWidth}
                onChange={(e) =>
                  setLayout((l) => ({
                    ...l,
                    rightWidth: Number(e.target.value),
                  }))
                }
              />
            </label>
            <Stack direction="row" flexWrap="wrap">
              {["Evidence", "Notes", "Metadata", "Materials", "Zotero"].map(
                (t) => (
                  <Button
                    key={t}
                    variant={rightTab === t ? "contained" : "text"}
                    onClick={() => setRightTab(t)}
                  >
                    {t}
                  </Button>
                ),
              )}
            </Stack>
            {rightTab === "Metadata" && paper && (
              <>
                <h3>{paper.title}</h3>
                <p>{paper.authors.join(", ")}</p>
                <p>
                  {paper.journal} · {paper.year}
                </p>
                <p>{paper.doi}</p>
                <p>Sources: {paper.sources.join(", ")}</p>
                <p>
                  {paper.oa_locations.length
                    ? "Open access available"
                    : "No known OA copy"}
                </p>
                <p>{paper.files.length} managed PDFs</p>
              </>
            )}
            {rightTab === "Materials" &&
              materials
                .filter((m) => m.annotation.work_id === file.work_id)
                .map((m) => (
                  <Button
                    key={m.id}
                    fullWidth
                    onClick={() => {
                      setActiveFocus(m.annotation.id);
                      setPage(m.annotation.page);
                    }}
                  >
                    p.{m.annotation.page} · {m.annotation.text}
                  </Button>
                ))}
            {rightTab === "Zotero" && (
              <Stack gap={1}>
                {(paper?.zotero || []).map((link) => (
                  <div key={link.id}>
                    <p>
                      {link.item_key} · {link.status}
                    </p>
                    <Button
                      onClick={() =>
                        void api(`/zotero/${link.library_id}/sync`, "POST")
                          .then(() => api<Work>(`/works/${file.work_id}`))
                          .then(setPaper)
                          .catch((e) => setError(e.message))
                      }
                    >
                      Sync linked paper
                    </Button>
                  </div>
                ))}
                {!paper?.zotero?.length && <p>Not linked</p>}
                <Button
                  onClick={() => window.dispatchEvent(new Event("open-zotero"))}
                >
                  Open Zotero connection / push
                </Button>
              </Stack>
            )}
            {rightTab === "Notes" && paper && (
              <>
                <TextField
                  fullWidth
                  multiline
                  label="Paper note"
                  value={paper.notes}
                  onChange={(e) =>
                    setPaper({ ...paper, notes: e.target.value })
                  }
                />
                <TextField
                  label="Paper tags"
                  value={paper.tags.join(", ")}
                  onChange={(e) =>
                    setPaper({
                      ...paper,
                      tags: e.target.value.split(",").map((t) => t.trim()),
                    })
                  }
                />
                <Button
                  onClick={() => {
                    void api<Work>(`/works/${paper.id}`, "PATCH", {
                      notes: paper.notes,
                      tags: paper.tags,
                    })
                      .then(setPaper)
                      .catch((e) => setError(e.message));
                  }}
                >
                  Save paper note
                </Button>
                {annotations.map((a) => (
                  <Button fullWidth key={a.id} onClick={() => setPage(a.page)}>
                    p.{a.page} · {a.text} — {a.note}
                  </Button>
                ))}
              </>
            )}
            {rightTab === "Evidence" && (
              <>
                <Typography variant="overline">SOURCE & EVIDENCE</Typography>
                <Typography variant="h6">Keep the original in reach</Typography>
                <Typography color="text.secondary" variant="body2">
                  Select text on the page to highlight it or save a
                  source-linked material.
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
              </>
            )}
          </aside>
        )}
      </div>
    </div>
  );
}

function Thumbnail({
  doc,
  page,
  onClick,
}: {
  doc: pdfjs.PDFDocumentProxy;
  page: number;
  onClick: () => void;
}) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    let cancelled = false;
    let task: pdfjs.RenderTask | undefined;
    const observer = new IntersectionObserver((entries) => {
      if (!entries.some((e) => e.isIntersecting)) return;
      observer.disconnect();
      void doc
        .getPage(page)
        .then((p) => {
          if (cancelled || !ref.current) return;
          const viewport = p.getViewport({ scale: 0.2 });
          ref.current.width = viewport.width;
          ref.current.height = viewport.height;
          task = p.render({ canvas: ref.current, viewport });
          return task.promise;
        })
        .catch(() => {});
    });
    if (ref.current) observer.observe(ref.current);
    return () => {
      cancelled = true;
      observer.disconnect();
      task?.cancel();
    };
  }, [doc, page]);
  return (
    <button
      className="thumbnail"
      onClick={onClick}
      aria-label={`Go to page ${page}`}
    >
      <canvas ref={ref} />
      <span>Page {page}</span>
    </button>
  );
}
