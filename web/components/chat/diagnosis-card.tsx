"use client";

import { useEffect } from "react";
import confetti from "canvas-confetti";
import { CircleCheck, Info, Leaf, ShieldAlert, Sparkles, TriangleAlert } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AnimatedCircularProgressBar } from "@/components/ui/animated-circular-progress-bar";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import type { BotReply } from "@/lib/types";

type Vision = NonNullable<BotReply["details"]["vision"]>;

const STATUS = {
  confident: { label: "Confident", color: "#16a34a", variant: "default" as const },
  possible: { label: "Possible", color: "#d97706", variant: "secondary" as const },
  unsure: { label: "Not sure", color: "#71717a", variant: "outline" as const },
  unsupported: { label: "Not supported", color: "#71717a", variant: "outline" as const },
};

const CONFIDENCE_LABEL = { high: "High confidence", medium: "Medium confidence", low: "Low confidence" };
const PART_LABEL: Record<string, string> = {
  leaf: "leaf", fruit: "fruit", stem: "stem", root: "root", flower: "flower",
  whole_plant: "whole plant", field: "field", other: "plant", not_a_plant: "not a plant",
};
const CATEGORY_LABEL: Record<string, string> = {
  fungal: "Fungal", bacterial: "Bacterial", viral: "Virus", pest: "Pest", nutrient_deficiency: "Nutrient deficiency",
  water_stress: "Water stress", heat_or_sun_damage: "Heat / sun damage", physical_damage: "Physical damage", weed: "Weed", other: "Other",
};

const FRESH_MS = 6000;

/** Celebrate a healthy crop, but only when the answer has just arrived (not when reloading history). */
function useHealthyConfetti(healthy: boolean, createdAt?: number) {
  useEffect(() => {
    if (!healthy || createdAt === undefined || Date.now() - createdAt > FRESH_MS) return;
    confetti({ particleCount: 90, spread: 70, origin: { y: 0.7 }, colors: ["#16a34a", "#84cc16", "#f59e0b"] });
  }, [healthy, createdAt]);
}

/** Result from an AI vision model: any crop, any plant part. */
function AiCard({ vision, createdAt }: { vision: Vision; createdAt?: number }) {
  const confidence = vision.confidence_label ?? "low";
  const healthy = !!vision.healthy && confidence === "high";
  useHealthyConfetti(healthy, createdAt);
  const part = vision.part ? PART_LABEL[vision.part] : null;
  const title = vision.healthy ? "Looks healthy" : (vision.problem ?? "Not clear from this photo");

  return (
    <Card size="sm" className="w-full max-w-md">
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center gap-2">
          {healthy ? <CircleCheck className="size-4 text-primary" /> : <Leaf className="size-4 text-primary" />}
          Photo check
          <Badge variant={confidence === "high" ? "default" : confidence === "medium" ? "secondary" : "outline"}>
            {CONFIDENCE_LABEL[confidence]}
          </Badge>
          <Badge variant="outline" className="gap-1 font-normal">
            <Sparkles className="size-3" /> AI
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <div>
          <p className="text-xs text-muted-foreground capitalize">
            {[vision.plant, part].filter(Boolean).join(" · ") || "Plant not identified"}
          </p>
          <p className="text-lg leading-snug font-semibold">{title}</p>
          {vision.category && !vision.healthy && (
            <Badge variant="secondary" className="mt-1.5 font-normal">
              {CATEGORY_LABEL[vision.category] ?? vision.category}
            </Badge>
          )}
        </div>

        {vision.symptoms && vision.symptoms.length > 0 && (
          <div>
            <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">What I can see</p>
            <ul className="list-disc space-y-0.5 pl-5 text-sm">
              {vision.symptoms.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
          </div>
        )}

        {vision.see_expert || confidence !== "high" ? (
          <Alert>
            <ShieldAlert />
            <AlertDescription>
              Please confirm with an expert before spraying anything: Kisan Call Centre 1800-180-1551 (free) or your
              nearest Krishi Vigyan Kendra.
            </AlertDescription>
          </Alert>
        ) : (
          <Alert>
            <Info />
            <AlertDescription>AI can make mistakes. If the problem spreads, ask an expert.</AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}

/** Result from the basic on-device leaf model (used when no AI key is set or the AI is unavailable). */
function LeafModelCard({ vision, createdAt }: { vision: Vision; createdAt?: number }) {
  const [top, ...others] = vision.predictions;
  const s = STATUS[vision.status];
  const healthy = vision.status === "confident" && !!top?.healthy;
  useHealthyConfetti(healthy, createdAt);

  if (!top) {
    return (
      <Alert className="max-w-md">
        <Info />
        <AlertDescription>
          This basic photo check only understands single leaves of a few crops. Describe the problem in words (for
          example “yellow leaves”) and I will help from there.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <Card size="sm" className="w-full max-w-md">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {healthy ? <CircleCheck className="size-4 text-primary" /> : <Leaf className="size-4 text-primary" />}
          Photo check
          <Badge variant={s.variant}>{s.label}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex items-center gap-4">
          <AnimatedCircularProgressBar
            value={Math.round(top.confidence * 100)}
            gaugePrimaryColor={s.color}
            gaugeSecondaryColor="rgba(120,120,120,0.2)"
            className="size-20 text-lg"
          />
          <div className="min-w-0">
            <p className="text-sm text-muted-foreground">{vision.status === "unsure" ? "Best guess" : "Looks like"}</p>
            <p className="font-medium leading-snug">{top.label}</p>
          </div>
        </div>

        {others.length > 0 && (
          <div className="flex flex-col gap-2">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Other possibilities</p>
            {others.map((p) => (
              <div key={p.label} className="flex items-center gap-3 text-sm">
                <span className="min-w-0 flex-1 truncate">{p.label}</span>
                <Progress value={p.confidence * 100} className="w-20" aria-label={`${p.label} ${Math.round(p.confidence * 100)}%`} />
                <span className="w-9 text-right tabular-nums text-muted-foreground">{Math.round(p.confidence * 100)}%</span>
              </div>
            ))}
          </div>
        )}

        <Alert>
          {vision.status === "unsure" ? <TriangleAlert /> : <Info />}
          <AlertDescription>
            {vision.status === "unsure"
              ? "This basic check only understands single leaves. Try a close-up of one affected leaf, or describe the problem in words."
              : "A photo check can be wrong. Confirm with the Kisan Call Centre (1800-180-1551) before spraying."}
          </AlertDescription>
        </Alert>
      </CardContent>
    </Card>
  );
}

export function DiagnosisCard({ vision, createdAt }: { vision: Vision; createdAt?: number }) {
  return vision.engine ? <AiCard vision={vision} createdAt={createdAt} /> : <LeafModelCard vision={vision} createdAt={createdAt} />;
}
