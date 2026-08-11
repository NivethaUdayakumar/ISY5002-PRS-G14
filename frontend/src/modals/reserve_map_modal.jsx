import { useEffect, useMemo, useState } from 'react';
import { X, Bird, PawPrint, CircleHelp, Video, Bookmark, Check, Plus, Trash2, Search, ZoomOut } from 'lucide-react';
import {
  locations,
  cameras,
  initialSightings,
  initialCollections,
  sightingsForCamera,
  sightingsForLocation,
  CLASS_META,
} from '../data/reserve_map_data';

const RING_RADIUS_PX = 36;
const MAX_RING_PINS = 5;
const ZOOM_SCALE = 2.2;

const CLASS_ICONS = { Bird, PawPrint, CircleHelp };

function ClassIcon({ cls, size = 12 }) {
  const meta = CLASS_META[cls] || CLASS_META.Unknown;
  const Icon = CLASS_ICONS[meta.icon] || CircleHelp;
  return <Icon size={size} color={meta.color} strokeWidth={2.25} />;
}

function ringOffsets(count) {
  return Array.from({ length: count }, (_, i) => {
    const angle = (-90 + (360 / count) * i) * (Math.PI / 180);
    return {
      dx: Math.round(Math.cos(angle) * RING_RADIUS_PX),
      dy: Math.round(Math.sin(angle) * RING_RADIUS_PX),
    };
  });
}

function uniqueRingSightings(sightingList, cameraId) {
  const seen = new Set();
  const unique = [];
  for (const sighting of sightingsForCamera(sightingList, cameraId)) {
    if (seen.has(sighting.species)) continue;
    seen.add(sighting.species);
    unique.push(sighting);
    if (unique.length >= MAX_RING_PINS) break;
  }
  return unique;
}

function SightingThumbnail({ cls, saved }) {
  const meta = CLASS_META[cls] || CLASS_META.Unknown;
  return (
    <div
      className="relative h-12 w-12 flex-shrink-0 overflow-hidden rounded-xl"
      style={{
        backgroundColor: meta.fill,
        backgroundImage:
          'repeating-linear-gradient(135deg, rgba(0,0,0,0.06) 0px, rgba(0,0,0,0.06) 2px, transparent 2px, transparent 8px)',
      }}
    >
      <div className="absolute inset-0 flex items-center justify-center">
        <ClassIcon cls={cls} size={18} />
      </div>
      {saved && (
        <div className="absolute right-1 top-1 flex h-4 w-4 items-center justify-center rounded-full bg-[#1e1e1e]">
          <Bookmark size={9} color="#fff" fill="#fff" />
        </div>
      )}
    </div>
  );
}

function SightingCard({ sighting, camera, saved, onOpen }) {
  return (
    <button
      type="button"
      onClick={() => onOpen(sighting)}
      className="mb-1.5 flex w-full items-center gap-3 rounded-2xl p-2 text-left transition hover:bg-[#f5f5f5]"
    >
      <SightingThumbnail cls={sighting.class} saved={saved} />
      <div className="min-w-0">
        <p className="truncate text-sm font-semibold text-[#1e1e1e]">{sighting.species}</p>
        <p className="truncate text-xs text-gray-500">
          {sighting.cameraId}
          {camera ? ` · ${camera.name}` : ''}
        </p>
        <p className="truncate text-xs text-gray-400">{sighting.timestamp}</p>
      </div>
    </button>
  );
}

