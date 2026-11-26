export default function LocationTile({ location, selected, onSelect }) {
  return (
    <button
      type="button"
      className={`tile tone-${location.tone}${selected ? " selected" : ""}`}
      onClick={() => onSelect(location)}
    >
      <span className="tile-name">{location.name}</span>
      <span className="tile-counts">
        {location.total === 0
          ? "No views this month"
          : `${location.oppose} oppose · ${location.support} support`}
      </span>
    </button>
  );
}
