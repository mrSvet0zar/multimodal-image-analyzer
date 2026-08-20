import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import type { DetailLevel } from '../types';

interface Props {
  onUpload: (files: File[], detailLevel: DetailLevel, language: string) => void;
  loading: boolean;
}

const LANGUAGES: { value: string; label: string }[] = [
  { value: 'en', label: 'English' },
  { value: 'fr', label: 'Français' },
  { value: 'es', label: 'Español' },
  { value: 'de', label: 'Deutsch' },
  { value: 'it', label: 'Italiano' },
  { value: 'pt', label: 'Português' },
  { value: 'ja', label: '日本語' },
  { value: 'zh', label: '中文' },
];

interface Preview {
  url: string;
  isVideo: boolean;
}

export default function ImageUpload({ onUpload, loading }: Props) {
  const [detailLevel, setDetailLevel] = useState<DetailLevel>('medium');
  const [language, setLanguage] = useState('en');
  const [previews, setPreviews] = useState<Preview[]>([]);

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles.length === 0) return;

      setPreviews((prev) => {
        prev.forEach((p) => URL.revokeObjectURL(p.url));
        return acceptedFiles.map((file) => ({
          url: URL.createObjectURL(file),
          isVideo: file.type.startsWith('video/'),
        }));
      });

      onUpload(acceptedFiles, detailLevel, language);
    },
    [onUpload, detailLevel, language],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.jpeg', '.jpg', '.png', '.gif', '.webp'],
      'video/*': ['.mp4', '.webm', '.mov', '.avi'],
    },
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
            onChange={(e) => setDetailLevel(e.target.value as DetailLevel)}
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
          <p>Drop the image(s) or video here…</p>
        ) : (
          <>
            <p className="dropzone-primary">Drag &amp; drop image(s) or a video here</p>
            <p className="dropzone-secondary">
              or click to select · images (JPEG, PNG, GIF, WebP) or video (MP4, WebM, MOV)
            </p>
          </>
        )}
      </div>

      {previews.length > 0 && (
        <div className={`preview ${previews.length > 1 ? 'preview-grid' : ''}`}>
          {previews.map((p, idx) =>
            p.isVideo ? (
              <video key={idx} src={p.url} controls muted />
            ) : (
              <img key={idx} src={p.url} alt={`Preview ${idx + 1}`} />
            ),
          )}
        </div>
      )}
    </div>
  );
}
