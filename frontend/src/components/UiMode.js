// Switching between Simple and Advanced, and saying where the rest went.
import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { useLogin } from '../App';
import { ADVANCED, SIMPLE } from '../utils/modes';

/** A button that switches to the other mode, and says so if that didn't save. */
export function ModeSwitch({ className = '', label, onDone }) {
    const { uiMode, changeUiMode } = useLogin();
    const [busy, setBusy] = useState(false);
    const [problem, setProblem] = useState(false);
    const next = uiMode === SIMPLE ? ADVANCED : SIMPLE;

    const change = async () => {
        if (busy) return;
        setBusy(true);
        setProblem(false);
        const saved = await changeUiMode(next);
        setBusy(false);
        if (!saved) setProblem(true);
        else if (onDone) onDone();
    };

    return (
        <>
            <button type="button" className={className} onClick={change} disabled={busy}>
                {label || (next === SIMPLE ? 'Switch to Simple' : 'Switch to Advanced')}
            </button>
            {problem && <span className="mode-problem" role="alert">That didn&rsquo;t save. Try again.</span>}
        </>
    );
}

ModeSwitch.propTypes = { className: PropTypes.string, label: PropTypes.string, onDone: PropTypes.func };

/** Where Simple leaves options out of a form. */
export function MoreInAdvanced({ what }) {
    const { uiMode, isLoggedIn } = useLogin();
    if (!isLoggedIn || uiMode !== SIMPLE) return null;
    return (
        <p className="mode-more">
            {what} in Advanced. <ModeSwitch className="mode-more-btn" label="Switch to Advanced" />
        </p>
    );
}

MoreInAdvanced.propTypes = { what: PropTypes.string.isRequired };
