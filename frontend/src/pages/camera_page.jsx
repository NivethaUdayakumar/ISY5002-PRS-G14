import React, { memo, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { sightingsForCamera } from "../data/reserve_map_data";
import { API_BASE_URL, CAMERA_IDS, areas, formatTimestamp } from "../data/cameras";
import SightingRecord from "../components/sighting_record";

const MIN_FRAME_INTERVAL_MS = 100;
const SIGHTINGS_POLL_MS = 1500;
const EMPTY_STATS = { sightings: 0, species: 0 };

const CameraCard = memo(function CameraCard({ camera, frameSrc, stats }) {
  return (
    <div className="group cursor-pointer">
      <div className="relative aspect-video w-full overflow-hidden rounded-lg bg-gray-900">
        <img src={frameSrc} alt={camera.name} className="h-full w-full object-cover" />

        <div className="absolute left-3 top-3 flex items-center gap-1.5 rounded bg-black/70 px-2 py-1">
          <span className="text-[11px] font-semibold tracking-wide text-white">{camera.id}</span>
          <span className="text-[11px] text-white/60">·</span>
          <span className="text-[11px] font-semibold tracking-wide text-white">LIVE</span>
          <span className="block h-2 w-2 rounded-full bg-red-500" />
        </div>

        <div className="absolute bottom-3 left-3 text-sm font-medium text-white/90 drop-shadow">
          {camera.clock}
        </div>

        <div className="absolute bottom-3 right-3 rounded bg-black/70 px-1.5 py-0.5 text-[11px] text-white">
          {camera.timestamp}
        </div>
      </div>

      <div className="mt-2 flex items-center justify-between">
        <span className="text-sm font-semibold text-gray-900">{camera.name}</span>
        <span className="text-sm text-gray-500">
          {stats.sightings} {stats.sightings === 1 ? "sighting" : "sightings"} · {stats.species} species
        </span>
      </div>
    </div>
  );
});

function AreaSection({ area, frames, stats, onOpenCamera }) {
  return (
    <section>
      <div className="border-b border-gray-200 pb-3">
        <div className="flex items-baseline gap-3">
          <h2 className="text-base font-semibold text-gray-900">{area.name}</h2>
          <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700">
            {area.cameraCount} cameras
          </span>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {area.cameras.map((camera) => (
          <button key={camera.id} type="button" onClick={() => onOpenCamera(camera, area.name)} className="text-left">
            <CameraCard camera={camera} frameSrc={frames[camera.id] ?? undefined} stats={stats[camera.id] ?? EMPTY_STATS} />
          </button>
        ))}
      </div>
    </section>
  );
}

const SightingListItem = memo(
  function SightingListItem({ sighting, onSelect }) {
    return (
      <button
        type="button"
        onClick={() => onSelect(sighting.id)}
        className="w-full overflow-hidden rounded-xl border border-gray-200 bg-white text-left transition hover:border-gray-900"
      >
        <img
          src={`${API_BASE_URL}${sighting.imageUrl}`}
          alt={sighting.species}
          loading="lazy"
          decoding="async"
          className="aspect-video w-full bg-gray-100 object-contain"
        />
        <div className="p-2.5">
          <div className="flex items-start justify-between gap-2">
            <p className="truncate text-sm font-semibold text-gray-900">{sighting.species}</p>
            <span className="rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-medium text-gray-700">
              {sighting.confidence.toFixed(2)}
            </span>
          </div>
          <div className="mt-1 flex items-center justify-between gap-2">
            <p className="text-[11px] text-gray-500">{formatTimestamp(sighting.lastSeen)}</p>
            {sighting.endangered && (
              <span className="rounded-full bg-red-100 px-2 py-0.5 text-[10px] font-semibold text-red-700">Endangered</span>
            )}
          </div>
        </div>
      </button>
    );
  },
  (prev, next) =>
    prev.sighting.id === next.sighting.id &&
    prev.sighting.lastSeen === next.sighting.lastSeen &&
    prev.sighting.species === next.sighting.species &&
    prev.sighting.endangered === next.sighting.endangered &&
    prev.sighting.confidence === next.sighting.confidence
);

function CameraLiveModal({ camera, areaName, frameSrc, sightings, onClose, onViewCollection }) {
  const [selectedSightingId, setSelectedSightingId] = useState(null);

  const cameraSightings = useMemo(
    () => sightingsForCamera(sightings, camera.id).slice().sort((a, b) => new Date(b.lastSeen) - new Date(a.lastSeen)),
    [camera.id, sightings]
  );

  const selectedSighting = cameraSightings.find((sighting) => sighting.id === selectedSightingId) ?? null;
  const location = `${camera.name}, ${areaName}`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4">
      <div className="max-h-[94vh] w-full max-w-6xl overflow-y-auto rounded-[26px] border border-gray-200 bg-[#f7f7f7] shadow-2xl">
        {selectedSighting ? (
          <SightingRecord
            key={selectedSighting.id}
            sighting={selectedSighting}
            location={location}
            onBack={() => setSelectedSightingId(null)}
            onClose={onClose}
            onViewCollection={onViewCollection}
          />
        ) : (
          <>
            <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
              <h2 className="text-3xl font-bold text-gray-900">{camera.name} · Live</h2>
              <button
                type="button"
                onClick={onClose}
                className="flex h-10 w-10 items-center justify-center rounded-full bg-gray-200 text-2xl text-gray-700 hover:bg-gray-300"
                aria-label="Close camera modal"
              >
                ×
              </button>
            </div>

            <div className="flex min-h-[60vh] w-full">
              <div className="w-[80%] border-r border-gray-200 bg-white p-6">
                <div className="relative aspect-video w-full overflow-hidden rounded-[18px] bg-gray-900">
                  {frameSrc ? (
                    <img src={frameSrc} alt={camera.name} className="h-full w-full object-cover" />
                  ) : (
                    <div className="flex h-full items-center justify-center text-sm text-gray-400">Waiting for camera frame…</div>
                  )}
                  <div className="absolute left-4 top-4 flex items-center gap-1.5 rounded bg-black/70 px-2 py-1 text-[11px] font-semibold tracking-wide text-white">
                    {camera.id} · LIVE <span className="ml-1 block h-2 w-2 rounded-full bg-red-500" />
                  </div>
                </div>
                <p className="mt-3 text-sm text-gray-600">{location}</p>
              </div>

              <aside className="flex w-[20%] flex-col bg-[#f2f2f2] p-4">
                <div className="mb-4 rounded-2xl border border-gray-200 bg-white p-3 shadow-sm">
                  <p className="text-3xl font-bold text-gray-900">{cameraSightings.length}</p>
                  <p className="text-sm text-gray-600">sightings captured</p>
                </div>

                <div className="max-h-[48vh] flex-1 space-y-3 overflow-y-auto pr-1">
                  {cameraSightings.length === 0 ? (
                    <div className="rounded-xl border border-dashed border-gray-300 bg-white p-4 text-sm text-gray-500">
                      No sightings captured yet.
                    </div>
                  ) : (
                    cameraSightings.map((sighting) => (
                      <SightingListItem key={sighting.id} sighting={sighting} onSelect={setSelectedSightingId} />
                    ))
                  )}
                </div>

                <button
                  type="button"
                  onClick={onViewCollection}
                  className="mt-4 w-full rounded-full border border-gray-300 bg-white px-4 py-2.5 text-sm font-medium text-gray-800 transition hover:bg-gray-50"
                >
                  View collection →
                </button>
              </aside>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default function CameraPage() {
  const navigate = useNavigate();
  const [frames, setFrames] = useState({});
  const [selectedCamera, setSelectedCamera] = useState(null);
  const [runtimeSightings, setRuntimeSightings] = useState([]);
  const sightingsSignatureRef = useRef("");

  // Frames: one request at a time, with the offset following the wall clock so the
  // video stays in real time even when the server is slower than the polling rate.
  useEffect(() => {
    let cancelled = false;
    let frameUrls = {};
    const startedAt = performance.now();

    const loop = async () => {
      while (!cancelled) {
        const requestStarted = performance.now();
        const offset = 1 + (requestStarted - startedAt) / 1000;
        try {
          const response = await fetch(`${API_BASE_URL}/frames?camera_ids=${CAMERA_IDS.join(",")}&offset=${offset.toFixed(2)}`);
          if (response.ok && !cancelled) {
            const data = await response.json();
            // Show frames via object URLs that are revoked once replaced: a fresh
            // multi-hundred-KB data URL per tick makes the browser keep every decoded
            // image around and eventually run out of memory.
            const blobs = await Promise.all(
              Object.entries(data)
                .filter(([, src]) => src) // null = camera unreadable; keep its last frame
                .map(async ([cameraId, src]) => [cameraId, await (await fetch(src)).blob()])
            );
            if (cancelled) break;
            const next = { ...frameUrls };
            for (const [cameraId, blob] of blobs) {
              if (next[cameraId]) URL.revokeObjectURL(next[cameraId]);
              next[cameraId] = URL.createObjectURL(blob);
            }
            frameUrls = next;
            setFrames(next);
          }
        } catch (err) {
          console.error("Failed to fetch camera frames", err);
          await new Promise((resolve) => setTimeout(resolve, 1000));
        }
        const elapsed = performance.now() - requestStarted;
        if (elapsed < MIN_FRAME_INTERVAL_MS) {
          await new Promise((resolve) => setTimeout(resolve, MIN_FRAME_INTERVAL_MS - elapsed));
        }
      }
    };

    loop();
    return () => {
      cancelled = true;
      Object.values(frameUrls).forEach((url) => URL.revokeObjectURL(url));
    };
  }, []);

  // Sightings: polled independently, and only re-rendered when something changed.
  useEffect(() => {
    let cancelled = false;

    const poll = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/sightings`);
        if (!response.ok || cancelled) return;
        const data = await response.json();
        const signature = data.map((item) => `${item.id}:${item.lastSeen}:${item.species}:${item.class}:${item.endangered}`).join("|");
        if (signature !== sightingsSignatureRef.current) {
          sightingsSignatureRef.current = signature;
          setRuntimeSightings(data);
        }
      } catch (err) {
        console.error("Failed to fetch sightings", err);
      }
    };

    poll();
    const interval = setInterval(poll, SIGHTINGS_POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const stats = useMemo(() => {
    const result = {};
    for (const cameraId of CAMERA_IDS) {
      const cameraSightings = sightingsForCamera(runtimeSightings, cameraId);
      result[cameraId] = {
        sightings: cameraSightings.length,
        species: new Set(cameraSightings.map((sighting) => sighting.species)).size,
      };
    }
    return result;
  }, [runtimeSightings]);

  return (
    <div className="p-8">
      <div className="space-y-10">
        {areas.map((area) => (
          <AreaSection
            key={area.name}
            area={area}
            frames={frames}
            stats={stats}
            onOpenCamera={(camera, areaName) => setSelectedCamera({ ...camera, areaName })}
          />
        ))}
      </div>

      {selectedCamera && (
        <CameraLiveModal
          camera={selectedCamera}
          areaName={selectedCamera.areaName}
          frameSrc={frames[selectedCamera.id]}
          sightings={runtimeSightings}
          onClose={() => setSelectedCamera(null)}
          onViewCollection={() => {
            setSelectedCamera(null);
            navigate("/collections");
          }}
        />
      )}
    </div>
  );
}
