import React from 'react';

const Privacy = () => {
  return (
    <div className="container">
      <main>
        <section className="privacy-intro">
          <h1>Privacy Policy</h1>
          <p>Your privacy is important to us. This privacy policy explains what personal data LogoSphere collects from you, how we use that data, and your rights regarding your personal information.</p>
        </section>
        <section className="privacy-collection">
          <h2>Data Collection</h2>
          <p>We collect the following types of data:</p>
          <ul>
            <li><strong>Personal Information:</strong> Name, email address, and other contact details provided during registration.</li>
            <li><strong>Usage Data:</strong> Information about how you use our platform, including the pages you visit, the features you use, and the actions you take.</li>
            <li><strong>Device Data:</strong> Information about the device you use to access our platform, including your IP address, browser type, and operating system.</li>
          </ul>
        </section>
        <section className="privacy-usage">
          <h2>Data Usage</h2>
          <p>We use your data for the following purposes:</p>
          <ul>
            <li>To provide and maintain our services</li>
            <li>To improve and personalize your experience</li>
            <li>To communicate with you, including sending updates and notifications</li>
            <li>To analyze usage patterns and improve our platform</li>
            <li>To comply with legal obligations</li>
          </ul>
        </section>
        <section className="privacy-sharing">
          <h2>Data Sharing</h2>
          <p>We do not sell or rent your personal information to third parties. We may share your data with:</p>
          <ul>
            <li>Service providers who assist us in operating our platform</li>
            <li>Legal authorities if required by law or to protect our rights</li>
          </ul>
        </section>
        <section className="privacy-rights">
          <h2>Your Rights</h2>
          <p>You have the following rights regarding your personal data:</p>
          <ul>
            <li>The right to access and update your information</li>
            <li>The right to request the deletion of your data</li>
            <li>The right to object to or restrict the processing of your data</li>
            <li>The right to data portability</li>
            <li>The right to withdraw consent at any time</li>
          </ul>
          <p>If you have any questions or concerns about your privacy, please contact us at <a href="mailto:privacy@logosphere.net">privacy@logosphere.net</a>.</p>
        </section>
      </main>
    </div>
  );
};

export default Privacy;
