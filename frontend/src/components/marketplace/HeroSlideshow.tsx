import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

interface Slide {
  src: string;
  alt: string;
}

interface HeroSlideshowProps {
  images: Slide[];
  intervalMs?: number;
  className?: string;
}

export function HeroSlideshow({ images, intervalMs = 4500, className }: HeroSlideshowProps) {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (images.length <= 1) return;
    const timer = setInterval(() => setIndex((i) => (i + 1) % images.length), intervalMs);
    return () => clearInterval(timer);
  }, [images.length, intervalMs]);

  return (
    <div className={cn("absolute inset-0 overflow-hidden", className)}>
      {images.map((img, i) => (
        <img
          key={img.src}
          src={img.src}
          alt={img.alt}
          className={cn(
            "absolute inset-0 h-full w-full object-cover transition-opacity duration-1000 ease-in-out",
            i === index ? "opacity-100" : "opacity-0",
          )}
        />
      ))}
    </div>
  );
}
