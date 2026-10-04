"use client";

import { useEffect } from "react";
import confetti from "canvas-confetti";
import { CircleCheck, Info, Leaf, TriangleAlert } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AnimatedCircularProgressBar } from "@/components/ui/animated-circular-progress-bar";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import type { BotReply } from "@/lib/types";

const STATUS = {
  confident: { label: "Confident", color: "#16a34a", variant: "default" as const },
  possible: { label: "Possible", color: "#d97706", variant: "secondary" as const },
  unsure: { label: "Not sure", color: "#71717a", variant: "outline" as const },
  unsupported: { label: "Not supported", color: "#71717a", variant: "outline" as const },
};

const FRESH_MS = 6000;

export function DiagnosisCard({
  vision,
  createdAt,
}: {
  vision: NonNullable<BotReply["details"]["vision"]>;
  createdAt?: number;
}) {
  const s = STATUS[vision.status];
  const [top, ...others] = vision.predictions;

  const healthy = vision.status === "confident" && !!top?.healthy;

  // Celebrate a healthy crop, but only when the answer has just arrived (not when reloading history).
  useEffect(() => {
    if (!healthy || createdAt === undefined || Date.now() - createdAt > FRESH_MS) return;
    confetti({ particleCount: 90, spread: 70, origin: { y: 0.7 }, colors: ["#16a34a", "#84cc16", "#f59e0b"] });
  }, [healthy, createdAt]);

  if (!top) {
    return (
      <Alert className="max-w-md">
        <Info />
        <AlertDescription>
          The photo check does not cover this crop yet. Describe the problem in words (for example “yellow leaves”)
          and I will help from there.
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

        {vision.status === "unsure" ? (
          <Alert>
            <TriangleAlert />
            <AlertDescription>
              Try again with a clear, close-up photo of one affected leaf in daylight.
            </AlertDescription>
          </Alert>
        ) : (
          <Alert>
            <Info />
            <AlertDescription>
              A photo check can be wrong, especially for field photos with many leaves. Confirm with the Kisan Call
              Centre (1800-180-1551) before spraying.
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}
