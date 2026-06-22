/**
 * FileAttachmentCard — Slack/ChatGPT-style attachment chip in chat.
 */
import { formatBytes, fileIcon, fileTypeLabel } from "../../utils/formatBytes.js";
import DownloadButton from "./DownloadButton.jsx";

function FileAttachmentCard({
  fileName,
  fileType,
  fileSize,
  createdAt,
  downloadUrl,
  onPreview,
  showPreview = true,
  subtitle,
}) {
  return (
    <div className="file-attachment-card">
      <div className="file-attachment-card__icon" aria-hidden="true">
        {fileIcon(fileType)}
      </div>
      <div className="file-attachment-card__body">
        <div className="file-attachment-card__name" title={fileName}>
          {fileName}
        </div>
        <div className="file-attachment-card__meta">
          <span>{fileTypeLabel(fileType)}</span>
          <span>·</span>
          <span>{formatBytes(fileSize)}</span>
          {createdAt && (
            <>
              <span>·</span>
              <span>{createdAt}</span>
            </>
          )}
        </div>
        {subtitle && <div className="file-attachment-card__subtitle">{subtitle}</div>}
      </div>
      <div className="file-attachment-card__actions">
        {showPreview && onPreview && (
          <button type="button" className="attachment-btn attachment-btn--preview" onClick={onPreview}>
            Preview
          </button>
        )}
        <DownloadButton urlPath={downloadUrl} filename={fileName} />
      </div>
    </div>
  );
}

export default FileAttachmentCard;
