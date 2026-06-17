/**
 * Documents API — upload, list, and delete RAG source files.
 */
import { authFetch } from "./http.js";

const ACCEPTED_EXTENSIONS = [".txt", ".md", ".pdf"];

/** GET /documents — list uploaded documents for the current user */
export function fetchDocuments() {
  return authFetch("/documents");
}

/**
 * POST /documents/upload — multipart file upload.
 * @param {File} file
 */
export function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);
  return authFetch("/documents/upload", {
    method: "POST",
    body: formData,
  });
}

/** DELETE /documents/{id} */
export function deleteDocument(documentId) {
  return authFetch(`/documents/${documentId}`, {
    method: "DELETE",
  });
}

export function isAcceptedDocumentFile(file) {
  if (!file?.name) return false;
  const lower = file.name.toLowerCase();
  return ACCEPTED_EXTENSIONS.some((ext) => lower.endsWith(ext));
}

export const ACCEPTED_DOCUMENT_TYPES = "text/plain,.txt,.md,.pdf";
