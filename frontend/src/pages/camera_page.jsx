import React from "react";
import { Map } from "lucide-react";

const areas = [
  {
    name: "Wetlands",
    location: "Island Mere Trail — reedbed & open water",
    cameraCount: 2,
    cameras: [
      {
        id: "C1",
        name: "Island Mere",
        timestamp: "10:55:12",
        clock: "10:55",
        sightingsToday: 8,
        thumbnail: "/thumbnails/island-mere.jpg",
      },
      {
        id: "C2",
        name: "Bittern Hide",
        timestamp: "10:55:09",
        clock: "10:55",
        sightingsToday: 5,
        thumbnail: "/thumbnails/bittern-hide.jpg",
      },
    ],
  },
  {
    name: "Coastal Lagoons",
    location: "The Scrape — shingle & shallow lagoons",
    cameraCount: 2,
    cameras: [
      {
        id: "C3",
        name: "Scrape East",
        timestamp: "10:55:14",
        clock: "10:55",
        sightingsToday: 11,
        thumbnail: "/thumbnails/scrape-east.jpg",
      },
      {
        id: "C5",
        name: "Sluice",
        timestamp: "10:55:11",
        clock: "10:55",
        sightingsToday: 9,
        thumbnail: "/thumbnails/sluice.jpg",
      },
    ],
  },
];

function CameraCard({ camera }) {
  return (
    <div className="group cursor-pointer">
      <div className="relative aspect-video w-full overflow-hidden rounded-lg bg-gray-900">
        <img
          src={camera.thumbnail}
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

function AreaSection({ area }) {
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

        <button className="flex items-center gap-1.5 rounded-full border border-gray-200 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors">
          <Map className="h-4 w-4" />
          Map
        </button>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {area.cameras.map((camera) => (
          <CameraCard key={camera.id} camera={camera} />
        ))}
      </div>
    </section>
  );
}

export default function CameraPage() {
  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Live cameras</h1>
        <p className="mt-1 text-sm text-gray-500">3 areas · 6 online</p>
      </div>

      <div className="space-y-10">
        {areas.map((area) => (
          <AreaSection key={area.name} area={area} />
        ))}
      </div>
    </div>
  );
}
