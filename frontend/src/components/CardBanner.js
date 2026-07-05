// CardBanner — a small banner strip shown at the top of an entity listing card
// (Sphere / Alliance / Project). Bleeds to the card edges via negative margins
// that match the shared card padding (1.5em 1.6em); the card's own
// overflow:hidden + border-radius clips the top corners. Renders nothing when
// the entity has no uploaded image, so cards without a banner stay compact.
import React from 'react';
import PropTypes from 'prop-types';
import '../styles/CardBanner.css';

const CardBanner = ({ imageUrl, alt }) => {
  if (!imageUrl) return null;
  return (
    <div className="card-banner" aria-hidden={!alt}>
      <img src={imageUrl} alt={alt || ''} loading="lazy" />
    </div>
  );
};

CardBanner.propTypes = {
  imageUrl: PropTypes.string,
  alt: PropTypes.string,
};

export default CardBanner;