function CameraLiveViewLightbox({ camera, onClose }) {
  if (!camera) return null;
  return (
    <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/60 p-6">
      <div className="flex max-h-full w-full max-w-md flex-col overflow-hidden rounded-3xl bg-white shadow-2xl ring-1 ring-black/5">
        <div className="flex flex-shrink-0 items-center justify-between border-b border-[#e6e6e6] px-5 py-4">
          <div className="flex items-center gap-2">
            <Video size={16} color="#1e1e1e" />
            <h3 className="text-sm font-semibold text-[#1e1e1e]">
              {camera.id} · {camera.name}
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full bg-[#f0f0f0] p-1.5 text-[#1e1e1e] transition hover:bg-[#e6e6e6]"
            aria-label="Close live view"
          >
            <X size={14} />
          </button>
        </div>
        <div className="overflow-y-auto">
          <div className="relative aspect-video w-full bg-[#1e1e1e]">
            <span className="absolute top-3 left-3 flex items-center gap-1.5 rounded-full bg-black/60 px-2.5 py-1">
              <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
              <span className="text-[11px] font-semibold tracking-wide text-white">LIVE</span>
            </span>
            <span className="absolute inset-0 flex items-center justify-center text-xs text-white/50">
              Live feed placeholder
            </span>
          </div>
          <div className="px-5 py-4 text-xs text-gray-500">{camera.locationName}</div>
        </div>
      </div>
    </div>
  );
}

function SightingDetailLightbox({ sighting, camera, collections, onClose, onToggleCollection, onCreateCollection, onDelete }) {
  const [isCreating, setIsCreating] = useState(false);
  const [newCollectionName, setNewCollectionName] = useState('');

  if (!sighting) return null;
  const meta = CLASS_META[sighting.class] || CLASS_META.Unknown;

  function handleCreate() {
    const name = newCollectionName.trim();
    if (!name) return;
    onCreateCollection(name, sighting.id);
    setIsCreating(false);
    setNewCollectionName('');
  }

  return (
    <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/60 p-6">
      <div className="flex max-h-full w-full max-w-md flex-col overflow-hidden rounded-3xl bg-white shadow-2xl ring-1 ring-black/5">
        <div className="flex flex-shrink-0 items-center justify-between border-b border-[#e6e6e6] px-5 py-4">
          <h3 className="text-sm font-semibold text-[#1e1e1e]">Sighting detail</h3>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full bg-[#f0f0f0] p-1.5 text-[#1e1e1e] transition hover:bg-[#e6e6e6]"
            aria-label="Close sighting detail"
          >
            <X size={14} />
          </button>
        </div>
        <div className="overflow-y-auto p-5">
          <div
            className="relative h-40 w-full overflow-hidden rounded-2xl"
            style={{
              backgroundColor: meta.fill,
              backgroundImage:
                'repeating-linear-gradient(135deg, rgba(0,0,0,0.06) 0px, rgba(0,0,0,0.06) 2px, transparent 2px, transparent 8px)',
            }}
          >
            <div className="absolute inset-0 flex items-center justify-center">
              <ClassIcon cls={sighting.class} size={36} />
            </div>
          </div>
          <div className="mt-4 space-y-2 text-sm">
            <p className="text-base font-semibold text-[#1e1e1e]">{sighting.species}</p>
            <div className="flex items-center gap-1.5">
              <span
                className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium"
                style={{ backgroundColor: meta.fill, color: meta.color }}
              >
                <ClassIcon cls={sighting.class} size={11} />
                {sighting.class}
              </span>
            </div>
            <p className="text-gray-600">
              <span className="font-medium text-[#1e1e1e]">Camera:</span> {sighting.cameraId}
              {camera ? ` · ${camera.name}` : ''}
              {camera ? ` (${camera.locationName})` : ''}
            </p>
            <p className="text-gray-600">
              <span className="font-medium text-[#1e1e1e]">Seen:</span> {sighting.timestamp}
            </p>
            <p className="text-gray-600">
              <span className="font-medium text-[#1e1e1e]">Confidence:</span>{' '}
              {Math.round(sighting.confidence * 100)}%
            </p>
          </div>

          <div className="my-5 h-px bg-[#e6e6e6]" />

          <div>
            <p className="text-sm font-medium text-[#1e1e1e]">Save to collection</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {collections.map((collection) => {
                const active = collection.sightingIds.includes(sighting.id);
                return (
                  <button
                    key={collection.id}
                    type="button"
                    onClick={() => onToggleCollection(collection.id, sighting.id)}
                    className={`inline-flex items-center gap-1 rounded-full border px-3 py-1.5 text-xs font-medium transition ${
                      active
                        ? 'border-[#1e1e1e] bg-[#1e1e1e] text-white'
                        : 'border-[#e6e6e6] bg-white text-[#1e1e1e] hover:bg-[#f5f5f5]'
                    }`}
                  >
                    {active && <Check size={11} />}
                    {collection.name}
                  </button>
                );
              })}

              {!isCreating && (
                <button
                  type="button"
                  onClick={() => setIsCreating(true)}
                  className="inline-flex items-center gap-1 rounded-full border border-dashed border-[#c9c9c9] bg-white px-3 py-1.5 text-xs font-medium text-gray-600 transition hover:bg-[#f5f5f5]"
                >
                  <Plus size={11} />
                  New collection
                </button>
              )}
            </div>

            {isCreating && (
              <div className="mt-2 flex items-center gap-2">
                <input
                  type="text"
                  autoFocus
                  value={newCollectionName}
                  onChange={(event) => setNewCollectionName(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') {
                      event.preventDefault();
                      handleCreate();
                    }
                  }}
                  placeholder="Collection name"
                  className="min-w-0 flex-1 rounded-xl border border-[#e6e6e6] bg-white px-3 py-2 text-sm text-[#1e1e1e] outline-none transition focus:border-[#1e1e1e]"
                />
                <button
                  type="button"
                  onClick={handleCreate}
                  className="flex-shrink-0 rounded-xl bg-[#1e1e1e] px-3 py-2 text-sm font-semibold text-white transition hover:bg-black"
                >
                  Add
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setIsCreating(false);
                    setNewCollectionName('');
                  }}
                  className="flex-shrink-0 rounded-xl border border-[#e6e6e6] bg-white px-3 py-2 text-sm font-semibold text-gray-700 transition hover:bg-[#f5f5f5]"
                >
                  Cancel
                </button>
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={() => onDelete(sighting)}
            className="mt-6 flex items-center gap-1.5 rounded-full border border-[#e6e6e6] bg-white px-4 py-2 text-sm font-semibold text-red-600 transition hover:bg-red-50"
          >
            <Trash2 size={14} />
            Delete sighting
          </button>
        </div>
      </div>
    </div>
  );
}

export default function ReserveMapModal({ open, onClose, initialLocationId }) {
  const [selectedLocationId, setSelectedLocationId] = useState(initialLocationId || locations[0]?.id);
  const [liveViewCamera, setLiveViewCamera] = useState(null);
  const [detailSightingId, setDetailSightingId] = useState(null);
  const [sightingList, setSightingList] = useState(initialSightings);
  const [collections, setCollections] = useState(initialCollections);
  const [zoomedCameraId, setZoomedCameraId] = useState(null);

  useEffect(() => {
    if (open) {
      setSelectedLocationId(initialLocationId || locations[0]?.id);
      setLiveViewCamera(null);
      setDetailSightingId(null);
      setZoomedCameraId(null);
    }
  }, [open, initialLocationId]);

  const selectedLocation = useMemo(
    () => locations.find((location) => location.id === selectedLocationId) || locations[0],
    [selectedLocationId],
  );

  const sidebarSightings = useMemo(
    () => (selectedLocation ? sightingsForLocation(sightingList, selectedLocation.id) : []),
    [selectedLocation, sightingList],
  );

  const visibleCameras = useMemo(
    () => (selectedLocation ? cameras.filter((camera) => camera.locationId === selectedLocation.id) : cameras),
    [selectedLocation],
  );

  const detailSighting = useMemo(
    () => sightingList.find((item) => item.id === detailSightingId) || null,
    [sightingList, detailSightingId],
  );

  const savedSightingIds = useMemo(
    () => new Set(collections.flatMap((collection) => collection.sightingIds)),
    [collections],
  );

  const zoomedCamera = useMemo(
    () => cameras.find((camera) => camera.id === zoomedCameraId) || null,
    [zoomedCameraId],
  );

  if (!open) return null;

  function handleZoomSelect(cameraId) {
    if (!cameraId) {
      setZoomedCameraId(null);
      return;
    }
    const camera = cameras.find((item) => item.id === cameraId);
    if (!camera) return;
    setSelectedLocationId(camera.locationId);
    setZoomedCameraId(cameraId);
  }

  function openCamera(camera) {
    setSelectedLocationId(camera.locationId);
    setLiveViewCamera(camera);
  }

  function openSighting(sighting) {
    const camera = cameras.find((item) => item.id === sighting.cameraId);
    if (camera) setSelectedLocationId(camera.locationId);
    setDetailSightingId(sighting.id);
  }

  function handleToggleCollection(collectionId, sightingId) {
    setCollections((prev) =>
      prev.map((collection) =>
        collection.id === collectionId
          ? {
              ...collection,
              sightingIds: collection.sightingIds.includes(sightingId)
                ? collection.sightingIds.filter((id) => id !== sightingId)
                : [...collection.sightingIds, sightingId],
            }
          : collection,
      ),
    );
  }

  function handleCreateCollection(name, sightingId) {
    const existing = collections.find((collection) => collection.name.toLowerCase() === name.toLowerCase());
    if (existing) {
      handleToggleCollection(existing.id, sightingId);
      return;
    }
    const id = `col-${Date.now()}`;
    setCollections((prev) => [...prev, { id, name, sightingIds: [sightingId] }]);
  }

  function handleDeleteSighting(sighting) {
    setSightingList((prev) => prev.filter((item) => item.id !== sighting.id));
    setCollections((prev) =>
      prev.map((collection) => ({
        ...collection,
        sightingIds: collection.sightingIds.filter((id) => id !== sighting.id),
      })),
    );
    setDetailSightingId(null);
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4 py-4"
      style={{ fontFamily: "'Instrument Sans', sans-serif" }}
    >
      <div className="flex h-[94vh] w-full max-w-[1600px] flex-col overflow-hidden rounded-3xl border border-[#e6e6e6] bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-[#e6e6e6] px-6 py-5">
          <div>
            <h2 className="text-lg font-semibold text-[#1e1e1e]">Reserve map — camera network</h2>
            <p className="mt-1 text-sm text-gray-500">
              {visibleCameras.length} cameras · {sidebarSightings.length} sightings this week
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full bg-[#f0f0f0] p-2 text-[#1e1e1e] transition hover:bg-[#e6e6e6]"
            aria-label="Close reserve map"
          >
            <X size={16} />
          </button>
        </div>

        <div className="flex min-h-0 flex-1">
          <div className="relative min-w-0 flex-1 overflow-hidden">
            <div
              className="absolute inset-0 transition-transform duration-500 ease-out"
              style={
                zoomedCamera
                  ? {
                      transformOrigin: `${zoomedCamera.x}% ${zoomedCamera.y}%`,
                      transform: `translate(${50 - zoomedCamera.x}%, ${50 - zoomedCamera.y}%) scale(${ZOOM_SCALE})`,
                    }
                  : undefined
              }
            >
              <div
                className="absolute inset-0"
                style={{
                  backgroundImage: `url('${selectedLocation?.mapImage || '/reserve-map.svg'}')`,
                  backgroundSize: 'cover',
                  backgroundPosition: 'center',
                }}
              />

              {visibleCameras.map((camera) => {
                const ring = uniqueRingSightings(sightingList, camera.id);
                const offsets = ringOffsets(ring.length);
                return (
                  <div key={camera.id} className="contents">
                    {ring.map((sighting, i) => {
                      const meta = CLASS_META[sighting.class] || CLASS_META.Unknown;
                      const { dx, dy } = offsets[i];
                      return (
                        <button
                          key={sighting.id}
                          type="button"
                          onClick={() => openSighting(sighting)}
                          className="group absolute z-20 flex h-5 w-5 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border border-white shadow-sm transition hover:scale-110"
                          style={{
                            left: `calc(${camera.x}% + ${dx}px)`,
                            top: `calc(${camera.y}% + ${dy}px)`,
                            backgroundColor: meta.color,
                          }}
                          aria-label={sighting.species}
                        >
                          <ClassIcon cls={sighting.class} size={10} />
                          <span
                            className="pointer-events-none absolute bottom-full left-1/2 mb-1.5 -translate-x-1/2 whitespace-nowrap rounded-full bg-[#1e1e1e] px-2 py-1 text-[11px] font-medium text-white opacity-0 shadow-lg transition group-hover:opacity-100"
                          >
                            {sighting.species}
                          </span>
                        </button>
                      );
                    })}

                    <button
                      type="button"
                      onClick={() => openCamera(camera)}
                      className="absolute z-30 flex h-8 w-8 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border-2 border-white bg-[#1e1e1e] text-[11px] font-semibold text-white shadow-md transition hover:scale-110"
                      style={{ left: `${camera.x}%`, top: `${camera.y}%` }}
                      aria-label={`Open live view for ${camera.name}`}
                      title={`${camera.id} · ${camera.name}`}
                    >
                      {camera.id}
                    </button>
                  </div>
                );
              })}
            </div>

            <div className="absolute left-3 top-3 z-40 flex items-center gap-2">
              <div className="flex items-center gap-1.5 rounded-full border border-[#e6e6e6] bg-white/95 px-3 py-1.5 shadow-sm backdrop-blur-sm">
                <Search size={13} color="#6b6b6b" />
                <select
                  value={zoomedCameraId || ''}
                  onChange={(event) => handleZoomSelect(event.target.value)}
                  className="bg-transparent text-xs font-medium text-[#1e1e1e] outline-none"
                  aria-label="Zoom to camera"
                >
                  <option value="">Zoom to camera…</option>
                  {visibleCameras.map((camera) => (
                    <option key={camera.id} value={camera.id}>
                      {camera.id} · {camera.name}
                    </option>
                  ))}
                </select>
              </div>
              {zoomedCamera && (
                <button
                  type="button"
                  onClick={() => handleZoomSelect(null)}
                  className="flex items-center gap-1.5 rounded-full border border-[#e6e6e6] bg-white/95 px-3 py-1.5 text-xs font-medium text-[#1e1e1e] shadow-sm backdrop-blur-sm transition hover:bg-[#f5f5f5]"
                >
                  <ZoomOut size={13} />
                  Full map
                </button>
              )}
            </div>

            <div className="absolute bottom-3 left-3 z-10 rounded-full border border-[#e6e6e6] bg-white/85 px-3 py-1 text-[11px] text-gray-500 backdrop-blur-sm">
              Placeholder map — not the real reserve survey map
            </div>

            <CameraLiveViewLightbox camera={liveViewCamera} onClose={() => setLiveViewCamera(null)} />
            <SightingDetailLightbox
              sighting={detailSighting}
              camera={detailSighting ? cameras.find((item) => item.id === detailSighting.cameraId) : null}
              collections={collections}
              onClose={() => setDetailSightingId(null)}
              onToggleCollection={handleToggleCollection}
              onCreateCollection={handleCreateCollection}
              onDelete={handleDeleteSighting}
            />
          </div>

          <div className="w-[250px] flex-shrink-0 overflow-y-auto border-l border-[#e6e6e6] bg-white p-4">
            {selectedLocation && (
              <>
                <h3 className="text-sm font-semibold text-[#1e1e1e]">{selectedLocation.name}</h3>
                <p className="mt-0.5 text-xs text-gray-500">{selectedLocation.description}</p>
                <div className="mt-4 space-y-0.5">
                  {sidebarSightings.map((sighting) => (
                    <SightingCard
                      key={sighting.id}
                      sighting={sighting}
                      camera={cameras.find((item) => item.id === sighting.cameraId)}
                      saved={savedSightingIds.has(sighting.id)}
                      onOpen={openSighting}
                    />
                  ))}
                  {sidebarSightings.length === 0 && (
                    <p className="mt-2 text-sm text-gray-400">No sightings for this location.</p>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
