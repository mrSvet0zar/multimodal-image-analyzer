import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';

export default function ImageUpload({ onUpload, loading }) {
  const [detailLevel, setDetailLevel] = useState('medium');
  const [preview, setPreview] = useState(null);

  const onDrop = useCallback(
    (acceptedFiles) => {
      if (acceptedFiles.length === 0) return;
      const file = acceptedFiles[0];

      const reader = new FileReader();
      reader.onload = (e) => setPreview(e.target.result);
      reader.readAsDataURL(file);

      onUpload(file, detailLevel);
    },
    [onUpload, detailLevel]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.jpeg', '.jpg', '.png', '.gif', '.webp'] },
    multiple: false,
    disabled: loading,
  });

  return (
    <div className="image-upload">
      <div className="detail-level-selector">
        <label htmlFor="detail-level">Analysis detail level:</label>
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

      <div
        {...getRootProps()}
        className={`dropzone ${isDragActive ? 'active' : ''} ${loading ? 'disabled' : ''}`}
      >
        <input {...getInputProps()} />
        {isDragActive ? (
          <p>Drop the image here…</p>
        ) : (
          <>
            <p className="dropzone-primary">Drag &amp; drop an image here</p>
            <p className="dropzone-secondary">or click to select · JPEG, PNG, GIF, WebP</p>
          </>
        )}
      </div>

      {preview && (
        <div className="preview">
          <img src={preview} alt="Preview of the uploaded image" />
        </div>
      )}
    </div>
  );
}
