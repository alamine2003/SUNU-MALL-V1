import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bell } from "lucide-react";
import * as monetizationApi from "@/api/monetization";
import { useAuthStore } from "@/store/authStore";
import { roleNotificationsPath } from "@/lib/roles";
import { cn, formatDate } from "@/lib/utils";
import type { Notification } from "@/types";

export function NotificationBell() {
  const user = useAuthStore((s) => s.user);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [open, setOpen] = useState(false);

  function load() {
    monetizationApi.listNotifications().then(setNotifications).catch(() => setNotifications([]));
  }

  useEffect(() => {
    if (user) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id]);

  if (!user) return null;

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  async function handleOpen() {
    setOpen((v) => !v);
    if (!open) load();
  }

  async function handleMarkRead(n: Notification) {
    if (n.is_read) return;
    setNotifications((prev) => prev.map((x) => (x.id === n.id ? { ...x, is_read: true } : x)));
    await monetizationApi.markNotificationRead(n.id);
  }

  async function handleMarkAllRead() {
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    await monetizationApi.markAllNotificationsRead();
  }

  return (
    <div className="relative">
      <button onClick={handleOpen} className="group relative flex flex-col items-center gap-0.5 px-2 py-1">
        <div className="relative">
          <Bell className="h-5 w-5 text-gray-500 transition-colors group-hover:text-orange" />
          {unreadCount > 0 && (
            <span className="absolute -right-1.5 -top-1.5 grid h-4 w-4 place-items-center rounded-full bg-orange text-[10px] font-bold text-white">
              {unreadCount > 9 ? "9+" : unreadCount}
            </span>
          )}
        </div>
        <span className="hidden text-[10px] text-gray-400 sm:block">Notifs</span>
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full z-20 mt-2 w-80 overflow-hidden rounded-xl border border-gray-100 bg-white text-left shadow-lg">
            <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
              <p className="text-sm font-semibold text-navy">Notifications</p>
              {unreadCount > 0 && (
                <button onClick={handleMarkAllRead} className="text-xs font-semibold text-orange hover:underline">
                  Tout marquer comme lu
                </button>
              )}
            </div>
            <div className="max-h-80 overflow-y-auto">
              {notifications.length === 0 ? (
                <p className="px-4 py-6 text-center text-sm text-muted-foreground">Aucune notification pour le moment.</p>
              ) : (
                notifications.slice(0, 8).map((n) => (
                  <button
                    key={n.id}
                    onClick={() => handleMarkRead(n)}
                    className={cn(
                      "flex w-full flex-col gap-0.5 border-b border-gray-50 px-4 py-2.5 text-left last:border-b-0 hover:bg-gray-50",
                      !n.is_read && "bg-orange/5",
                    )}
                  >
                    <div className="flex items-center gap-2">
                      {!n.is_read && <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-orange" />}
                      <p className="truncate text-sm font-semibold text-ink">{n.subject}</p>
                    </div>
                    <p className="line-clamp-2 text-xs text-muted-foreground">{n.message}</p>
                    <p className="text-[11px] text-gray-400">{formatDate(n.created_at)}</p>
                  </button>
                ))
              )}
            </div>
            <Link
              to={roleNotificationsPath(user.roles)}
              onClick={() => setOpen(false)}
              className="block border-t border-gray-100 px-4 py-2.5 text-center text-sm font-semibold text-orange hover:bg-gray-50"
            >
              Voir tout
            </Link>
          </div>
        </>
      )}
    </div>
  );
}
