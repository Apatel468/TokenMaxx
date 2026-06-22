/**
 * PreviewModal — expanded preview for generated attachments.
 */
function PreviewModal({ open, title, onClose, children }) {
  if (!open) return null;

  return (
    <div className="preview-modal" role="dialog" aria-modal="true" aria-label={title}>
      <div className="preview-modal__backdrop" onClick={onClose} aria-hidden="true" />
      <div className="preview-modal__panel">
        <header className="preview-modal__header">
          <h3>{title}</h3>
          <button type="button" className="preview-modal__close" onClick={onClose}>
            ×
          </button>
        </header>
        <div className="preview-modal__body">{children}</div>
      </div>
    </div>
  );
}

export default PreviewModal;
