/**
 * DocumentsPage — upload and manage TXT/MD/PDF files for RAG in chat.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ACCEPTED_DOCUMENT_TYPES,
  deleteDocument,
  fetchDocuments,
  isAcceptedDocumentFile,
  uploadDocument,
} from "../api/documents.js";

function formatUploadedAt(isoString) {
  if (!isoString) return "—";
  try {
    const date = new Date(isoString);
    return date.toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return isoString;
  }
}

function fileTypeLabel(fileType) {
  if (!fileType) return "—";
  return fileType.toUpperCase();
}

function DocumentsPage() {
  const fileInputRef = useRef(null);
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const loadDocuments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const rows = await fetchDocuments();
      setDocuments(Array.isArray(rows) ? rows : []);
    } catch (err) {
      setError(err.message || "Could not load documents.");
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  useEffect(() => {
    if (!success) return undefined;
    const timer = setTimeout(() => setSuccess(null), 5000);
    return () => clearTimeout(timer);
  }, [success]);

  async function handleFileSelect(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    if (!isAcceptedDocumentFile(file)) {
      setError("Only TXT, MD, and PDF files are supported.");
      setSuccess(null);
      return;
    }

    setUploading(true);
    setError(null);
    setSuccess(null);
    try {
      await uploadDocument(file);
      setSuccess("Document indexed and ready for RAG.");
      await loadDocuments();
    } catch (err) {
      setError(err.message || "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(documentId, filename) {
    if (
      !window.confirm(
        `Delete "${filename}"? This removes it from RAG search.`,
      )
    ) {
      return;
    }

    setDeletingId(documentId);
    setError(null);
    setSuccess(null);
    try {
      await deleteDocument(documentId);
      setDocuments((prev) => prev.filter((doc) => doc.id !== documentId));
    } catch (err) {
      setError(err.message || "Could not delete document.");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="documents-page">
      <header className="documents-header">
        <div>
          <h2 className="documents-header__title">Documents</h2>
          <p className="documents-header__subtitle">
            Upload TXT, MD, or PDF files. TokenMaxx searches them during chat
            to ground answers in your content.
          </p>
        </div>
        <button
          type="button"
          className="documents-refresh"
          onClick={loadDocuments}
          disabled={loading || uploading}
        >
          Refresh
        </button>
      </header>

      <section className="documents-upload panel">
        <h3 className="documents-upload__title">Upload document</h3>
        <p className="panel__hint documents-upload__hint">
          Supported formats: TXT, MD, PDF (max 10 MB)
        </p>
        <div className="documents-upload__actions">
          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED_DOCUMENT_TYPES}
            className="documents-upload__input"
            onChange={handleFileSelect}
            disabled={uploading}
          />
          <button
            type="button"
            className="documents-upload__btn"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            {uploading ? "Uploading…" : "Choose file"}
          </button>
        </div>
      </section>

      {success && (
        <div className="alert alert--success" role="status">
          {success}
        </div>
      )}

      {error && (
        <div className="alert alert--error" role="alert">
          {error}
        </div>
      )}

      <section className="documents-list panel">
        <h3 className="documents-list__title">
          Your documents
          {!loading && (
            <span className="documents-list__count">{documents.length}</span>
          )}
        </h3>

        {loading ? (
          <div className="documents-loading">
            <div className="spinner" />
            <p>Loading documents…</p>
          </div>
        ) : documents.length === 0 ? (
          <p className="documents-empty">
            No documents yet. Upload a file to enable RAG in chat.
          </p>
        ) : (
          <div className="documents-table-wrap">
            <table className="documents-table">
              <thead>
                <tr>
                  <th>Filename</th>
                  <th>Type</th>
                  <th>Chunks</th>
                  <th>Uploaded</th>
                  <th aria-label="Actions" />
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => (
                  <tr key={doc.id}>
                    <td className="documents-table__filename" title={doc.filename}>
                      {doc.filename}
                    </td>
                    <td>
                      <span className="documents-type-badge">
                        {fileTypeLabel(doc.file_type)}
                      </span>
                    </td>
                    <td>{doc.chunk_count ?? 0}</td>
                    <td className="documents-table__date">
                      {formatUploadedAt(doc.created_at)}
                    </td>
                    <td className="documents-table__actions">
                      <button
                        type="button"
                        className="documents-delete-btn"
                        onClick={() => handleDelete(doc.id, doc.filename)}
                        disabled={deletingId === doc.id}
                      >
                        {deletingId === doc.id ? "Deleting…" : "Delete"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

export default DocumentsPage;
