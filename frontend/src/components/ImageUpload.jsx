import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';

const LANGUAGES = [
  { value: 'en', label: 'English' },
  { value: 'fr', label: 'Français' },
  { value: 'es', label: 'Español' },
  { value: 'de', label: 'Deutsch' },
  { value: 'it', label: 'Italiano' },
  { value: 'pt', label: 'Português' },
  { value: 'ja', label: '日本語' },
  { value: 'zh', label: '中文' },
];

export default function ImageUpload({ onUpload, loading }) {
  const [detailLevel, setDetailLevel] = useState('medium');
  const [language, setLanguage] = useState('en');
  const [previews, setPreviews] = useState([]);

  const onDrop = useCallback(
    (acceptedFiles) => {
      if (acceptedFiles.length === 0) return;

      Promise.all(
        acceptedFiles.map(
          (file) =>
            new Promise((resolve) => {
              const reader = new FileReader();
              reader.onload = (e) => resolve(e.target.result);
              reader.readAsDataURL(file);
            })
        )
      ).then(setPreviews);

      onUpload(acceptedFiles, detailLevel, language);
    },
    [onUpload, detailLevel, language]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.jpeg', '.jpg', '.png', '.gif', '.webp'] },
    multiple: true,
    disabled: loading,
  });

  return (
    <div className="image-upload">
      <div className="upload-options">
        <div className="option">
          <label htmlFor="detail-level">Detail level</label>
          <select
            id="detail-level"
            value={detailLevel}
            onChange={(e) => setDetailLevel(e.target.value)}
            disabled={loading}
          >
            <option value="simple">Simple (quick)</option>
            <option value="medium">Medium (balanced)</option>
            <option value="detailed">Detailed (comprehensive)</option>
          </select>
        </div>

        <div className="option">
          <label htmlFor="language">Language</label>
          <select
            id="language"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            disabled={loading}
          >
            {LANGUAGES.map((l) => (
              <option key={l.value} value={l.value}>
                {l.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div
        {...getRootProps()}
        className={`dropzone ${isDragActive ? 'active' : ''} ${loading ? 'disabled' : ''}`}
      >
        <input {...getInputProps()} />
        {isDragActive ? (
          <p>Drop the image(s) here…</p>
        ) : (
          <>
            <p className="dropzone-primary">Drag &amp; drop image(s) here</p>
            <p className="dropzone-secondary">
              or click to select · one or several · JPEG, PNG, GIF, WebP
            </p>
          </>
        )}
      </div>

      {previews.length > 0 && (
        <div className={`preview ${previews.length > 1 ? 'preview-grid' : ''}`}>
          {previews.map((src, idx) => (
            <img key={idx} src={src} alt={`Preview ${idx + 1}`} />
          ))}
        </div>
      )}
    </div>
  );
}
