import React, { useEffect, useRef, useState } from "react";
import { Map } from "lucide-react";
import ReserveMapModal from "../modals/reserve_map_modal";
import { locations as reserveMapLocations } from "../data/reserve_map_data";

const OFFSET_TICK_INTERVAL_MS = 1000;

const areas = [
  {
    name: "Sonian Forest",
    location: "Belgium",
    cameraCount: 2,
    cameras: [
      {
        id: "camera_01",
        name: "Camera 01",
        sightingsToday: 8,
      },
      {
        id: "camera_02",
        name: "Camera 02",
        sightingsToday: 5,
      },
      {
        id: "camera_03",
        name: "Camera 03",
        sightingsToday: 3,
      },
    ],
  },
  {
    name: "Coastal Lagoons",
    location: "The Scrape — shingle & shallow lagoons",
    cameraCount: 2,
    cameras: [
      {
        id: "camera_04",
        name: "Scrape East",
        sightingsToday: 11,
      },
      {
        id: "camera_05",
        name: "Sluice",
        sightingsToday: 9,
      },
      {
        id: "camera_06",
        name: "Sluice",
        sightingsToday: 9,
      },
    ],
  },
];

function CameraCard({ camera, offset }) {
  const [frameSrc, setFrameSrc] = useState();
  const [detections, setDetections] = useState([]);
  const prevUrlRef = useRef(null);
  const requestIdRef = useRef(0);
  const appliedRequestIdRef = useRef(0);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  // Refetch the frame whenever offset changes. Detection adds real backend
  // latency, so a request can still be in flight when the next tick fires —
  // apply whichever request resolves most recently instead of dropping
  // slow-but-still-latest frames, so a camera can't get stuck blank.
  useEffect(() => {
    const requestId = ++requestIdRef.current;

    const fetchFrame = async () => {
      try {
        const res = await fetch(
          `http://127.0.0.1:8000/frame?camera_id=${camera.id}&offset=${offset}`
        );
        if (!res.ok || !mountedRef.current) return;

        const blob = await res.blob();
        if (!mountedRef.current || requestId <= appliedRequestIdRef.current) return;

        const url = URL.createObjectURL(blob);
        setFrameSrc(url);
        if (prevUrlRef.current) URL.revokeObjectURL(prevUrlRef.current);
        prevUrlRef.current = url;
        appliedRequestIdRef.current = requestId;

        const detectionsRes = await fetch(
          `http://127.0.0.1:8000/detections?camera_id=${camera.id}`
        );
        if (detectionsRes.ok && mountedRef.current) {
          setDetections(await detectionsRes.json());
        }
      } catch (err) {
        console.error("Failed to fetch camera frame", err);
      }
    };

    fetchFrame();
  }, [offset, camera.id]);

  useEffect(() => {
    return () => {
      if (prevUrlRef.current) URL.revokeObjectURL(prevUrlRef.current);
    };
  }, []);

  return (
    <div className="group cursor-pointer">
      <div className="relative aspect-video w-full overflow-hidden rounded-lg bg-gray-900">
        <img
          src={frameSrc}
          alt={camera.name}
          className="h-full w-full object-cover"
        />

        {/* Top-left label: camera id + LIVE */}
        <div className="absolute top-3 left-3 flex items-center gap-1.5 rounded bg-black/70 px-2 py-1">
          <span className="text-[11px] font-semibold tracking-wide text-white">
            {camera.id}
          </span>
          <span className="text-[11px] text-white/60">·</span>
          <span className="text-[11px] font-semibold tracking-wide text-white">
            LIVE
          </span>
        </div>

        {/* Top-right recording dot */}
        <div className="absolute top-3 right-3">
          <span className="block h-2 w-2 rounded-full bg-red-500" />
        </div>

        {detections.length > 0 && (
          <div className="absolute bottom-10 left-3 flex flex-wrap gap-1">
            {detections.slice(0, 3).map((detection, index) => (
              <span
                key={index}
                className="rounded bg-emerald-600/85 px-1.5 py-0.5 text-[10px] font-semibold text-white"
              >
                {detection.species} · {Math.round(detection.confidence * 100)}%
              </span>
            ))}
          </div>
        )}

        {/* Bottom-left clock */}
        <div className="absolute bottom-3 left-3 text-sm font-medium text-white/90 drop-shadow">
          {camera.clock}
        </div>

        {/* Bottom-right timestamp */}
        <div className="absolute bottom-3 right-3 rounded bg-black/70 px-1.5 py-0.5 text-[11px] text-white">
          {camera.timestamp}
        </div>
      </div>

      {/* Caption row */}
      <div className="mt-2 flex items-center justify-between">
        <span className="text-sm font-semibold text-gray-900">
          {camera.name}
        </span>
        <span className="text-sm text-gray-500">
          {camera.sightingsToday} sightings today
        </span>
      </div>
    </div>
  );
}

function AreaSection({ area, offset, onOpenMap }) {
  return (
    <section>
      <div className="flex items-center justify-between border-b border-gray-200 pb-3">
        <div className="flex items-baseline gap-3">
          <h2 className="text-base font-semibold text-gray-900">
            {area.name}
          </h2>
          <span className="text-sm text-gray-500">{area.location}</span>
          <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700">
            {area.cameraCount} cameras
          </span>
        </div>

        <button
          onClick={() => onOpenMap(area.name)}
          className="flex items-center gap-1.5 rounded-full border border-gray-200 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
        >
          <Map className="h-4 w-4" />
          Map
        </button>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {area.cameras.map((camera) => (
          <CameraCard key={camera.id} camera={camera} offset={offset} />
        ))}
      </div>
    </section>
  );
}

export default function CameraPage() {
  const [mapOpen, setMapOpen] = useState(false);
  const [mapInitialLocationId, setMapInitialLocationId] = useState(null);
  const [offset, setOffset] = useState(1);

  useEffect(() => {
    const interval = setInterval(() => {
      setOffset((prev) => prev + 1);
    }, OFFSET_TICK_INTERVAL_MS);

    return () => clearInterval(interval);
  }, []);

  function handleOpenMap(areaName) {
    const location = reserveMapLocations.find((item) => item.name === areaName);
    setMapInitialLocationId(location?.id ?? null);
    setMapOpen(true);
  }

  return (
    <div className="p-8">

      <div className="space-y-10">
        {areas.map((area) => (
          <AreaSection
            key={area.name}
            area={area}
            offset={offset}
            onOpenMap={handleOpenMap}
          />
        ))}
      </div>

      <ReserveMapModal
        open={mapOpen}
        onClose={() => setMapOpen(false)}
        initialLocationId={mapInitialLocationId}
      />
    </div>
  );
}
