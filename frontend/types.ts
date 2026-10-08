export type Rect = { x: number; y: number; width: number; height: number };
export type Attachment = {
  id: number;
  work_id: number;
  name: string;
  pages: number;
  sha256: string;
};
export type Work = {
  id: number;
  title: string;
  doi: string | null;
  authors: string[];
  year: number | null;
  publication_date: string | null;
  journal: string | null;
  publisher_url: string | null;
  citations: number | null;
  oa_locations: Location[];
  sources: string[];
  in_library: boolean;
  starred: boolean;
  status: string;
  notes: string;
  tags: string[];
  collections: number[];
  files: Attachment[];
  zotero?: {
    id: number;
    library_id: number;
    item_key: string;
    status: string;
  }[];
  external_attachments?: {
    id: number;
    managed_file_id: number | null;
    metadata_json: { filename?: string; contentType?: string };
  }[];
  zotero_notes?: { id: number; content: string }[];
};
export type Location = {
  url?: string;
  pdf_url?: string;
  license?: string;
  source?: string;
};
export type Annotation = {
  id: number;
  file_id: number;
  work_id: number;
  page: number;
  text: string;
  context: string;
  rects: Rect[];
  note: string;
  tags: string[];
  created_at: string;
};
export type Material = {
  id: number;
  kind: string;
  provenance: {
    title: string;
    doi: string | null;
    authors: string[];
    year: number | null;
    filename: string;
  };
  annotation: Annotation;
};
export type Job = {
  id: number;
  kind: string;
  state: string;
  progress: number;
  error: string | null;
  result: {
    work_ids?: number[];
    errors?: Record<string, string> | { file: string; error: string }[];
    source_counts?: Record<string, number>;
    imports?: unknown[];
  };
};
declare global {
  interface Window {
    desktop?: {
      config: () => Promise<{ base: string; token: string }>;
      pickPDFs: (folder?: boolean) => Promise<string[]>;
      openExternal: (url: string) => Promise<void>;
      fullscreen: (enabled: boolean) => Promise<boolean>;
      choosePath: (
        kind: "save-backup" | "open-backup",
      ) => Promise<string | undefined>;
      useDataRoot: (path: string) => Promise<void>;
    };
  }
}
