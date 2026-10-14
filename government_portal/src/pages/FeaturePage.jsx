export default function FeaturePage({ kicker, title }) {
  return (
    <div className="page-shell civic-ui">
      <header className="civic-heading">
        <div>
          <span className="civic-kicker">{kicker}</span>
          <h1>{title}</h1>
        </div>
        <span className="civic-priority">Coming soon</span>
      </header>
      <section className="civic-panel civic-empty feature-placeholder">
        <p>This workflow is being prepared for the government portal.</p>
      </section>
    </div>
  );
}
