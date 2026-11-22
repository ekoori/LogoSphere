# A Meaning Trail as one chronology: exchanges and acknowledgements together.
#
# Acknowledgements that follow one another with no exchange between them form a
# run. A run of three or more is shown folded: just the highlighted ones (else
# the newest). At most two in a run are highlighted. Pure functions, no database,
# so the rule can be tested and read on its own.
from datetime import datetime

MAX_HIGHLIGHTS = 2
FOLD_FROM = 3


def chronology(exchanges, acks):
    """Entries newest first: ('exchange', exchange) or ('run', [acks newest first]).
    `exchanges` are (when, exchange) pairs; an ack has created_at and ack_id."""
    marks = [(when or datetime.min, 0, '', 'exchange', x) for when, x in exchanges]
    marks += [(a.created_at or datetime.min, 1, str(a.ack_id), 'ack', a) for a in acks]
    marks.sort(key=lambda m: m[:3], reverse=True)
    out, run = [], []
    for _, _, _, what, thing in marks:
        if what == 'ack':
            run.append(thing)
            continue
        if run:
            out.append(('run', run))
            run = []
        out.append(('exchange', thing))
    if run:
        out.append(('run', run))
    return out


def highlights(run):
    """The ids highlighted in a run. Runs can merge (an exchange between two was
    removed, or is hidden from this viewer): only the two latest highlights count."""
    chosen = [a for a in run if a.highlighted_at]
    chosen.sort(key=lambda a: (a.highlighted_at, str(a.ack_id)), reverse=True)
    return {a.ack_id for a in chosen[:MAX_HIGHLIGHTS]}


def shown(run):
    """The ids that stay visible while the run is folded."""
    if len(run) < FOLD_FROM:
        return {a.ack_id for a in run}
    return highlights(run) or {run[0].ack_id}


def run_of(entries, ack_id):
    for what, thing in entries:
        if what == 'run' and any(a.ack_id == ack_id for a in thing):
            return thing
    return []


def may_highlight(entries, ack_id):
    """Whether one more highlight fits in this acknowledgement's run."""
    lit = highlights(run_of(entries, ack_id))
    return ack_id in lit or len(lit) < MAX_HIGHLIGHTS
