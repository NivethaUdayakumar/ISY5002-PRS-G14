import { useEffect, useRef, useState } from "react";
import { Outlet, NavLink } from "react-router-dom";
import NotificationsModal from "../modals/notifications_modal";
import { API_BASE_URL } from "../data/cameras";

const SIGHTINGS_POLL_MS = 1500;

export default function MainLayout() {
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [endangeredSightings, setEndangeredSightings] = useState([]);
  const signatureRef = useRef("");

  // Live list of endangered sightings, shared by the header button and the modal.
  useEffect(() => {
    let cancelled = false;

    const poll = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/sightings`);
        if (!response.ok || cancelled) return;
        const endangered = (await response.json()).filter((sighting) => sighting.endangered);
        const signature = endangered.map((item) => `${item.id}:${item.lastSeen}:${item.species}`).join("|");
        if (signature !== signatureRef.current) {
          signatureRef.current = signature;
          setEndangeredSightings(endangered);
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

  return (
    <>
   <header className="w-full bg-white border-b border-gray-200">
      <div className="flex items-center justify-between px-8 py-4">
        {/* Left: Logo + nav tabs */}
        <div className="flex items-center gap-8">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-black inline-block" />
            <span className="font-semibold text-lg text-gray-900">WildLens</span>
          </div>

          <nav className="flex items-center gap-1">
            <NavLink
              to="/"
              end
              className={({ isActive }) =>
                `px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
                  isActive ? 'bg-gray-100 text-gray-900' : 'text-gray-500 hover:text-gray-900 hover:bg-gray-50'
                }`
              }
            >
              Cameras
            </NavLink>
            <NavLink
              to="/collections"
              end
              className={({ isActive }) =>
                `px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
                  isActive ? 'bg-gray-100 text-gray-900' : 'text-gray-500 hover:text-gray-900 hover:bg-gray-50'
                }`
              }
            >
              Collections
            </NavLink>
          </nav>
        </div>

        {/* Right: location, notifications, live view */}
        <div className="flex items-center gap-6">


            <button
                type="button"
                onClick={() => setNotificationsOpen(true)}
                className="flex items-center gap-2 rounded-full border border-gray-200 bg-white px-4 py-1.5 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 hover:text-gray-900"
            >
                Notifications
                <span
                  className={`flex h-5 min-w-5 items-center justify-center rounded-full px-1.5 text-[11px] font-semibold leading-none ${
                    endangeredSightings.length > 0 ? 'bg-red-600 text-white' : 'bg-gray-200 text-gray-600'
                  }`}
                >
                  {endangeredSightings.length}
                </span>
            </button>

          
         
        </div>
      </div>
    </header>
    <Outlet />
    <NotificationsModal open={notificationsOpen} onClose={() => setNotificationsOpen(false)} sightings={endangeredSightings} />
    </>
  );
}