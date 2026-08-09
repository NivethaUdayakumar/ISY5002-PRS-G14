import { Outlet } from "react-router-dom";

export default function MainLayout() {
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
            <button className="px-4 py-1.5 rounded-full bg-gray-100 text-sm font-medium text-gray-900">
              Cameras
            </button>
            <button className="px-4 py-1.5 rounded-full text-sm font-medium text-gray-500 hover:text-gray-900 hover:bg-gray-50 transition-colors">
              Collections
            </button>
          </nav>
        </div>

        {/* Right: location, notifications, live view */}
        <div className="flex items-center gap-6">


            <button className="relative flex items-center gap-1.5 text-sm font-medium text-gray-700 hover:text-gray-900">
                Notifications
                <span className="absolute -top-2 -right-3 flex items-center justify-center w-4 h-4 rounded-full bg-black text-white text-[10px] leading-none">
                3
                </span>
            </button>

          
         
        </div>
      </div>
    </header>
    <Outlet />
    </>
  );
}