// Mock data model for the Reserve map modal.
// Cameras are grouped into named location areas and have fixed percentage
// positions on the map background. Sightings reference a camera + species/class.

export const CLASS_META = {
  Birds: { color: '#4a7c4e', fill: '#e7efe6', icon: 'Bird' },
  Mammals: { color: '#8a5a35', fill: '#f1e6da', icon: 'PawPrint' },
  Unknown: { color: '#6b6b6b', fill: '#ececec', icon: 'CircleHelp' },
};

export const locations = [
  {
    id: 'wetlands',
    name: 'Sonian Forest',
    description: 'Island Mere Trail — reedbed & open water',
    cameras: [
      { id: 'C1', name: 'Island Mere', lat: 52.2372, lng: 1.6108 },
      { id: 'C2', name: 'Bittern Hide', lat: 52.2352, lng: 1.6135 },
    ],
  },
  {
    id: 'coastal-lagoons',
    name: 'Coastal Lagoons',
    description: 'The Scrape — shingle & shallow lagoons',
    cameras: [
      { id: 'C3', name: 'Scrape East', lat: 52.2445, lng: 1.623 },
      { id: 'C4', name: 'Sluice', lat: 52.2461, lng: 1.6248 },
    ],
  },
  {
    id: 'heathland',
    name: 'Heathland',
    description: 'Whin Hill — dry heath & scrub',
    cameras: [
      { id: 'C5', name: 'Whin Hill', lat: 52.2458, lng: 1.61 },
      { id: 'C6', name: 'North Wall', lat: 52.2478, lng: 1.6165 },
    ],
  },
];

export const cameras = locations.flatMap((location) =>
  location.cameras.map((camera) => ({ ...camera, locationId: location.id, locationName: location.name })),
);

export function locationCenter(location) {
  const lat = location.cameras.reduce((sum, camera) => sum + camera.lat, 0) / location.cameras.length;
  const lng = location.cameras.reduce((sum, camera) => sum + camera.lng, 0) / location.cameras.length;
  return { lat, lng };
}

export const RESERVE_CENTER = { lat: 52.2417, lng: 1.6183 };

export const initialSightings = [
  // Island Mere (C1)
  { id: 'sg-01', cameraId: 'C1', species: 'Grey Heron', class: 'Birds', timestamp: '11 Aug 2026 07:18', confidence: 0.94 },
  { id: 'sg-02', cameraId: 'C1', species: 'Eurasian Otter', class: 'Mammals', timestamp: '10 Aug 2026 19:42', confidence: 0.88 },
  { id: 'sg-03', cameraId: 'C1', species: 'Reed Warbler', class: 'Birds', timestamp: '09 Aug 2026 06:05', confidence: 0.81 },
  { id: 'sg-04', cameraId: 'C1', species: 'Unidentified animal', class: 'Unknown', timestamp: '07 Aug 2026 23:51', confidence: 0.38 },

  // Bittern Hide (C2)
  { id: 'sg-05', cameraId: 'C2', species: 'Bittern', class: 'Birds', timestamp: '11 Aug 2026 05:47', confidence: 0.9 },
  { id: 'sg-06', cameraId: 'C2', species: 'Water Vole', class: 'Mammals', timestamp: '10 Aug 2026 08:12', confidence: 0.79 },
  { id: 'sg-07', cameraId: 'C2', species: 'Little Egret', class: 'Birds', timestamp: '09 Aug 2026 17:30', confidence: 0.92 },
  { id: 'sg-08', cameraId: 'C2', species: 'Kingfisher', class: 'Birds', timestamp: '08 Aug 2026 12:03', confidence: 0.87 },
  { id: 'sg-09', cameraId: 'C2', species: 'Unknown (night)', class: 'Unknown', timestamp: '06 Aug 2026 02:14', confidence: 0.31 },

  // Scrape East (C3)
  { id: 'sg-10', cameraId: 'C3', species: 'Little Egret', class: 'Birds', timestamp: '11 Aug 2026 09:22', confidence: 0.9 },
  { id: 'sg-11', cameraId: 'C3', species: 'Avocet', class: 'Birds', timestamp: '10 Aug 2026 16:08', confidence: 0.85 },
  { id: 'sg-12', cameraId: 'C3', species: 'Red Fox', class: 'Mammals', timestamp: '09 Aug 2026 21:37', confidence: 0.93 },
  { id: 'sg-13', cameraId: 'C3', species: 'Unclear species', class: 'Unknown', timestamp: '08 Aug 2026 04:59', confidence: 0.42 },

  // Sluice (C4)
  { id: 'sg-14', cameraId: 'C4', species: 'Eurasian Otter', class: 'Mammals', timestamp: '11 Aug 2026 06:40', confidence: 0.86 },
  { id: 'sg-15', cameraId: 'C4', species: 'Grey Heron', class: 'Birds', timestamp: '10 Aug 2026 18:55', confidence: 0.91 },
  { id: 'sg-16', cameraId: 'C4', species: 'European Badger', class: 'Mammals', timestamp: '09 Aug 2026 22:48', confidence: 0.89 },
  { id: 'sg-17', cameraId: 'C4', species: 'Kingfisher', class: 'Birds', timestamp: '07 Aug 2026 13:21', confidence: 0.83 },

  // Whin Hill (C5)
  { id: 'sg-18', cameraId: 'C5', species: 'Red Fox', class: 'Mammals', timestamp: '11 Aug 2026 04:12', confidence: 0.95 },
  { id: 'sg-19', cameraId: 'C5', species: 'Roe Deer', class: 'Mammals', timestamp: '10 Aug 2026 05:33', confidence: 0.97 },
  { id: 'sg-20', cameraId: 'C5', species: 'Eurasian Jay', class: 'Birds', timestamp: '09 Aug 2026 11:15', confidence: 0.84 },
  { id: 'sg-21', cameraId: 'C5', species: 'Brown Hare', class: 'Mammals', timestamp: '08 Aug 2026 20:02', confidence: 0.8 },
  { id: 'sg-22', cameraId: 'C5', species: 'Unidentified animal', class: 'Unknown', timestamp: '06 Aug 2026 01:47', confidence: 0.35 },

  // North Wall (C6)
  { id: 'sg-23', cameraId: 'C6', species: 'European Badger', class: 'Mammals', timestamp: '11 Aug 2026 03:05', confidence: 0.91 },
  { id: 'sg-24', cameraId: 'C6', species: 'Water Vole', class: 'Mammals', timestamp: '09 Aug 2026 07:52', confidence: 0.76 },
  { id: 'sg-25', cameraId: 'C6', species: 'Grey Heron', class: 'Birds', timestamp: '08 Aug 2026 18:19', confidence: 0.88 },
  { id: 'sg-26', cameraId: 'C6', species: 'Unknown (motion blur)', class: 'Unknown', timestamp: '05 Aug 2026 22:36', confidence: 0.29 },
];

export function sightingsForCamera(sightingList, cameraId) {
  return sightingList.filter((sighting) => sighting.cameraId === cameraId);
}

export function sightingsForLocation(sightingList, locationId) {
  const location = locations.find((item) => item.id === locationId);
  if (!location) return [];
  const cameraIds = new Set(location.cameras.map((camera) => camera.id));
  return sightingList
    .filter((sighting) => cameraIds.has(sighting.cameraId))
    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
}

export const initialCollections = [
  { id: 'col-highlights', name: 'Highlights', sightingIds: [] },
  { id: 'col-needs-review', name: 'Needs review', sightingIds: [] },
];
