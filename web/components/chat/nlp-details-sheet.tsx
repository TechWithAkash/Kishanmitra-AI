"use client";

import { Badge } from "@/components/ui/badge";
import { AnimatedCircularProgressBar } from "@/components/ui/animated-circular-progress-bar";
import { Separator } from "@/components/ui/separator";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { INTENT_LABELS, languageName } from "@/lib/languages";
import type { BotReply } from "@/lib/types";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</span>
      {children}
    </div>
  );
}

/** "How did it understand me?" panel: shows each NLP pipeline step for one answer. */
export function NlpDetailsSheet({ reply, onClose }: { reply: BotReply | null; onClose: () => void }) {
  const entities = reply ? Object.entries(reply.entities).filter(([, v]) => v) : [];
  const heard = reply?.details.heard;

  return (
    <Sheet open={reply !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="w-full overflow-y-auto sm:max-w-md">
        <SheetHeader>
          <SheetTitle>How I understood this</SheetTitle>
          <SheetDescription>The NLP pipeline steps behind this answer.</SheetDescription>
        </SheetHeader>
        {reply && (
          <div className="flex flex-col gap-5 px-4 pb-6">
            <Row label="1 · Language detected">
              <div className="flex gap-2">
                <Badge>{languageName(reply.lang)}</Badge>
                {reply.script === "latin" && reply.lang !== "en" && <Badge variant="secondary">romanized</Badge>}
              </div>
            </Row>
            <Separator />
            <Row label="2 · Intent">
              <div className="flex items-center gap-3">
                <Badge variant="secondary">{INTENT_LABELS[reply.intent] ?? reply.intent}</Badge>
                <AnimatedCircularProgressBar
                  value={Math.round(reply.confidence * 100)}
                  gaugePrimaryColor="#16a34a"
                  gaugeSecondaryColor="rgba(120,120,120,0.2)"
                  className="ml-auto size-16 text-sm"
                />
              </div>
            </Row>
            <Separator />
            <Row label="3 · Entities found">
              {entities.length ? (
                <div className="flex flex-wrap gap-2">
                  {entities.map(([k, v]) => (
                    <Badge key={k} variant="outline">
                      {k}: <span className="font-semibold">{v}</span>
                    </Badge>
                  ))}
                </div>
              ) : (
                <span className="text-sm text-muted-foreground">None</span>
              )}
            </Row>
            {reply.details.place && (
              <>
                <Separator />
                <Row label="Place used">
                  <p className="text-sm">
                    <b>{reply.details.place.label}</b>{" "}
                    <span className="text-muted-foreground">
                      ({reply.details.place_from === "question" ? "named in your question" : "your saved location"})
                    </span>
                  </p>
                </Row>
              </>
            )}
            {reply.details.follow_up && (
              <>
                <Separator />
                <Row label="Follow-up">
                  <p className="text-sm text-muted-foreground">Understood as a follow-up to your previous question.</p>
                </Row>
              </>
            )}
            {heard && (
              <>
                <Separator />
                <Row label="Voice">
                  <p className="text-sm">
                    Whisper detected <b>{languageName(heard.lang)}</b>; the words were written by{" "}
                    <b>{heard.engine === "google" ? "Google speech recognition" : "Whisper"}</b>.
                  </p>
                </Row>
              </>
            )}
            {reply.details.nlu_text && reply.lang !== "en" && reply.lang !== "hi" && reply.lang !== "mr" && (
              <>
                <Separator />
                <Row label="Translated for understanding">
                  <p className="text-sm">{reply.details.nlu_text}</p>
                </Row>
              </>
            )}
            <Separator />
            <Row label="Answer in English (before translation)">
              <p className="whitespace-pre-wrap text-sm text-muted-foreground">{reply.english}</p>
            </Row>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}
