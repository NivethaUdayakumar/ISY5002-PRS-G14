import { useState } from "react";
import { Outlet, NavLink } from "react-router-dom";
import NotificationsModal from "../modals/notifications_modal";

export default function MainLayout() {
  const [notificationsOpen, setNotificationsOpen] = useState(false);

  return (
    <>
   <header className="w-full bg-white border-b border-gray-200">
      <div className="flex items-center justify-between px-8 py-4">
        {/* Left: Logo + nav tabs */}
        <div className="flex items-center gap-8">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-black inline-block" />
            <span className="font-semibold text-lg text-gray-900">WildGuard</span>
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
          </nav>
        </div>

        {/* Right: location, notifications, live view */}
        <div className="flex items-center gap-6">


            <button
                onClick={() => setNotificationsOpen(true)}
                className="relative flex items-center gap-1.5 text-sm font-medium text-gray-700 hover:text-gray-900"
            >
                Notifications
                <span className="absolute -top-2 -right-3 flex items-center justify-center w-4 h-4 rounded-full bg-black text-white text-[10px] leading-none">
                3
                </span>
            </button>

          
         
        </div>
      </div>
    </header>
    <Outlet />
    <NotificationsModal open={notificationsOpen} onClose={() => setNotificationsOpen(false)} />
    </>
  );
}