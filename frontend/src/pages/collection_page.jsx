import { useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import { initialSightings } from '../data/reserve_map_data';
import folderIcon from '../assets/collections/folder-icon.png';
import deerSample from '../assets/collections/deer-sample.jpg';

function buildCollections(sightings) {
  const byName = new Map();
  sightings.forEach((sighting) => {
    if (sighting.class === 'Unknown') return;
    const existing = byName.get(sighting.species);
    if (existing) {
      existing.count += 1;
    } else {
      byName.set(sighting.species, { name: sighting.species, class: sighting.class, count: 1 });
    }
  });
  return Array.from(byName.values()).sort((a, b) => b.count - a.count);
}

const ALL_COLLECTIONS = buildCollections(initialSightings);

function CollectionCard({ collection }) {
  return (
    <button type="button" className="group flex flex-col items-center text-center">
      <div className="relative aspect-square w-full">
        <img
          src={folderIcon}
          alt=""
          className="absolute inset-0 h-full w-full object-contain transition-transform group-hover:scale-[1.03]"
        />
        <img
          src={deerSample}
          alt={collection.name}
          className="absolute left-[16%] top-[14%] h-[62%] w-[62%] rounded-md object-cover shadow-md ring-2 ring-white"
        />
      </div>
      <div className="mt-1.5">
        <p className="truncate text-xs font-semibold text-gray-900">{collection.name}</p>
        <p className="text-xs text-gray-500">Sightings: {collection.count}</p>
      </div>
    </button>
  );
}

export default function CollectionPage() {
  const [search, setSearch] = useState('');

  const collections = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return ALL_COLLECTIONS;
    return ALL_COLLECTIONS.filter((collection) => collection.name.toLowerCase().includes(term));
  }, [search]);

  return (
    <div className="p-8">
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Collections</h1>
          <p className="mt-2 text-sm text-gray-500">Sightings grouped by species.</p>
        </div>

        <div className="relative w-full sm:w-72">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search species..."
            className="w-full rounded-full border border-gray-200 py-2 pl-9 pr-4 text-sm text-gray-900 placeholder:text-gray-400 focus:border-gray-300 focus:outline-none"
          />
        </div>
      </div>

      {collections.length === 0 ? (
        <p className="text-sm text-gray-500">No species match your search.</p>
      ) : (
        <div className="grid grid-cols-4 gap-x-4 gap-y-6 sm:grid-cols-5 md:grid-cols-6 lg:grid-cols-8 xl:grid-cols-10">
          {collections.map((collection) => (
            <CollectionCard key={collection.name} collection={collection} />
          ))}
        </div>
      )}
    </div>
  );
}
