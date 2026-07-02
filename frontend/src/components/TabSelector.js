// TabSelector — the site's single, consistent segmented-tab control.
// A pill-shaped switch used for Meaning Trail / Offers·Needs on the home feed,
// the management pages, and anywhere a small set of views share one surface.
//
//   <TabSelector
//       tabs={[{ key: 'a', label: 'Governance' }, { key: 'b', label: 'Value Graph' }]}
//       active={tab}
//       onChange={setTab}
//   />

import React from 'react';
import PropTypes from 'prop-types';
import '../styles/TabSelector.css';

function TabSelector({ tabs, active, onChange, className = '' }) {
    return (
        <div className={`seg-tabs ${className}`} role="tablist">
            {tabs.map(({ key, label, icon }) => (
                <button
                    key={key}
                    type="button"
                    role="tab"
                    aria-selected={active === key}
                    className={`seg-tab ${active === key ? 'is-active' : ''}`}
                    onClick={() => onChange(key)}
                >
                    {icon && <span className="seg-tab-icon" aria-hidden="true">{icon}</span>}
                    {label}
                </button>
            ))}
        </div>
    );
}

TabSelector.propTypes = {
    tabs: PropTypes.arrayOf(PropTypes.shape({
        key: PropTypes.string.isRequired,
        label: PropTypes.node.isRequired,
        icon: PropTypes.node,
    })).isRequired,
    active: PropTypes.string.isRequired,
    onChange: PropTypes.func.isRequired,
    className: PropTypes.string,
};

export default TabSelector;
