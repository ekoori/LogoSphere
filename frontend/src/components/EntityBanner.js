// EntityBanner — the top banner shared by Sphere/Alliance/Project/Opening
// pages. Shows the entity's real uploaded image when present; otherwise a
// generated, on-brand placeholder (gradient + glyph) so every page looks
// finished even before a photo is set. When `onUpload` is provided (only on
// the respective management pages, or the opening's own page for its
// provider/manager), an overlaid "Set image…" button lets you attach one.
import React, { useState, useRef } from 'react';
import PropTypes from 'prop-types';
import '../styles/EntityBanner.css';

const GLYPH = { sphere: '✦', alliance: '◈', project: '◻', opening: '◍' };

function EntityBanner({ kind, image, onUpload, children }) {
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState('');
    const fileInputRef = useRef(null);

    const handleFileChange = async (e) => {
        const file = e.target.files?.[0];
        e.target.value = ''; // allow re-selecting the same file later
        if (!file || !onUpload) return;
        setUploading(true);
        setError('');
        try {
            await onUpload(file);
        } catch (err) {
            setError('Could not update the image.');
        } finally {
            setUploading(false);
        }
    };

    return (
        <header className={`ep-banner ep-banner--${kind}`}>
            {image ? (
                <img src={`data:image/jpeg;base64,${image}`} alt="" className="ep-banner-img" />
            ) : (
                <div className="ep-banner-fallback" aria-hidden="true">
                    <span className="ep-banner-glyph">{GLYPH[kind] || '◻'}</span>
                </div>
            )}
            <div className="ep-banner-scrim" />
            <div className="ep-banner-content">{children}</div>

            {onUpload && (
                <div className="ep-banner-upload">
                    <button
                        type="button"
                        className="ep-banner-upload-btn"
                        onClick={() => fileInputRef.current?.click()}
                        disabled={uploading}
                    >
                        {uploading ? 'Uploading…' : (image ? '↻ Change image' : '+ Set image…')}
                    </button>
                    <input
                        ref={fileInputRef}
                        type="file"
                        accept="image/*"
                        style={{ display: 'none' }}
                        onChange={handleFileChange}
                    />
                    {error && <span className="ep-banner-upload-error">{error}</span>}
                </div>
            )}
        </header>
    );
}

EntityBanner.propTypes = {
    kind: PropTypes.oneOf(['sphere', 'alliance', 'project', 'opening']).isRequired,
    image: PropTypes.string,
    onUpload: PropTypes.func,
    children: PropTypes.node,
};

export default EntityBanner;
