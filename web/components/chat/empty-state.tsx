"use client";

import { Camera, Mic } from "lucide-react";
import { Button } from "@/components/ui/button";
import { BlurFade } from "@/components/ui/blur-fade";
import { AuroraText } from "@/components/ui/aurora-text";
import { LightRays } from "@/components/ui/light-rays";
import { MagicCard } from "@/components/ui/magic-card";
import { MorphingText } from "@/components/ui/morphing-text";
import { ShimmerButton } from "@/components/ui/shimmer-button";
import { GREETINGS, SUGGESTIONS } from "@/lib/languages";

export function EmptyState({
  onPick,
  onScan,
  onTalk,
}: {
  onPick: (text: string) => void;
  onScan: () => void;
  onTalk: () => void;
}) {
  return (
    <div className="relative mx-auto flex min-h-full w-full max-w-2xl flex-col items-center justify-center gap-7 px-4 py-10">
      <LightRays color="rgba(34, 197, 94, 0.18)" count={6} blur={40} speed={16} className="-z-10 fixed" />

      <div className="flex flex-col items-center gap-2 text-center">
        <span className="text-5xl" aria-hidden>
          🌾
        </span>
        <MorphingText texts={GREETINGS} className="h-20 text-6xl text-primary md:h-24 md:text-7xl lg:text-7xl" />
        <h1 className="text-xl font-medium tracking-tight sm:text-2xl">
          How can I help <AuroraText colors={["#16a34a", "#84cc16", "#f59e0b", "#0ea5e9"]}>your farm</AuroraText> today?
        </h1>
        <p className="text-sm text-muted-foreground">Type, talk or send a photo of your crop. Any Indian language works.</p>
      </div>

      <BlurFade delay={0.1} className="flex flex-wrap items-center justify-center gap-3">
        <ShimmerButton onClick={onScan} background="#16a34a" className="h-11 gap-2 px-5 text-sm font-medium text-white">
          <Camera className="size-4" /> Scan a crop leaf
        </ShimmerButton>
        <Button variant="outline" className="h-11 gap-2 rounded-full px-5" onClick={onTalk}>
          <Mic /> Talk in your language
        </Button>
      </BlurFade>

      <div className="grid w-full grid-cols-1 gap-3 sm:grid-cols-2">
        {SUGGESTIONS.map((s, i) => (
          <BlurFade key={s.title} delay={0.15 + i * 0.07} className="h-full">
            <MagicCard className="h-full rounded-xl" gradientColor="rgba(22,163,74,0.14)" gradientFrom="#16a34a" gradientTo="#f59e0b">
              <button
                type="button"
                onClick={() => onPick(s.text)}
                className="flex h-full w-full flex-col gap-1 rounded-xl p-4 text-left outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
              >
                <span className="flex items-center gap-2 text-sm font-medium">
                  <span aria-hidden>{s.icon}</span>
                  {s.title}
                  <span className="ml-auto text-xs font-normal text-muted-foreground">{s.hint}</span>
                </span>
                <span className="text-sm text-muted-foreground">{s.text}</span>
              </button>
            </MagicCard>
          </BlurFade>
        ))}
      </div>
    </div>
  );
}
