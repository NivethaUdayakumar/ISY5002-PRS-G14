import { useMemo, useState } from 'react';
import { ModalOverlay, ModalCard, ModalHeader } from '../components/modal';
import { PillButton } from '../components/pill_button';
import { StripedPlaceholder } from '../components/striped_placeholder';

const initialSpeciesOptions = [
  'Eurasian Jay',
  'Eurasian Otter',
  'Red Fox',
  'European Badger',
  'Grey Heron',
  'Water Vole',
  'Unknown',
];

const NEW_SPECIES_VALUE = '__new__';

const classOptions = [
  'Mammals',
  'Birds',
  'Fish',
  'Reptiles',
  'Amphibians',
  'Insects',
  'Arachnids',
  'Mollusks',
  'Crustaceans',
  'Unknown',
];

const initialSightings = [
  {
    id: 's1',
    species: 'Eurasian Jay',
    class: 'Birds',
    location: 'Island Mere',
    camera: 'C1',
    datetime: '1 Aug 2026 08:00:00',
    frame: '0412',
    confidence: 0.91,
    endangered: 'No',
    isNew: false,
  },
  {
    id: 's2',
    species: 'Eurasian Otter',
    class: 'Mammals',
    location: 'Sluice',
    camera: 'C5',
    datetime: '1 Aug 2026 06:42:18',
    frame: '0387',
    confidence: 0.87,
    endangered: 'Yes',
    isNew: true,
  },
  {
    id: 's3',
    species: 'Red Fox',
    class: 'Mammals',
    location: 'Whin Hill',
    camera: 'C4',
    datetime: '31 Jul 2026 22:15:44',
    frame: '0361',
    confidence: 0.95,
    endangered: 'No',
    isNew: false,
  },
  {
    id: 's4',
    species: 'European Badger',
    class: 'Mammals',
    location: 'Bittern Hide',
    camera: 'C2',
    datetime: '31 Jul 2026 21:03:29',
    frame: '0349',
    confidence: 0.89,
    endangered: 'No',
    isNew: false,
  },
  {
    id: 's5',
    species: 'Grey Heron',
    class: 'Birds',
    location: 'Scrape East',
    camera: 'C3',
    datetime: '31 Jul 2026 19:37:02',
    frame: '0322',
    confidence: 0.93,
    endangered: 'No',
    isNew: false,
  },
  {
    id: 's6',
    species: 'Unknown',
    class: 'Unknown',
    location: 'North Wall',
    camera: 'C6',
    datetime: '31 Jul 2026 03:12:51',
    frame: '0298',
    confidence: 0.41,
    endangered: 'No',
    isNew: true,
  },
  {
    id: 's7',
    species: 'Water Vole',
    class: 'Mammals',
    location: 'Bittern Hide',
    camera: 'C7',
    datetime: '30 Jul 2026 18:47:11',
    frame: '0276',
    confidence: 0.78,
    endangered: 'Yes',
    isNew: true,
  },
];

function SightingThumbnail() {
  return <StripedPlaceholder className="h-14 w-14 flex-shrink-0 rounded-xl bg-gray-200" />;
}

