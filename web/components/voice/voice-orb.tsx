"use client";

import { motion, useSpring, useTransform, type MotionValue } from "motion/react";
import { cn } from "@/lib/utils";

export type VoicePhase = "listening" | "thinking" | "speaking" | "paused";

export const PHASE_STYLE: Record<VoicePhase, { gradient: string; text: string; hex: string; beam: [string, string] }> = {
  listening: { gradient: "from-emerald-300 to-green-600", text: "text-emerald-500", hex: "#10b981", beam: ["#34d399", "#16a34a"] },
  thinking: { gradient: "from-amber-300 to-orange-500", text: "text-orange-500", hex: "#f59e0b", beam: ["#fbbf24", "#f97316"] },
  speaking: { gradient: "from-sky-300 to-blue-600", text: "text-blue-500", hex: "#0ea5e9", beam: ["#38bdf8", "#2563eb"] },
  paused: { gradient: "from-zinc-300 to-zinc-500 dark:from-zinc-600 dark:to-zinc-800", text: "text-zinc-500", hex: "#a1a1aa", beam: ["#a1a1aa", "#71717a"] },
};

/** The glowing orb. Its size follows the microphone volume while listening. */
export function VoiceOrb({
  phase,
  level,
  onClick,
  label,
}: {
  phase: VoicePhase;
  level: MotionValue<number>;
  onClick: () => void;
  label: string;
}) {
  const scale = useSpring(useTransform(level, [0, 1], [1, 1.4]), { stiffness: 220, damping: 18 });
  const style = PHASE_STYLE[phase];

  return (
    <div className="relative grid size-52 place-items-center">
      {/* soft pulsing halo */}
      <motion.div
        aria-hidden
        className={cn("absolute size-40 rounded-full bg-current opacity-20 blur-2xl transition-colors duration-700", style.text)}
        animate={phase === "paused" ? { scale: 1, opacity: 0.1 } : { scale: [1, 1.25, 1], opacity: [0.18, 0.3, 0.18] }}
        transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.button
        type="button"
        onClick={onClick}
        aria-label={label}
        style={phase === "listening" ? { scale } : undefined}
        animate={
          phase === "thinking"
            ? { scale: [1, 1.07, 1], rotate: [0, 180, 360] }
            : phase === "speaking"
              ? { scale: [1, 1.12, 0.98, 1.08, 1] }
              : { scale: 1 }
        }
        transition={
          phase === "thinking"
            ? { duration: 2.6, repeat: Infinity, ease: "linear" }
            : phase === "speaking"
              ? { duration: 1.5, repeat: Infinity, ease: "easeInOut" }
              : { duration: 0.3 }
        }
        className={cn(
          "relative z-10 size-32 rounded-full bg-gradient-to-br shadow-[0_0_70px_-8px] shadow-current outline-none transition-colors duration-500 focus-visible:ring-4 focus-visible:ring-ring/50",
          style.gradient,
          style.text,
          phase === "paused" && "shadow-none",
        )}
      >
        {/* glossy highlight */}
        <span aria-hidden className="absolute top-3 left-5 h-8 w-14 rotate-[-18deg] rounded-full bg-white/35 blur-md" />
      </motion.button>
    </div>
  );
}
