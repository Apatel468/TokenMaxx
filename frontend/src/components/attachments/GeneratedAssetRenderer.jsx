/**
 * GeneratedAssetRenderer — inline chat attachments for documents and images.
 *
 * Composes FileAttachmentCard, DownloadButton, and PreviewModal.
 */
import { useCallback, useEffect, useState } from "react";
import {
  downloadArtifact,
  fetchAuthenticatedBlobUrl,
  fetchDocumentPreview,
  regenerateDocument,
  regenerateImage,
} from "../../api/generations.js";
import { formatBytes } from "../../utils/formatBytes.js";
import DownloadButton from "./DownloadButton.jsx";
import FileAttachmentCard from "./FileAttachmentCard.jsx";
import PreviewModal from "./PreviewModal.jsx";

function renderMarkdownBasic(text) {
  const lines = text.split("\n");
  return lines.map((line, i) => {
    if (line.startsWith("### ")) {
      return <h4 key={i}>{line.slice(4)}</h4>;
    }
    if (line.startsWith("## ")) {
      return <h3 key={i}>{line.slice(3)}</h3>;
    }
    if (line.startsWith("# ")) {
      return <h2 key={i}>{line.slice(2)}</h2>;
    }
    if (line.startsWith("- ") || line.startsWith("* ")) {
      return <li key={i}>{line.slice(2)}</li>;
    }
    if (!line.trim()) return <br key={i} />;
    return <p key={i}>{line}</p>;
  });
}

