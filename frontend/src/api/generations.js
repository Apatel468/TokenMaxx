/**
 * Generation API — downloads, previews, and regeneration (chat-integrated).
 */
import { API_BASE } from "./config.js";
import { authFetch, getToken } from "./http.js";

export function regenerateDocument(docId) {
  return authFetch(`/generations/documents/${docId}/regenerate`, { method: "POST" });
}

export function regenerateImage(imageId) {
  return authFetch(`/generations/images/${imageId}/regenerate`, { method: "POST" });
}

export function fetchDocumentPreview(docId) {
  return authFetch(`/generations/documents/${docId}/preview`);
}

async function authFetchBlob(urlPath) {
  const token = getToken();
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${API_BASE}${urlPath}`, { headers });
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }
  return response.blob();
}

/**
 * Download a generated file with auth and trigger browser save.
 */
export async function downloadArtifact(urlPath, filename) {
  const blob = await authFetchBlob(urlPath);
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename || "download";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
}

/**
 * Fetch authenticated blob URL for image/PDF preview.
 */
export async function fetchAuthenticatedBlobUrl(urlPath) {
  const blob = await authFetchBlob(urlPath);
  return URL.createObjectURL(blob);
}

/** @deprecated use fetchAuthenticatedBlobUrl */
export const fetchImagePreviewUrl = fetchAuthenticatedBlobUrl;
