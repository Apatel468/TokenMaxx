/** Format byte sizes for attachment cards. */
export function formatBytes(bytes) {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function fileTypeLabel(fileType) {
  if (!fileType) return "FILE";
  return fileType.toUpperCase();
}

export function fileIcon(fileType) {
  const ext = (fileType || "").toLowerCase();
  if (["png", "jpg", "jpeg", "webp", "svg"].includes(ext)) return "🖼️";
  if (ext === "pdf") return "📕";
  if (["docx", "doc"].includes(ext)) return "📘";
  if (["xlsx", "csv"].includes(ext)) return "📊";
  if (ext === "pptx") return "📙";
  if (["py", "js", "ts", "java", "cpp", "go", "rs"].includes(ext)) return "💻";
  if (ext === "zip") return "🗂️";
  if (ext === "md") return "📝";
  return "📄";
}
