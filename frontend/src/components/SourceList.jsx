export default function SourceList({ sources, openIndex, onToggle }) {
  if (!sources?.length) return null;
  return (
    <div className="sources">
      <div className="sources-title">Nguồn ({sources.length})</div>
      {sources.map((s) => (
        <div key={s.index} className={`source ${openIndex === s.index ? "open" : ""}`}>
          <button className="source-head" onClick={() => onToggle(s.index)}>
            <span className="source-index">[{s.index}]</span>
            <span className="source-section">{s.section}</span>
            <span className="source-score">{s.score.toFixed(2)}</span>
          </button>
          {openIndex === s.index && <p className="source-text">{s.text}</p>}
        </div>
      ))}
    </div>
  );
}