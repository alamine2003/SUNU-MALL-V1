import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { cn } from "@/lib/utils";

function dotIcon(color: string) {
  return L.divIcon({
    className: "",
    html: `<div style="width:18px;height:18px;border-radius:9999px;background:${color};border:3px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.45);"></div>`,
    iconSize: [18, 18],
    iconAnchor: [9, 9],
    popupAnchor: [0, -10],
  });
}

const driverIcon = dotIcon("#0A163A");
const destinationIcon = dotIcon("#FF7A00");

export interface MapPoint {
  lat: number;
  lng: number;
  label: string;
}

interface DeliveryMapProps {
  driverPosition?: MapPoint | null;
  destination?: MapPoint | null;
  className?: string;
}

/**
 * Implémenté en Leaflet natif (pas react-leaflet) : react-leaflet v4 lève
 * "Map container is already initialized" sous React 18 StrictMode, qui
 * monte/démonte les composants deux fois en dev pour détecter les effets
 * de bord. Gérer nous-mêmes le cycle de vie (création + `map.remove()` au
 * nettoyage) évite ce problème.
 */
export function DeliveryMap({ driverPosition, destination, className }: DeliveryMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const points = [driverPosition, destination].filter((p): p is MapPoint => !!p);

  useEffect(() => {
    if (!containerRef.current || points.length === 0) return;

    const center: [number, number] =
      points.length === 2
        ? [(points[0].lat + points[1].lat) / 2, (points[0].lng + points[1].lng) / 2]
        : [points[0].lat, points[0].lng];

    const map = L.map(containerRef.current, { scrollWheelZoom: false }).setView(center, points.length === 2 ? 13 : 15);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(map);

    if (driverPosition) {
      L.marker([driverPosition.lat, driverPosition.lng], { icon: driverIcon }).addTo(map).bindPopup(driverPosition.label);
    }
    if (destination) {
      L.marker([destination.lat, destination.lng], { icon: destinationIcon }).addTo(map).bindPopup(destination.label);
    }

    return () => {
      map.remove();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [driverPosition?.lat, driverPosition?.lng, destination?.lat, destination?.lng]);

  if (points.length === 0) return null;

  return <div ref={containerRef} className={cn("overflow-hidden rounded-2xl", className)} />;
}