export default function NotificationsModal({ open, onClose }) {
  const [sightings, setSightings] = useState(initialSightings);
  const [speciesOptions, setSpeciesOptions] = useState(initialSpeciesOptions);
  const [selectedId, setSelectedId] = useState(initialSightings[0]?.id ?? null);
  const [reclassifySpecies, setReclassifySpecies] = useState(initialSightings[0]?.species ?? '');
  const [reclassifyClass, setReclassifyClass] = useState(initialSightings[0]?.class ?? '');
  const [endangered, setEndangered] = useState(initialSightings[0]?.endangered ?? 'No');
  const [isCreatingSpecies, setIsCreatingSpecies] = useState(false);
  const [newSpeciesName, setNewSpeciesName] = useState('');

  const selectedSighting = useMemo(
    () => sightings.find((sighting) => sighting.id === selectedId) || null,
    [sightings, selectedId],
  );

  const newCount = useMemo(() => sightings.filter((sighting) => sighting.isNew).length, [sightings]);

  if (!open) return null;

  function handleSelect(sighting) {
    setSelectedId(sighting.id);
    setReclassifySpecies(sighting.species);
    setReclassifyClass(sighting.class);
    setEndangered(sighting.endangered);
    setIsCreatingSpecies(false);
    setNewSpeciesName('');
  }

  function handleSpeciesChange(value) {
    if (value === NEW_SPECIES_VALUE) {
      setIsCreatingSpecies(true);
      return;
    }
    setReclassifySpecies(value);
  }

  function handleAddSpecies() {
    const name = newSpeciesName.trim();
    if (!name) return;
    if (!speciesOptions.some((option) => option.toLowerCase() === name.toLowerCase())) {
      setSpeciesOptions((prev) => [...prev, name]);
    }
    setReclassifySpecies(name);
    setIsCreatingSpecies(false);
    setNewSpeciesName('');
  }

  function handleCancelAddSpecies() {
    setIsCreatingSpecies(false);
    setNewSpeciesName('');
  }

  function handleDeleteSpecies() {
    if (!reclassifySpecies) return;
    const remaining = speciesOptions.filter((option) => option !== reclassifySpecies);
    setSpeciesOptions(remaining);
    setReclassifySpecies(remaining[0] ?? '');
  }

  function handleSave() {
    if (!selectedSighting) return;
    setSightings((prev) =>
      prev.map((sighting) =>
        sighting.id === selectedSighting.id
          ? { ...sighting, species: reclassifySpecies, class: reclassifyClass, endangered, isNew: false }
          : sighting,
      ),
    );
  }

  function handleDelete() {
    if (!selectedSighting) return;
    const remaining = sightings.filter((sighting) => sighting.id !== selectedSighting.id);
    setSightings(remaining);
    const next = remaining[0] || null;
    setSelectedId(next?.id ?? null);
    setReclassifySpecies(next?.species ?? '');
    setReclassifyClass(next?.class ?? '');
    setEndangered(next?.endangered ?? 'No');
    setIsCreatingSpecies(false);
    setNewSpeciesName('');
  }

  return (
    <ModalOverlay className="py-8">
      <ModalCard className="h-[85vh] max-w-6xl rounded-3xl shadow-2xl ring-1 ring-black/5">
        <ModalHeader onClose={onClose}>
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-bold text-gray-900">Notifications — unreviewed sightings</h2>
            {newCount > 0 && (
              <span className="rounded-full bg-black px-3 py-1 text-xs font-semibold text-white">
                {newCount} NEW
              </span>
            )}
          </div>
        </ModalHeader>

        <div className="grid min-h-0 flex-1 grid-cols-[280px_1fr_320px]">
          <div className="min-h-0 overflow-y-auto border-r border-gray-200 p-3">
            {sightings.map((sighting) => (
              <button
                key={sighting.id}
                type="button"
                onClick={() => handleSelect(sighting)}
                className={`mb-1 flex w-full items-center gap-3 rounded-2xl p-2 text-left transition ${
                  sighting.id === selectedId ? 'bg-gray-100' : 'hover:bg-gray-50'
                }`}
              >
                <SightingThumbnail />
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="truncate text-sm font-semibold text-gray-900">{sighting.species}</span>
                    {sighting.isNew && (
                      <span className="h-2 w-2 flex-shrink-0 rounded-full bg-red-500" aria-label="Unreviewed" />
                    )}
                  </div>
                  <p className="truncate text-xs text-gray-500">
                    {sighting.location}, {sighting.camera}
                  </p>
                  <p className="truncate text-xs text-gray-400">{sighting.datetime}</p>
                </div>
              </button>
            ))}
          </div>

          {selectedSighting ? (
            <>
              <div className="min-h-0 overflow-y-auto p-6">
                <div className="relative aspect-video w-full overflow-hidden rounded-2xl bg-black">
                  <span className="absolute bottom-3 left-4 font-mono text-sm text-white/90">
                    {selectedSighting.datetime}
                  </span>
                </div>
                <p className="mt-3 text-sm text-gray-500">
                  Frame {selectedSighting.frame} · Confidence {selectedSighting.confidence.toFixed(2)}
                </p>
              </div>

              <div className="min-h-0 overflow-y-auto border-l border-gray-200 p-6">
                <div className="space-y-2 rounded-2xl bg-gray-50 p-4 text-sm">
                  <p className="text-gray-700">
                    <span className="font-semibold text-gray-900">Classified as:</span> {selectedSighting.species}
                  </p>
                  <p className="text-gray-700">
                    <span className="font-semibold text-gray-900">Class:</span> {selectedSighting.class}
                  </p>
                  <p className="text-gray-700">
                    <span className="font-semibold text-gray-900">Last seen:</span> {selectedSighting.datetime}
                  </p>
                  <p className="text-gray-700">
                    <span className="font-semibold text-gray-900">Location:</span> {selectedSighting.location}, {selectedSighting.camera}
                  </p>
                </div>

                <div className="mt-6">
                  <div className="flex items-center justify-between">
                    <label className="block text-sm font-medium text-gray-700">Reclassify species</label>
                    {!isCreatingSpecies && reclassifySpecies && (
                      <button
                        type="button"
                        onClick={handleDeleteSpecies}
                        className="text-xs font-semibold text-red-600 transition hover:text-red-700"
                      >
                        Delete species
                      </button>
                    )}
                  </div>
                  <select
                    value={isCreatingSpecies ? NEW_SPECIES_VALUE : reclassifySpecies}
                    onChange={(event) => handleSpeciesChange(event.target.value)}
                    className="mt-2 w-full rounded-xl border border-gray-200 bg-white px-3 py-2.5 text-sm text-gray-900 outline-none ring-indigo-500/20 transition focus:border-indigo-500"
                  >
                    {speciesOptions.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                    <option value={NEW_SPECIES_VALUE}>+ Create new species…</option>
                  </select>

                  {isCreatingSpecies && (
                    <div className="mt-2 flex items-center gap-2">
                      <input
                        type="text"
                        autoFocus
                        value={newSpeciesName}
                        onChange={(event) => setNewSpeciesName(event.target.value)}
                        onKeyDown={(event) => {
                          if (event.key === 'Enter') {
                            event.preventDefault();
                            handleAddSpecies();
                          }
                        }}
                        placeholder="New species name"
                        className="min-w-0 flex-1 rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 outline-none ring-indigo-500/20 transition focus:border-indigo-500"
                      />
                      <button
                        type="button"
                        onClick={handleAddSpecies}
                        className="flex-shrink-0 rounded-xl bg-black px-3 py-2 text-sm font-semibold text-white transition hover:bg-gray-800"
                      >
                        Add
                      </button>
                      <button
                        type="button"
                        onClick={handleCancelAddSpecies}
                        className="flex-shrink-0 rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-50"
                      >
                        Cancel
                      </button>
                    </div>
                  )}
                </div>

                <div className="mt-5">
                  <label className="block text-sm font-medium text-gray-700">Reclassify class</label>
                  <select
                    value={reclassifyClass}
                    onChange={(event) => setReclassifyClass(event.target.value)}
                    className="mt-2 w-full rounded-xl border border-gray-200 bg-white px-3 py-2.5 text-sm text-gray-900 outline-none ring-indigo-500/20 transition focus:border-indigo-500"
                  >
                    {classOptions.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="mt-5">
                  <label className="block text-sm font-medium text-gray-700">Endangered / protected</label>
                  <select
                    value={endangered}
                    onChange={(event) => setEndangered(event.target.value)}
                    className="mt-2 w-full rounded-xl border border-gray-200 bg-white px-3 py-2.5 text-sm text-gray-900 outline-none ring-indigo-500/20 transition focus:border-indigo-500"
                  >
                    <option value="No">No</option>
                    <option value="Yes">Yes</option>
                  </select>
                </div>

                <div className="mt-6 flex items-center gap-3">
                  <PillButton onClick={handleSave} className="bg-black text-white hover:bg-gray-800">
                    Save
                  </PillButton>
                  <PillButton onClick={handleDelete} className="border border-gray-200 bg-white text-gray-700 hover:bg-gray-50">
                    Delete sighting
                  </PillButton>
                </div>
              </div>
            </>
          ) : (
            <div className="col-span-2 flex items-center justify-center p-6 text-sm text-gray-500">
              No sightings to review.
            </div>
          )}
        </div>
      </ModalCard>
    </ModalOverlay>
  );
}
