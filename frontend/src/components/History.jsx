import React from 'react';

export default function History({ images, apiUrl, onSelect, onDelete, activeId }) {
  return (
    <div className="history">
      <h3>History</h3>
      {images.length === 0 ? (
        <p className="history-empty">No images analyzed yet.</p>
      ) : (
        <ul className="history-list">
          {images.map((img) => (
            <li
              key={img.id}
              className={`history-item ${img.id === activeId ? 'active' : ''}`}
              onClick={() => onSelect(img)}
            >
              <img
                className="history-thumb"
                src={`${apiUrl}${img.image_url}`}
                alt={img.filename}
              />
              <div className="history-meta">
                <div className="history-filename">{img.filename}</div>
                <div className="history-tags">
                  {(img.tags || []).slice(0, 3).join(' · ')}
                </div>
              </div>
              {onDelete && (
                <button
                  className="history-delete"
                  title="Delete this analysis"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(img.id);
                  }}
                >
                  ✕
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
