import React from 'react';
import PropTypes from 'prop-types';
import ExchangeCard from './ExchangeCard';
import AcknowledgementCard from './AcknowledgementCard';
import '../styles/MeaningTrail.css';

function MeaningTrail({ items }) {
    return (
        <section id="meaning-trail" className="user-meaning-trail">
            {items.map((item) =>
                item.type === 'acknowledgement' ? (
                    <AcknowledgementCard key={item.id} acknowledgement={item} />
                ) : (
                    // Every mapped field (isDemo, likedBy, canLike, ...) reaches the card.
                    <ExchangeCard
                        key={item.id}
                        {...item}
                        onAddReceipt={item.onAddReceipt || (() => {})}
                        onAddAcknowledgement={item.onAddAcknowledgement || (() => {})}
                        onModifyExchange={item.onModifyExchange || (() => {})}
                        canModify={item.canModify || false}
                    />
                )
            )}
        </section>
    );
}

MeaningTrail.propTypes = {
    items: PropTypes.arrayOf(PropTypes.shape({
        id: PropTypes.string.isRequired,
        type: PropTypes.string.isRequired,
        title: PropTypes.string,
        spheres: PropTypes.array,
        participants: PropTypes.array,
        description: PropTypes.string,
        project: PropTypes.string,
        projectId: PropTypes.string,
        imageUrl: PropTypes.string,
        time: PropTypes.string.isRequired,
        status: PropTypes.string,
        likesCount: PropTypes.number.isRequired,
        likedByCurrentUser: PropTypes.bool.isRequired,
        receipts: PropTypes.array,
        acknowledgements: PropTypes.array,
        onAddReceipt: PropTypes.func,
        onAddAcknowledgement: PropTypes.func,
        onModifyExchange: PropTypes.func,
        canModify: PropTypes.bool,
    })).isRequired,
};

export default MeaningTrail;
