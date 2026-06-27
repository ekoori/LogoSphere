// File: ./frontend/src/components/TrustTrail.js:
// Description: React component file for displaying the trust trail of a user.
// Class: TrustTrail - Presents a list of all transactions of the logged-in users along with corresponding trust points.
// Properties:
//      [-] transaction_history - Contains the list of trust transactions of the logged-in user.
// Methods:
//      [-] add_transaction() - 
//      [-] get_trusttrail() - 
//      [-] componentDidMount() - Fetches user transactions from API when the component loads.
// Features:
//      [-] Users can view their history of transactions and the corresponding trust ratings received.
//      [-] Users can receive trust/gratitude entries from other users in the form of textual comments.
//      [-] Users can post trust/gratitude entries to other users' transactions.



import React from 'react';
import PropTypes from 'prop-types';
import TransactionCard from './TransactionCard';
import ShoutoutCard from './ShoutoutCard';
import '../styles/TrustTrail.css';

function TrustTrail({ items }) {
    return (
        <section id="trusttrail" className="user-trusttrail">
            {items.map(item => (
                item.type === 'shoutout' ? (
                    <ShoutoutCard key={item.id} shoutout={item} />
                ) : (
                    <TransactionCard
                        key={item.id}
                        type={item.type}
                        title={item.title}
                        spheres={item.spheres}
                        participants={item.participants}
                        description={item.description}
                        project={item.project}
                        imageUrl={item.imageUrl}
                        time={item.time}
                        status={item.status}
                        likesCount={item.likesCount}
                        likedByCurrentUser={item.likedByCurrentUser}
                        originService={item.originService}
                        initiatedTime={item.initiatedTime}
                        inProgressTime={item.inProgressTime}
                        finishedTime={item.finishedTime}
                        trustifactedTime={item.trustifactedTime}
                        additionalCommentsTime={item.additionalCommentsTime}
                        trustifacts={item.trustifacts}
                        shoutouts={item.shoutouts}
                        onAddTrustifact={item.onAddTrustifact}
                        onAddShoutout={item.onAddShoutout}
                        onModifyTransaction={item.onModifyTransaction}
                        canModify={item.canModify}
                    />
                )
            ))}
        </section>
    );
}

TrustTrail.propTypes = {
    items: PropTypes.arrayOf(PropTypes.shape({
        id: PropTypes.string.isRequired,
        type: PropTypes.string.isRequired,
        title: PropTypes.string,
        spheres: PropTypes.arrayOf(PropTypes.string).isRequired,
        participants: PropTypes.arrayOf(PropTypes.oneOfType([PropTypes.string, PropTypes.object])),
        description: PropTypes.string,
        project: PropTypes.string,
        imageUrl: PropTypes.string,
        time: PropTypes.string.isRequired,
        status: PropTypes.string,
        likesCount: PropTypes.number.isRequired,
        likedByCurrentUser: PropTypes.bool.isRequired,
        originService: PropTypes.string,
        initiatedTime: PropTypes.string,
        inProgressTime: PropTypes.string,
        finishedTime: PropTypes.string,
        trustifactedTime: PropTypes.string,
        additionalCommentsTime: PropTypes.string,
        trustifacts: PropTypes.arrayOf(PropTypes.shape({
            author: PropTypes.string.isRequired,
            text: PropTypes.string.isRequired,
            time: PropTypes.string.isRequired,
            likesCount: PropTypes.number.isRequired,
            likedByCurrentUser: PropTypes.bool.isRequired,
            imageUrl: PropTypes.string
        })),
        shoutouts: PropTypes.arrayOf(PropTypes.shape({
            author: PropTypes.string.isRequired,
            text: PropTypes.string.isRequired,
            time: PropTypes.string.isRequired,
            likesCount: PropTypes.number.isRequired,
            likedByCurrentUser: PropTypes.bool.isRequired
        })),
        onAddTrustifact: PropTypes.func,
        onAddShoutout: PropTypes.func,
        onModifyTransaction: PropTypes.func,
        canModify: PropTypes.bool
    })).isRequired
};

export default TrustTrail;
