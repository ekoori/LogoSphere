import React from 'react';
import PropTypes from 'prop-types';
import TransactionCard from './TransactionCard';
import ShoutoutCard from './ShoutoutCard';
import '../styles/TrustTrail.css';

function TrustTrail({ items }) {
    return (
        <section id="trusttrail" className="user-trusttrail">
            {items.map((item) =>
                item.type === 'shoutout' ? (
                    <ShoutoutCard key={item.id} shoutout={item} />
                ) : (
                    <TransactionCard
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
                        trustifactedTime={item.trustifactedTime}
                        additionalCommentsTime={item.additionalCommentsTime}
                        trustifacts={item.trustifacts}
                        shoutouts={item.shoutouts}
                        onAddTrustifact={item.onAddTrustifact || (() => {})}
                        onAddShoutout={item.onAddShoutout || (() => {})}
                        onModifyTransaction={item.onModifyTransaction || (() => {})}
                        canModify={item.canModify || false}
                    />
                )
            )}
        </section>
    );
}

TrustTrail.propTypes = {
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
        trustifacts: PropTypes.array,
        shoutouts: PropTypes.array,
        onAddTrustifact: PropTypes.func,
        onAddShoutout: PropTypes.func,
        onModifyTransaction: PropTypes.func,
        canModify: PropTypes.bool,
    })).isRequired,
};

export default TrustTrail;
