// What's on: the events of your spheres, and those put on for everyone.
import React from 'react';
import { Link } from 'react-router-dom';
import EventList from '../components/EventList';
import '../styles/Events.css';

export default function EventsPage() {
    return (
        <div className="evt-page">
            <div className="evt-head">
                <div>
                    <h1>What&rsquo;s on</h1>
                    <p className="evt-soft">Your spheres&rsquo; events, and those open to every member.</p>
                </div>
                <Link className="evt-btn evt-btn--main" to="/event-edit">+ Put on an event</Link>
            </div>
            <EventList empty="Nothing is on yet. A mending night, a swap, a shared meal: yours could be the first." />
        </div>
    );
}
