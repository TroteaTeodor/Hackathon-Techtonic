"use client";

import { MeshGradient } from "@paper-design/shaders-react";
import { useState } from "react";

/** Slow, living gradient in the brand's navy and cyan. Still for reduced motion. */
export function FluidBackdrop({ photo, calm = false }: { photo?: string; calm?: boolean }) {
  const [reduced] = useState(
    () => typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
      <MeshGradient
        colors={calm ? ["#041833", "#06224a", "#0b3a73", "#1a6fa8", "#06224a"] : ["#041833", "#0b3a73", "#1fb6e8", "#06224a", "#3d6194"]}
        distortion={calm ? 0.7 : 0.85}
        swirl={calm ? 0.25 : 0.35}
        grainOverlay={0.05}
        speed={reduced ? 0 : calm ? 0.14 : 0.22}
        style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}
      />
      {photo && (
        <div
          className="absolute inset-0 bg-cover bg-center opacity-25 mix-blend-soft-light"
          style={{ backgroundImage: `url(${photo})` }}
        />
      )}
      <div className="absolute inset-0 bg-gradient-to-t from-navy-950/85 via-navy-950/20 to-transparent" />
    </div>
  );
}
