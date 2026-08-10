const notifications = [
  {
    id: 'n1',
    title: 'Camera offline',
    message: 'Camera C1 in Island Mere has gone offline. Check the connection or power supply.',
    time: '2 min ago',
    type: 'warning',
  },
  {
    id: 'n2',
    title: 'Species confirmed',
    message: 'A new leopard detection was confirmed and added to the database.',
    time: '18 min ago',
    type: 'success',
  },
  {
    id: 'n3',
    title: 'System update available',
    message: 'A new update is available for the detection model. Schedule a maintenance window.',
    time: '1h ago',
    type: 'info',
  },
];

function NotificationTile({ notification }) {
  const colors = {
    warning: 'bg-amber-50 text-amber-900 border-amber-200',
    success: 'bg-emerald-50 text-emerald-900 border-emerald-200',
    info: 'bg-sky-50 text-sky-900 border-sky-200',
  };

  return (
    <div className={`rounded-3xl border p-5 shadow-sm ${colors[notification.type]}`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-base font-semibold text-gray-900">{notification.title}</h3>
          <p className="mt-2 text-sm text-gray-700">{notification.message}</p>
        </div>
        <span className="text-xs font-medium uppercase tracking-[0.28em] text-gray-500">
          {notification.time}
        </span>
      </div>
    </div>
  );
}

export default function NotificationsPage() {
  return (
    <div className="p-8">
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Notifications</h1>
          <p className="mt-2 text-sm text-gray-500">
            Monitor system alerts, camera health, and species classification updates from one place.
          </p>
        </div>

        <button className="rounded-full bg-indigo-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-indigo-700">
          Mark all read
        </button>
      </div>

      <div className="grid gap-4">
        {notifications.map((notification) => (
          <NotificationTile key={notification.id} notification={notification} />
        ))}
      </div>
    </div>
  );
}
