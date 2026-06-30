import React from 'react';

const Donate = () => {
  return (
    <div className="container">
      <main>
        <section className="donate-intro">
          <h1>Support LogoSphere</h1>
          <p>LogoSphere relies on the generous support of its members to continue building a community-driven platform. Your donations help us improve the platform, add new features, and maintain our services. Any contribution, big or small, is greatly appreciated.</p>
        </section>
        <section className="donate-methods">
          <h2>How to Donate</h2>
          <p>You can make a donation using PayPal. Simply click the button below to proceed with your donation.</p>
          <div className="paypal-button">
            <form action="https://www.paypal.com/donate" method="post" target="_top">
              <input type="hidden" name="business" value="donate@logosphere.net" />
              <input type="hidden" name="no_recurring" value="0" />
              <input type="hidden" name="item_name" value="Support LogoSphere" />
              <input type="hidden" name="currency_code" value="USD" />
              <input type="image" src="https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif" border="0" name="submit" title="PayPal - The safer, easier way to pay online!" alt="Donate with PayPal button" />
              <img alt="" border="0" src="https://www.paypal.com/en_US/i/scr/pixel.gif" width="1" height="1" />
            </form>
          </div>
        </section>
        <section className="donate-thanks">
          <h2>Thank You!</h2>
          <p>We deeply appreciate your support. Your donation helps us continue our mission to foster trust, collaboration, and mutual support within our community.</p>
        </section>
      </main>
    </div>
  );
};

export default Donate;
