// A stored place inside the form that saves it (utils/usePlace.js): where,
// and for yourself whether members nearby may find you.
import React from 'react';
import PropTypes from 'prop-types';
import { hasPoint } from '../utils/places';
import PlacePicker from './PlacePicker';
import '../styles/Places.css';

export default function PlaceFields({ editor, label = 'Where' }) {
    if (editor.failed) return <p className="place-problem">The place didn&rsquo;t load, so it stays as it was.</p>;
    if (!editor.loaded) return null;
    return (
        <div className="place-fields">
            <PlacePicker value={editor.place} onChange={editor.setPlace} person={editor.person} label={label} />
            {editor.person && (
                <label className="place-findable">
                    <input type="checkbox" checked={editor.findable} disabled={!hasPoint(editor.place)}
                           onChange={(e) => editor.setFindable(e.target.checked)} />
                    <span>
                        Members nearby can find me
                        <small>
                            {hasPoint(editor.place)
                                ? 'They see your name, the words above and a rough distance. Never the spot.'
                                : 'Put yourself on the map first.'}
                        </small>
                    </span>
                </label>
            )}
        </div>
    );
}

PlaceFields.propTypes = { editor: PropTypes.object.isRequired, label: PropTypes.string };
