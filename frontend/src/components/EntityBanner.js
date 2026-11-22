// EntityBanner — the top banner shared by Sphere/Alliance/Project/Opening
// pages. Shows the entity's real uploaded image when present; otherwise a
// generated, on-brand placeholder (gradient + glyph) so every page looks
// finished even before a photo is set. When `onUpload` is provided (only on
// the respective management pages, or the opening's own page for its
// provider/manager), an overlaid "Set image…" button lets you attach one.
import React, { useEffect, useState, useRef } from 'react';
import PropTypes from 'prop-types';
import '../styles/EntityBanner.css';
import { AiTag } from './AiTag';
import AiPictureMaker from './AiPictureMaker';

const GLYPH = { sphere: '✦', alliance: '◈', project: '◻', opening: '◍' };

function EntityBanner({ kind, image, imageUrl, onUpload, asAdmin = false, isAi = false, aiSubject = null, children }) {
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState('');
    const [imgFailed, setImgFailed] = useState(false);
    // A new picture gets its chance after one failed to load.
    useEffect(() => setImgFailed(false), [imageUrl]);
    const fileInputRef = useRef(null);

    // Prefer an image URL (served lazily from the entity's /image endpoint) over
    // an inline base64 blob; either counts as "has an image" for the button label.
    const src = imageUrl || (image ? `data:image/jpeg;base64,${image}` : null);
    const hasImage = !!src && !imgFailed;

    const handleFileChange = async (e) => {
        const file = e.target.files?.[0];
        e.target.value = ''; // allow re-selecting the same file later
        if (!file || !onUpload) return;
        setUploading(true);
        setError('');
        try {
            await onUpload(file);
        } catch (err) {
            setError(err.response?.data?.message || 'Could not update the image.');
        } finally {
            setUploading(false);
        }
    };

    return (
        <>
        <header className={`ep-banner ep-banner--${kind}`}>
            {hasImage ? (
                <img src={src} alt="" className="ep-banner-img" onError={() => setImgFailed(true)} />
            ) : (
                <div className="ep-banner-fallback" aria-hidden="true">
                    <span className="ep-banner-glyph">{GLYPH[kind] || '◻'}</span>
                </div>
            )}
            <div className="ep-banner-scrim" />
            {hasImage && isAi && <AiTag className="ai-tag--banner" />}
            <div className="ep-banner-content">{children}</div>

            {onUpload && (
                <div className="ep-banner-upload">
                    <button
                        type="button"
                        className="ep-banner-upload-btn"
                        onClick={() => fileInputRef.current?.click()}
                        disabled={uploading}
                    >
                        {uploading ? 'Uploading…' : (hasImage ? '↻ Change image' : '+ Set image…')}
                        {asAdmin && !uploading && ' (admin)'}
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
        {onUpload && aiSubject && (
            <div className="ep-ai-panel">
                <AiPictureMaker purpose={kind} title={aiSubject.title} description={aiSubject.description} onUse={onUpload} />
            </div>
        )}
        </>
    );
}

EntityBanner.propTypes = {
    kind: PropTypes.oneOf(['sphere', 'alliance', 'project', 'opening']).isRequired,
    image: PropTypes.string,
    imageUrl: PropTypes.string,
    onUpload: PropTypes.func,
    // Uploading only through the platform-admin override: the button says so.
    asAdmin: PropTypes.bool,
    isAi: PropTypes.bool,
    // What an AI picture would be of; offered only with onUpload.
    aiSubject: PropTypes.shape({ title: PropTypes.string, description: PropTypes.string }),
    children: PropTypes.node,
};

export default EntityBanner;
