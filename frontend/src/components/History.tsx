import { useMemo, useState } from 'react';
import type { Analysis } from '../types';

interface Props {
  images: Analysis[];
  apiUrl: string;
  onSelect: (analysis: Analysis) => void;
  onDelete: (id: string) => void;
  activeId?: string;
}

export default function History({
  images,
  apiUrl,
  onSelect,
  onDelete,
  activeId,
}: Props) {
  const [query, setQuery] = useState('');

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return images;
    return images.filter((img) => {
      const haystack = [
        img.filename,
        img.description,
        img.sentiment,
        ...img.tags,
      ]
        .join(' ')
        .toLowerCase();
      return haystack.includes(q);
    });
  }, [images, query]);

  return (
    <div className="history">
      <h3>History</h3>

      {images.length > 0 && (
        <input
          type="search"
          className="history-search"
          placeholder="Search filename, tags, text…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      )}

      {images.length === 0 ? (
        <p className="history-empty">No images analyzed yet.</p>
      ) : filtered.length === 0 ? (
        <p className="history-empty">No results for “{query}”.</p>
      ) : (
        <ul className="history-list">
          {filtered.map((img) => (
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
                  {img.tags.slice(0, 3).join(' · ')}
                </div>
              </div>
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
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
