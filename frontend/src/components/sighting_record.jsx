import { API_BASE_URL, formatTimestamp } from "../data/cameras";

function classOf(sighting) {
  return sighting.class ?? "Unknown";
}

export default function SightingRecord({ sighting, location, onBack, onClose, onViewCollection }) {
  return (
    <div className="w-full bg-white">
      <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
        <div className="flex items-center gap-4">
          {onBack && (
            <button
              type="button"
              onClick={onBack}
              className="rounded-full bg-gray-100 px-4 py-1.5 text-sm font-medium text-gray-800 hover:bg-gray-200"
            >
              ← Back
            </button>
          )}
          <h2 className="text-2xl font-bold text-gray-900">Sighting record</h2>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="flex h-10 w-10 items-center justify-center rounded-full bg-gray-200 text-2xl text-gray-700 hover:bg-gray-300"
          aria-label="Close camera modal"
        >
          ×
        </button>
      </div>

      <div className="grid gap-8 p-6 md:grid-cols-2">
        <div>
          <div className="relative overflow-hidden rounded-2xl bg-gray-100">
            <img src={`${API_BASE_URL}${sighting.imageUrl}`} alt={sighting.species} className="mx-auto max-h-[55vh] w-full object-contain" />
            <div className="absolute bottom-3 left-3 rounded bg-black/70 px-2 py-1 font-mono text-xs text-white">
              {formatTimestamp(sighting.lastSeen)}
            </div>
          </div>
          <p className="mt-2 text-sm text-gray-500">
            {sighting.cameraId} · Confidence {sighting.confidence.toFixed(2)}
          </p>
          {sighting.file && <p className="font-mono text-xs text-gray-400">data/sightings/{sighting.file}</p>}
          {onViewCollection && (
            <button type="button" onClick={onViewCollection} className="mt-4 font-semibold text-gray-900 underline">
              View collection →
            </button>
          )}
        </div>

        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-2xl border-2 border-gray-900 bg-white p-5">
              <p className="text-sm font-semibold uppercase tracking-wide text-gray-500">Species</p>
              <p className="mt-1 text-3xl font-bold text-gray-900">{sighting.species}</p>
            </div>
            <div
              className={`rounded-2xl border-2 p-5 ${
                sighting.endangered ? "border-red-600 bg-red-50" : "border-gray-300 bg-white"
              }`}
            >
              <p className="text-sm font-semibold uppercase tracking-wide text-gray-500">Endangered / protected</p>
              <span
                className={`mt-2 inline-block rounded-full px-4 py-1.5 text-lg font-bold ${
                  sighting.endangered ? "bg-red-600 text-white" : "bg-gray-200 text-gray-700"
                }`}
              >
                {sighting.endangered ? "Yes" : "No"}
              </span>
            </div>
          </div>

          <div className="space-y-1.5 rounded-2xl bg-gray-100 p-5 text-base text-gray-900">
            <p><span className="font-bold">Class:</span> {classOf(sighting)}</p>
            <p><span className="font-bold">Last seen:</span> {formatTimestamp(sighting.lastSeen)}</p>
            <p><span className="font-bold">Location:</span> {location}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
