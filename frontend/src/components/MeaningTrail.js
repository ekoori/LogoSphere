import React from 'react';
import PropTypes from 'prop-types';
import InteractionCard from './InteractionCard';
import ShoutoutCard from './ShoutoutCard';
import '../styles/MeaningTrail.css';

function MeaningTrail({ items }) {
    return (
        <section id="meaning-trail" className="user-meaning-trail">
            {items.map((item) =>
                item.type === 'shoutout' ? (
                    <ShoutoutCard key={item.id} shoutout={item} />
                ) : (
                    <InteractionCard
                        key={item.id}
                        id={item.id}
                        type={item.type}
                        title={item.title}
                        spheres={item.spheres}
                        participants={item.participants}
                        description={item.description}
                        project={item.project}
                        projectId={item.projectId}
                        imageUrl={item.imageUrl}
                        time={item.time}
                        status={item.status}
                        likesCount={item.likesCount}
                        likedByCurrentUser={item.likedByCurrentUser}
                        initiatedTime={item.initiatedTime}
                        inProgressTime={item.inProgressTime}
                        finishedTime={item.finishedTime}
                        receiptedTime={item.receiptedTime}
                        additionalCommentsTime={item.additionalCommentsTime}
                        receipts={item.receipts}
                        shoutouts={item.shoutouts}
                        onAddReceipt={item.onAddReceipt || (() => {})}
                        onAddShoutout={item.onAddShoutout || (() => {})}
                        onModifyInteraction={item.onModifyInteraction || (() => {})}
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
        shoutouts: PropTypes.array,
        onAddReceipt: PropTypes.func,
        onAddShoutout: PropTypes.func,
        onModifyInteraction: PropTypes.func,
        canModify: PropTypes.bool,
    })).isRequired,
};

export default MeaningTrail;
