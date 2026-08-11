import { useMemo, useState } from 'react';
import { ModalOverlay, ModalCard, ModalHeader } from '../components/modal';
import { PillButton } from '../components/pill_button';

const candidateSpecies = [
  'African elephant',
  'Leopard',
  'White rhino',
  'Red river hog',
  'Vantage bird',
];

export default function ClassifySpeciesModal({ open, onClose, onConfirm }) {
  const [selectedSpecies, setSelectedSpecies] = useState(candidateSpecies[0]);
  const [classificationNotes, setClassificationNotes] = useState('');

  const activeClass = useMemo(
    () => candidateSpecies.find((item) => item === selectedSpecies) || candidateSpecies[0],
    [selectedSpecies],
  );

  if (!open) return null;

  return (
    <ModalOverlay align="end" className="py-10 sm:px-6">
      <ModalCard className="max-w-3xl rounded-3xl shadow-2xl ring-1 ring-black/5">
        <ModalHeader onClose={onClose}>
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-indigo-600">Classification</p>
            <h2 className="mt-2 text-2xl font-semibold text-gray-900">Classify Species</h2>
            <p className="mt-1 text-sm text-gray-500">Review the detected animal and confirm the species label.</p>
          </div>
        </ModalHeader>

        <div className="grid gap-6 px-6 py-6 sm:grid-cols-[320px_1fr]">
          <section className="space-y-4 rounded-3xl bg-slate-50 p-4">
            <div className="relative overflow-hidden rounded-3xl border border-gray-200 bg-white shadow-sm">
              <img
                src="https://images.unsplash.com/photo-1526336024174-e58f5cdd8e13?auto=format&fit=crop&w=720&q=80"
                alt="Detected animal"
                className="h-72 w-full object-cover"
              />
              <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent px-4 py-3 text-white">
                <p className="text-sm font-semibold">Camera 07 · 08 Jun · 16:42</p>
                <p className="text-xs text-white/80">Captured in the lowland foliage</p>
              </div>
            </div>

            <div className="rounded-3xl border border-gray-200 bg-white p-4 text-sm text-gray-700">
              <p className="font-semibold text-gray-900">Classification summary</p>
              <div className="mt-4 space-y-3">
                <div className="flex items-center justify-between rounded-2xl bg-gray-50 px-3 py-2">
                  <span className="text-sm text-gray-500">Current suggestion</span>
                  <span className="font-medium text-gray-900">{activeClass}</span>
                </div>
                <div className="flex items-center justify-between rounded-2xl bg-gray-50 px-3 py-2">
                  <span className="text-sm text-gray-500">Confidence</span>
                  <span className="font-medium text-gray-900">92%</span>
                </div>
                <div className="flex items-center justify-between rounded-2xl bg-gray-50 px-3 py-2">
                  <span className="text-sm text-gray-500">Location</span>
                  <span className="font-medium text-gray-900">Mweru Wetlands</span>
                </div>
              </div>
            </div>
          </section>

          <section className="space-y-6">
            <div className="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
              <h3 className="text-base font-semibold text-gray-900">Select species label</h3>
              <p className="mt-2 text-sm text-gray-500">Choose the species that best matches the animal in the photo.</p>

              <div className="mt-5 grid gap-3">
                {candidateSpecies.map((species) => (
                  <button
                    key={species}
                    type="button"
                    onClick={() => setSelectedSpecies(species)}
                    className={`rounded-3xl border px-4 py-3 text-left text-sm transition ${
                      selectedSpecies === species
                        ? 'border-indigo-500 bg-indigo-50 text-indigo-900'
                        : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300 hover:bg-gray-50'
                    }`}
                  >
                    <span className="font-medium">{species}</span>
                    <span className="mt-1 block text-xs text-gray-500">Suggested by the detection model</span>
                  </button>
                ))}
              </div>
            </div>

            <div className="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
              <label htmlFor="classificationNotes" className="block text-sm font-semibold text-gray-900">
                Notes
              </label>
              <p className="mt-1 text-sm text-gray-500">Add an optional confirmation note for the species classification.</p>
              <textarea
                id="classificationNotes"
                value={classificationNotes}
                onChange={(event) => setClassificationNotes(event.target.value)}
                rows={5}
                className="mt-3 w-full rounded-3xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-900 outline-none ring-indigo-500/20 transition focus:border-indigo-500 focus:bg-white"
                placeholder="Enter any observations or corrections..."
              />
            </div>

            <div className="flex flex-col gap-3 sm:flex-row sm:justify-end">
              <PillButton size="lg" onClick={onClose} className="border border-gray-200 bg-white text-gray-700 hover:bg-gray-50">
                Cancel
              </PillButton>
              <PillButton
                size="lg"
                onClick={() => {
                  if (onConfirm) onConfirm({ species: selectedSpecies, notes: classificationNotes });
                  onClose();
                }}
                className="bg-indigo-600 text-white shadow-sm hover:bg-indigo-700"
              >
                Save classification
              </PillButton>
            </div>
          </section>
        </div>
      </ModalCard>
    </ModalOverlay>
  );
}
