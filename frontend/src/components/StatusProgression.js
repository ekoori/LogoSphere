// Unified phase-progression control: an arrow/chevron flow showing where a
// transaction or service is in its lifecycle. Used by ServiceCard and
// TransactionCard so the whole app shows status the same way.
import React from 'react';
import '../styles/StatusProgression.css';

function StatusProgression({ steps, currentIndex, cancelled = false }) {
    return (
        <div className="status-progression" role="list">
            {steps.map((step, i) => {
                const label = typeof step === 'string' ? step : step.label;
                const time = typeof step === 'string' ? '' : step.time;
                let state = 'pending';
                if (cancelled && i === currentIndex) state = 'cancelled';
                else if (i < currentIndex) state = 'done';
                else if (i === currentIndex) state = 'active';
                return (
                    <div key={i} role="listitem" className={`phase phase-${state}`} style={{ zIndex: steps.length - i }}>
                        <span className="phase-label">{label}</span>
                        {time ? <span className="phase-time">{time}</span> : null}
                    </div>
                );
            })}
        </div>
    );
}

export default StatusProgression;
