/**
 * DownloadButton — authenticated file download trigger.
 */
import { useState } from "react";
import { downloadArtifact } from "../../api/generations.js";

function DownloadButton({ urlPath, filename, label = "Download", className = "" }) {
  const [loading, setLoading] = useState(false);

  async function handleClick() {
    if (!urlPath || loading) return;
    setLoading(true);
    try {
      await downloadArtifact(urlPath, filename);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <button
      type="button"
      className={`attachment-btn attachment-btn--download ${className}`.trim()}
      onClick={handleClick}
      disabled={loading || !urlPath}
    >
      {loading ? "Downloading…" : label}
    </button>
  );
}

export default DownloadButton;
