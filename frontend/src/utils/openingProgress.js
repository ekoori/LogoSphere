// Shared progress-bar model for an opening's lifecycle, used by both the
// ServiceCard (feed) and the OpeningPage (detail) so the two never drift.
//
// A single-cadence opening walks Posted -> Accepted -> In Progress -> Completed
// once, with a real date per phase as it's reached. A perpetual opening gathers
// many acceptances, so its middle phases become aggregate "(multiple)" labels
// showing the most recent activation date.

export const SERVICE_STEPS = ['Posted', 'Accepted', 'In Progress', 'Completed'];
const PERPETUAL_LABELS = ['Posted', 'Accepted (multiple)', 'In Progress (multiple)', 'Completed (multiple)'];

// Accepts the mapService-shaped fields (either the whole mapped service object,
// or ServiceCard's individual props gathered into one). Returns everything
// StatusProgression needs: { steps, currentIndex, cancelled }.
export function buildOpeningProgress({
    status, cadence,
    postedAt, acceptedAt, inProgressAt, completedAt,
    activity,
}) {
    const cancelled = status === 'Cancelled';
    const isPerpetual = cadence === 'perpetual';

    const currentIndex = cancelled ? 1
        : isPerpetual
            ? (activity?.completedLastAt ? 3 : activity?.inProgressCount ? 2 : activity?.acceptedCount ? 1 : 0)
            : Math.max(0, SERVICE_STEPS.findIndex((s) => s.toLowerCase() === (status || '').toLowerCase()));

    const singleDates = [postedAt, acceptedAt, inProgressAt, completedAt];
    const perpetualDates = [postedAt, activity?.acceptedLastAt, activity?.inProgressLastAt, activity?.completedLastAt];

    const steps = SERVICE_STEPS.map((label, i) => ({
        label: isPerpetual ? PERPETUAL_LABELS[i] : label,
        // A phase's date only appears once that phase has actually been reached.
        time: i <= currentIndex ? (isPerpetual ? perpetualDates[i] : singleDates[i]) || '' : '',
    }));

    return { steps, currentIndex, cancelled };
}
