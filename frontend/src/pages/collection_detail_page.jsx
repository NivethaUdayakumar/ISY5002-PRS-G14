import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { API_BASE_URL, cameraLocation, cameraName, formatTimestamp } from '../data/cameras';
import SightingRecord from '../components/sighting_record';

export default function CollectionDetailPage() {
  const { folderName } = useParams();
  const [collection, setCollection] = useState(null);
  const [error, setError] = useState(null);
  const [selectedSighting, setSelectedSighting] = useState(null);

  useEffect(() => {
    setCollection(null);
    setError(null);
    fetch(`${API_BASE_URL}/collections/${encodeURIComponent(folderName)}`)
      .then((response) => {
        if (!response.ok) throw new Error(response.status === 404 ? 'Collection not found.' : 'Failed to load collection.');
        return response.json();
      })
      .then(setCollection)
      .catch((err) => {
        console.error('Failed to fetch collection', err);
        setError(err.message);
      });
  }, [folderName]);

  return (
    <div className="p-8">
      <Link to="/collections" className="inline-flex items-center gap-1.5 text-sm font-medium text-gray-500 hover:text-gray-900">
        <ArrowLeft className="h-4 w-4" />
        Collections
      </Link>

      <div className="mb-8 mt-3">
        <h1 className="text-2xl font-bold text-gray-900">{folderName}</h1>
        <p className="mt-2 text-sm text-gray-500">
          {collection ? `Sightings: ${collection.images.length}` : error ? '' : 'Loading...'}
        </p>
      </div>

      {error ? (
        <p className="text-sm text-gray-500">{error}</p>
      ) : collection && collection.images.length === 0 ? (
        <p className="text-sm text-gray-500">No images in this collection yet.</p>
      ) : (
        <div className="grid grid-cols-2 gap-x-4 gap-y-8 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
          {collection?.images.map((image) => (
            <button
              key={image.file}
              type="button"
              onClick={() => setSelectedSighting(image.metadata)}
              disabled={!image.metadata}
              className="group cursor-pointer overflow-hidden rounded-xl bg-gray-200 text-left disabled:cursor-default"
            >
              <img
                src={`${API_BASE_URL}${image.imageUrl}`}
                alt={image.metadata?.species ?? image.file}
                loading="lazy"
                className="aspect-square w-full object-cover transition-transform group-hover:scale-[1.03]"
              />
              {(image.metadata || image.cameraId || image.capturedAt) && (
                <div className="space-y-1.5 bg-gray-100 px-2 py-2">
                  <div className="flex min-w-0 items-center gap-1.5">
                    {image.cameraId && (
                      <span className="flex-shrink-0 truncate rounded-full bg-gray-900 px-2.5 py-0.5 text-xs font-semibold text-white">
                        {cameraName(image.cameraId)}
                      </span>
                    )}
                    {image.metadata?.species && <p className="min-w-0 truncate text-sm font-semibold text-gray-900">{image.metadata.species}</p>}
                  </div>
                  {image.capturedAt && <p className="truncate text-xs text-gray-500">{formatTimestamp(image.capturedAt)}</p>}
                </div>
              )}
            </button>
          ))}
        </div>
      )}

      {selectedSighting && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4">
          <div className="max-h-[94vh] w-full max-w-6xl overflow-y-auto rounded-[26px] border border-gray-200 bg-white shadow-2xl">
            <SightingRecord
              key={selectedSighting.id}
              sighting={selectedSighting}
              location={cameraLocation(selectedSighting.cameraId)}
              onClose={() => setSelectedSighting(null)}
            />
          </div>
        </div>
      )}
    </div>
  );
}
