import React from 'react';

const Contribute = () => {
  return (
    <div className="container">
      <main>
        <section className="contribute">
          <h1>Contribute to LogoSphere</h1>
          <p>LogoSphere is an open-source project aimed at building a social network and gift economy platform. We welcome contributions from developers, designers, and anyone interested in making a positive impact. Join us in creating a community-driven platform that fosters trust, collaboration, and mutual support.</p>
        </section>
        <section className="contribute-tech">
          <h3>Technologies We Use</h3>
          <ul>
            <li><strong>Frontend:</strong> React</li>
            <li><strong>Backend:</strong> Flask (Python)</li>
            <li><strong>Database:</strong> Cassandra</li>
            <li><strong>Version Control:</strong> Git</li>
          </ul>
        </section>
        <section className="contribute-phase">
          <h3>Current Development Phase</h3>
          <p>We are currently in the phase of fine-tuning the mockup and translating it into precise requirements for the frontend, data model, database configuration, and backend functionality. Our goal is to close the development loop one class at a time and define unit tests to ensure the robustness of our platform.</p>
        </section>
        <section className="contribute-github">
          <h3>Get Involved</h3>
          <p>Our project is hosted on GitHub. You can find the repository, contribute to the code, report issues, and join discussions:</p>
          <a href="https://github.com/ekoori/LogoSphere" target="_blank" className="btn-github">Visit our GitHub Repository</a>
        </section>
        <section className="contribute-join">
          <h3>Join Our Community</h3>
          <p>Interested in contributing? Join our community of developers and collaborators. Whether you're a seasoned developer or just getting started, your contributions are valuable to us.</p>
          <button className="btn-join">Join LogoSphere on GitHub</button>
        </section>
      </main>
    </div>
  );
};

export default Contribute;
