"use client";

import { motion, useSpring, useTransform, type MotionValue } from "motion/react";
import type { VoicePhase } from "./voice-orb";

const BARS = 29;
// Bell-shaped envelope with a little irregularity, so the bars look like a voice waveform.
const WEIGHTS = Array.from({ length: BARS }, (_, i) => {
  const x = (i - (BARS - 1) / 2) / ((BARS - 1) / 2);
  return Math.exp(-x * x * 2.4) * (0.65 + 0.35 * Math.abs(Math.sin(i * 1.9)));
});

function Bar({ index, weight, phase, level }: { index: number; weight: number; phase: VoicePhase; level: MotionValue<number> }) {
  const live = useSpring(useTransform(level, [0, 1], [0.1, 0.1 + 0.9 * weight]), { stiffness: 260, damping: 20 });

  const animated =
    phase === "speaking"
      ? { scaleY: [0.2, 0.25 + weight, 0.2 + weight * 0.4, 0.3 + weight * 0.9, 0.2] }
      : phase === "thinking"
        ? { scaleY: [0.12, 0.12 + weight * 0.5, 0.12] }
        : { scaleY: 0.1 };

  return (
    <motion.span
      aria-hidden
      className="h-14 w-1 origin-center rounded-full bg-current"
      style={phase === "listening" ? { scaleY: live } : undefined}
      animate={phase === "listening" ? undefined : animated}
      transition={
        phase === "speaking"
          ? { duration: 0.9 + (index % 5) * 0.08, repeat: Infinity, ease: "easeInOut", delay: index * 0.03 }
          : phase === "thinking"
            ? { duration: 1.2, repeat: Infinity, ease: "easeInOut", delay: index * 0.045 }
            : { duration: 0.4 }
      }
    />
  );
}

/** Audio-reactive bars: follow the microphone while listening, animate on their own while speaking. */
export function LevelBars({ phase, level }: { phase: VoicePhase; level: MotionValue<number> }) {
  return (
    <div className="flex h-14 items-center justify-center gap-[3px] text-current transition-colors duration-500" role="presentation">
      {WEIGHTS.map((w, i) => (
        <Bar key={i} index={i} weight={w} phase={phase} level={level} />
      ))}
    </div>
  );
}
