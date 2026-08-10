import { useState } from 'react';
import ClassifySpeciesModal from '../modals/classify_species_modal';

export default function SpeciesPage() {
  const [modalOpen, setModalOpen] = useState(false);
  const [lastClassification, setLastClassification] = useState(null);

  return (
    <div className="p-8">
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Species classification</h1>
          <p className="mt-2 text-sm text-gray-500">
            Review detected animals and confirm species labels before sending them to the monitoring dashboard.
          </p>
        </div>

        <button
          type="button"
          onClick={() => setModalOpen(true)}
          className="inline-flex items-center justify-center rounded-full bg-indigo-600 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700"
        >
          Classify species
        </button>
      </div>

      {lastClassification ? (
        <div className="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">Last classification</h2>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <div className="rounded-3xl bg-gray-50 p-4">
              <p className="text-sm text-gray-500">Species</p>
              <p className="mt-2 text-base font-semibold text-gray-900">{lastClassification.species}</p>
            </div>
            <div className="rounded-3xl bg-gray-50 p-4">
              <p className="text-sm text-gray-500">Notes</p>
              <p className="mt-2 text-base text-gray-900">
                {lastClassification.notes || 'No notes provided.'}
              </p>
            </div>
          </div>
        </div>
      ) : (
        <div className="rounded-3xl border border-dashed border-gray-300 bg-white/80 p-6 text-center text-sm text-gray-500">
          Open the modal to classify the next detected animal.
        </div>
      )}

      <ClassifySpeciesModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onConfirm={(data) => setLastClassification(data)}
      />
    </div>
  );
}
