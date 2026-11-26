import LocationTile from "./LocationTile.jsx";

export default function LocationList({ locations, selectedId, onSelect }) {
  if (!locations.length) {
    return <p className="empty">No locations in the database yet.</p>;
  }

  return (
    <div className="tile-stack">
      {locations.map((location) => (
        <LocationTile
          key={location.location_id}
          location={location}
          selected={selectedId === location.location_id}
          onSelect={onSelect}
        />
      ))}
    </div>
  );
}
