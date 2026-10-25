import { useMemo, useState } from 'react';
import { ModalOverlay, ModalCard, ModalHeader } from '../components/modal';
import { API_BASE_URL, cameraLocation, formatTimestamp } from '../data/cameras';

export default function NotificationsModal({ open, onClose, sightings }) {
  const [selectedId, setSelectedId] = useState(null);

  const sortedSightings = useMemo(
    () => sightings.slice().sort((a, b) => new Date(b.lastSeen) - new Date(a.lastSeen)),
    [sightings],
  );

  const selectedSighting = sortedSightings.find((sighting) => sighting.id === selectedId) ?? sortedSightings[0] ?? null;

  if (!open) return null;

  return (
    <ModalOverlay className="py-8">
      <ModalCard className="h-[85vh] max-w-6xl rounded-3xl shadow-2xl ring-1 ring-black/5">
        <ModalHeader onClose={onClose}>
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-bold text-gray-900">Notifications — endangered sightings</h2>
            {sortedSightings.length > 0 && (
              <span className="rounded-full bg-red-600 px-3 py-1 text-xs font-semibold text-white">
                {sortedSightings.length}
              </span>
            )}
          </div>
        </ModalHeader>

        <div className="grid min-h-0 flex-1 grid-cols-[280px_1fr_320px]">
          <div className="min-h-0 overflow-y-auto border-r border-gray-200 p-3">
            {sortedSightings.map((sighting) => (
              <button
                key={sighting.id}
                type="button"
                onClick={() => setSelectedId(sighting.id)}
                className={`mb-1 flex w-full items-center gap-3 rounded-2xl p-2 text-left transition ${
                  sighting.id === selectedSighting?.id ? 'bg-gray-100' : 'hover:bg-gray-50'
                }`}
              >
                <img
                  src={`${API_BASE_URL}${sighting.imageUrl}`}
                  alt={sighting.species}
                  loading="lazy"
                  decoding="async"
                  className="h-14 w-14 flex-shrink-0 rounded-xl bg-gray-200 object-cover"
                />
                <div className="min-w-0">
                  <span className="block truncate text-sm font-semibold text-gray-900">{sighting.species}</span>
                  <p className="truncate text-xs text-gray-500">{cameraLocation(sighting.cameraId)}</p>
                  <p className="truncate text-xs text-gray-400">{formatTimestamp(sighting.lastSeen)}</p>
                </div>
              </button>
            ))}
          </div>

          {selectedSighting ? (
            <>
              <div className="min-h-0 overflow-y-auto p-6">
                <div className="relative overflow-hidden rounded-2xl bg-gray-100">
                  <img
                    src={`${API_BASE_URL}${selectedSighting.imageUrl}`}
                    alt={selectedSighting.species}
                    className="mx-auto max-h-[60vh] w-full object-contain"
                  />
                  <span className="absolute bottom-3 left-4 rounded bg-black/70 px-2 py-1 font-mono text-xs text-white">
                    {formatTimestamp(selectedSighting.lastSeen)}
                  </span>
                </div>
                <p className="mt-3 text-sm text-gray-500">
                  {selectedSighting.cameraId} · Confidence {selectedSighting.confidence.toFixed(2)}
                </p>
              </div>

              <div className="min-h-0 overflow-y-auto border-l border-gray-200 p-6">
                <div className="space-y-2 rounded-2xl bg-gray-50 p-4 text-sm">
                  <p className="text-gray-700">
                    <span className="font-semibold text-gray-900">Classified as:</span> {selectedSighting.species}
                  </p>
                  <p className="text-gray-700">
                    <span className="font-semibold text-gray-900">Class:</span> {selectedSighting.class ?? 'Unknown'}
                  </p>
                  <p className="text-gray-700">
                    <span className="font-semibold text-gray-900">Last seen:</span> {formatTimestamp(selectedSighting.lastSeen)}
                  </p>
                  <p className="text-gray-700">
                    <span className="font-semibold text-gray-900">Location:</span> {cameraLocation(selectedSighting.cameraId)}
                  </p>
                </div>
                <span className="mt-4 inline-block rounded-full bg-red-100 px-3 py-1 text-xs font-semibold text-red-700">
                  Endangered / protected
                </span>
              </div>
            </>
          ) : (
            <div className="col-span-2 flex items-center justify-center p-6 text-sm text-gray-500">
              No endangered sightings yet.
            </div>
          )}
        </div>
      </ModalCard>
    </ModalOverlay>
  );
}
