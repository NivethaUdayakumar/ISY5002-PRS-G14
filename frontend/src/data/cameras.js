export const API_BASE_URL = "http://127.0.0.1:8000";

export const areas = [
  {
    name: "Golden Plains",
    cameraCount: 3,
    cameras: [
      { id: "camera_01", name: "Camera 01" },
      { id: "camera_02", name: "Camera 02" },
      { id: "camera_03", name: "Camera 03" },
    ],
  },
  {
    name: "Red Dust Plains",
    cameraCount: 3,
    cameras: [
      { id: "camera_04", name: "Camera 04" },
      { id: "camera_05", name: "Camera 05" },
      { id: "camera_06", name: "Camera 06" },
    ],
  },
];

export const CAMERA_IDS = areas.flatMap((area) => area.cameras.map((camera) => camera.id));

/** "Scrape East, Coastal Lagoons" for a camera id, or the id itself if unknown. */
export function cameraLocation(cameraId) {
  for (const area of areas) {
    const camera = area.cameras.find((item) => item.id === cameraId);
    if (camera) return `${camera.name}, ${area.name}`;
  }
  return cameraId;
}

export function formatTimestamp(iso) {
  const date = new Date(iso);
  const day = date.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
  return `${day} ${date.toLocaleTimeString("en-GB", { hour12: false })}`;
}

/** Display name of a camera, e.g. "Scrape East", or the id itself if unknown. */
export function cameraName(cameraId) {
  for (const area of areas) {
    const camera = area.cameras.find((item) => item.id === cameraId);
    if (camera) return camera.name;
  }
  return cameraId;
}
