import { useState } from "react";
import { Link } from "react-router-dom";
import { cn } from "@/lib/utils";

export function Logo({
  to = "/home",
  light,
  size = 44,
  className,
}: {
  to?: string;
  light?: boolean;
  size?: number;
  className?: string;
}) {
  const [imgFailed, setImgFailed] = useState(false);

  return (
    <Link to={to} className={cn("inline-flex items-center", className)} style={{ height: size }}>
      {imgFailed ? (
        <span
          className={cn(
            "select-none font-display font-extrabold leading-none tracking-tight",
            light ? "text-white" : "text-navy",
          )}
          style={{ fontSize: size * 0.45 }}
        >
          SUNU<span className="text-orange">MALL</span>
        </span>
      ) : (
        <img
          src="/logo.png"
          alt="SUNU MALL"
          onError={() => setImgFailed(true)}
          style={{ height: size, width: "auto", filter: light ? "brightness(0) invert(1)" : undefined }}
          className="select-none object-contain"
        />
      )}
    </Link>
  );
}
