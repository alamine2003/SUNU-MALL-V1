import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
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

export function DeliveryMap({ driverPosition, destination, className }: DeliveryMapProps) {
  const points = [driverPosition, destination].filter((p): p is MapPoint => !!p);
  if (points.length === 0) return null;

  const center: [number, number] =
    points.length === 2
      ? [(points[0].lat + points[1].lat) / 2, (points[0].lng + points[1].lng) / 2]
      : [points[0].lat, points[0].lng];

  return (
    <div className={cn("overflow-hidden rounded-2xl", className)}>
      <MapContainer
        key={`${center[0]},${center[1]},${points.length}`}
        center={center}
        zoom={points.length === 2 ? 13 : 15}
        scrollWheelZoom={false}
        className="h-full w-full"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {driverPosition && (
          <Marker position={[driverPosition.lat, driverPosition.lng]} icon={driverIcon}>
            <Popup>{driverPosition.label}</Popup>
          </Marker>
        )}
        {destination && (
          <Marker position={[destination.lat, destination.lng]} icon={destinationIcon}>
            <Popup>{destination.label}</Popup>
          </Marker>
        )}
      </MapContainer>
    </div>
  );
}
