// A button that asks twice before doing what can't be undone.
import React, { useState } from 'react';
import PropTypes from 'prop-types';

export default function TwoPress({ label, confirmLabel, onConfirm, disabled = false, className = '' }) {
    const [armed, setArmed] = useState(false);
    const press = () => {
        if (!armed) {
            setArmed(true);
            return;
        }
        setArmed(false);
        onConfirm();
    };
    return (
        <button type="button" className={`${className}${armed ? ' is-danger' : ''}`} disabled={disabled}
                onClick={press} onBlur={() => setArmed(false)}>
            {armed ? confirmLabel : label}
        </button>
    );
}

TwoPress.propTypes = {
    label: PropTypes.node.isRequired,
    confirmLabel: PropTypes.node.isRequired,
    onConfirm: PropTypes.func.isRequired,
    disabled: PropTypes.bool,
    className: PropTypes.string,
};