function CsvPreviewTable({ table }) {
  const headers = table?.headers || [];
  const rows = table?.rows || [];
  if (!headers.length && !rows.length) {
    return <p className="attachment-preview__empty">No CSV data to preview.</p>;
  }
  const cols = headers.length ? headers : rows[0] || [];
  const bodyRows = headers.length ? rows : rows.slice(1);
  return (
    <div className="attachment-preview__table-wrap">
      <table className="attachment-preview__table">
        <thead>
          <tr>
            {cols.map((h, i) => (
              <th key={i}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {bodyRows.map((row, ri) => (
            <tr key={ri}>
              {row.map((cell, ci) => (
                <td key={ci}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function InlinePreview({ preview, pdfUrl, imageUrl }) {
  if (!preview && !pdfUrl && !imageUrl) return null;

  if (imageUrl) {
    return (
      <div className="attachment-inline-preview">
        <img src={imageUrl} alt="Generated" className="attachment-inline-preview__image" />
      </div>
    );
  }

  if (pdfUrl) {
    return (
      <div className="attachment-inline-preview attachment-inline-preview--pdf">
        <iframe src={pdfUrl} title="PDF preview" className="attachment-inline-preview__pdf" />
      </div>
    );
  }

  if (!preview) return null;

  switch (preview.preview_type) {
    case "code":
    case "text":
      return (
        <pre className={`attachment-inline-preview__code language-${preview.language || "text"}`}>
          <code>{preview.content}</code>
        </pre>
      );
    case "markdown":
      return (
        <div className="attachment-inline-preview__markdown">
          {renderMarkdownBasic(preview.content || "")}
        </div>
      );
    case "csv":
      return <CsvPreviewTable table={preview.table} />;
    case "archive":
      return (
        <ul className="attachment-inline-preview__tree">
          {(preview.files || []).map((f) => (
            <li key={f.name || f.path}>{f.name || f.path}</li>
          ))}
        </ul>
      );
    default:
      return preview.message ? (
        <p className="attachment-preview__empty">{preview.message}</p>
      ) : null;
  }
}

function PreviewBody({ preview, pdfUrl, imageUrl }) {
  return <InlinePreview preview={preview} pdfUrl={pdfUrl} imageUrl={imageUrl} />;
}

function GeneratedAssetRenderer({ artifact, onRegenerated, defaultExpanded = true }) {
  const [previewOpen, setPreviewOpen] = useState(false);
  const [preview, setPreview] = useState(null);
  const [pdfUrl, setPdfUrl] = useState(null);
  const [imageUrl, setImageUrl] = useState(null);
  const [inlineExpanded, setInlineExpanded] = useState(defaultExpanded);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const isImage = artifact?.artifact_type === "image";
  const isDocument = artifact?.artifact_type === "document";

  const loadImagePreview = useCallback(async () => {
    if (!artifact?.preview_url) return;
    const url = await fetchAuthenticatedBlobUrl(artifact.preview_url);
    setImageUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return url;
    });
  }, [artifact?.preview_url]);

  useEffect(() => {
    if (!isImage) return undefined;
    let cancelled = false;
    loadImagePreview().catch((err) => {
      if (!cancelled) setError(err.message || "Could not load image.");
    });
    return () => {
      cancelled = true;
    };
  }, [isImage, loadImagePreview]);

  useEffect(
    () => () => {
      if (imageUrl) URL.revokeObjectURL(imageUrl);
      if (pdfUrl) URL.revokeObjectURL(pdfUrl);
    },
    [imageUrl, pdfUrl],
  );

  const loadDocumentPreview = useCallback(async () => {
    if (!artifact?.artifact_id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchDocumentPreview(artifact.artifact_id);
      setPreview(data);
      if (data.preview_type === "pdf" && artifact.download_url) {
        const url = await fetchAuthenticatedBlobUrl(artifact.download_url);
        setPdfUrl((prev) => {
          if (prev) URL.revokeObjectURL(prev);
          return url;
        });
      }
    } catch (err) {
      setError(err.message || "Preview unavailable.");
    } finally {
      setLoading(false);
    }
  }, [artifact?.artifact_id, artifact?.download_url]);

  useEffect(() => {
    if (!isDocument || !inlineExpanded) return;
    loadDocumentPreview();
  }, [isDocument, inlineExpanded, loadDocumentPreview]);

  const handleOpenPreview = async () => {
    if (isImage) {
      setPreviewOpen(true);
      return;
    }
    if (!preview) await loadDocumentPreview();
    setPreviewOpen(true);
  };

  const handleRegenerate = async () => {
    if (!artifact?.artifact_id) return;
    setLoading(true);
    setError(null);
    try {
      const fn = isImage ? regenerateImage : regenerateDocument;
      const result = await fn(artifact.artifact_id);
      onRegenerated?.(result);
    } catch (err) {
      setError(err.message || "Regeneration failed.");
    } finally {
      setLoading(false);
    }
  };

  if (!artifact) return null;

  const canPreview =
    isImage ||
    isDocument ||
    ["md", "py", "js", "ts", "json", "csv", "txt", "html", "pdf"].includes(
      (artifact.file_type || "").toLowerCase(),
    );

  return (
    <div className={`chat-attachment chat-attachment--${artifact.artifact_type}`}>
      <FileAttachmentCard
        fileName={artifact.file_name || (isImage ? "Generated image" : "Generated file")}
        fileType={isImage ? "png" : artifact.file_type}
        fileSize={artifact.file_size}
        createdAt={artifact.created_at}
        downloadUrl={artifact.download_url}
        showPreview={canPreview}
        onPreview={canPreview ? handleOpenPreview : null}
        subtitle={
          isImage
            ? [
                artifact.image_type?.replace(/_/g, " "),
                artifact.width > 0 ? `${artifact.width}×${artifact.height}px` : null,
                artifact.provider_used,
              ]
                .filter(Boolean)
                .join(" · ")
            : artifact.model_used
              ? `Model: ${artifact.model_used}`
              : null
        }
      />

      {isImage && imageUrl && inlineExpanded && (
        <InlinePreview imageUrl={imageUrl} />
      )}

      {isDocument && inlineExpanded && (
        <div className="chat-attachment__inline">
          {loading && !preview && (
            <p className="attachment-preview__empty">Loading preview…</p>
          )}
          <InlinePreview preview={preview} pdfUrl={pdfUrl} />
          {artifact.is_archive && artifact.files?.length > 1 && (
            <details className="chat-attachment__tree">
              <summary>{artifact.file_count} files in archive</summary>
              <ul>
                {artifact.files.map((f) => (
                  <li key={f.name || f.path}>
                    {f.name || f.path}
                    {f.size != null ? ` (${formatBytes(f.size)})` : ""}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}

      <div className="chat-attachment__footer">
        {isDocument && (
          <button
            type="button"
            className="attachment-btn attachment-btn--ghost"
            onClick={() => setInlineExpanded((v) => !v)}
          >
            {inlineExpanded ? "Collapse preview" : "Expand preview"}
          </button>
        )}
        <button
          type="button"
          className="attachment-btn attachment-btn--ghost"
          onClick={handleRegenerate}
          disabled={loading}
        >
          Regenerate
        </button>
      </div>

      <PreviewModal
        open={previewOpen}
        title={artifact.file_name || "Preview"}
        onClose={() => setPreviewOpen(false)}
      >
        <PreviewBody preview={preview} pdfUrl={pdfUrl} imageUrl={imageUrl} />
      </PreviewModal>

      {error && <p className="chat-attachment__error">{error}</p>}
    </div>
  );
}

export default GeneratedAssetRenderer;
