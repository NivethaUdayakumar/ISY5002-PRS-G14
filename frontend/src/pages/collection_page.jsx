import { useEffect, useMemo, useState } from 'react';
import { Search, TriangleAlert } from 'lucide-react';
import { Link } from 'react-router-dom';
import { API_BASE_URL } from '../data/cameras';
import folderIcon from '../assets/collections/folder-icon.png';

const ENDANGERED_COLLECTION = 'endangered';

function CollectionCard({ collection }) {
  const endangered = collection.name === ENDANGERED_COLLECTION;
  return (
    <Link to={`/collections/${encodeURIComponent(collection.name)}`} className="group flex flex-col items-center text-center">
      <div className="relative aspect-square w-full">
        <img
          src={folderIcon}
          alt=""
          className="absolute inset-0 h-full w-full object-contain transition-transform group-hover:scale-[1.03]"
        />
        {collection.imageUrl && (
          <img
            src={`${API_BASE_URL}${collection.imageUrl}`}
            alt={collection.name}
            className="absolute left-[16%] top-[14%] h-[62%] w-[62%] rounded-md object-cover shadow-md ring-2 ring-white"
          />
        )}
        {endangered && (
          <span className="absolute right-[6%] top-[6%] flex h-7 w-7 items-center justify-center rounded-full bg-red-600 text-white shadow-md ring-2 ring-white">
            <TriangleAlert className="h-4 w-4" />
          </span>
        )}
      </div>
      <div className="mt-1.5">
        <p className={`truncate text-xs font-semibold ${endangered ? 'text-red-700' : 'text-gray-900'}`}>{collection.name}</p>
        <p className="text-xs text-gray-500">Sightings: {collection.count}</p>
      </div>
    </Link>
  );
}

export default function CollectionPage() {
  const [search, setSearch] = useState('');
  const [allCollections, setAllCollections] = useState([]);

  useEffect(() => {
    fetch(`${API_BASE_URL}/collections`)
      .then((response) => response.json())
      // The backend orders by sighting count; the endangered collection always leads.
      .then((items) => setAllCollections([
        ...items.filter((item) => item.name === ENDANGERED_COLLECTION),
        ...items.filter((item) => item.name !== ENDANGERED_COLLECTION),
      ]))
      .catch((err) => console.error('Failed to fetch collections', err));
  }, []);

  const collections = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return allCollections;
    return allCollections.filter((collection) => collection.name.toLowerCase().includes(term));
  }, [search, allCollections]);

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
