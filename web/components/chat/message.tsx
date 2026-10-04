"use client";

import { useRef, useState } from "react";
import { Brain, Check, Copy, Loader2, LocateFixed, Mic, Square, Volume2 } from "lucide-react";
import { toast } from "sonner";
import { IconButton } from "@/components/icon-button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { BlurFade } from "@/components/ui/blur-fade";
import { Lens } from "@/components/ui/lens";
import { tts } from "@/lib/api";
import { play, type Playback } from "@/lib/audio";
import { cn } from "@/lib/utils";
import type { BotReply, Message } from "@/lib/types";
import { DiagnosisCard } from "./diagnosis-card";
import { PriceCard } from "./price-card";
import { WeatherCard } from "./weather-card";

const ENTITY_EMOJI: Record<string, string> = { crop: "🌱", symptom: "🔎", location: "📍" };

function ListenButton({ message }: { message: Message }) {
  const [state, setState] = useState<"idle" | "loading" | "playing">("idle");
  const playback = useRef<Playback | null>(null);
  const reply = message.reply;
  if (!reply) return null;

  async function toggle() {
    if (state === "playing") {
      playback.current?.stop();
      return;
    }
    setState("loading");
    try {
      // Romanized replies sound wrong in a speech engine, so speak the English
      // answer translated into the native script instead.
      const romanized = reply!.script === "latin" && reply!.lang !== "en";
      const blob = romanized ? await tts(reply!.english, reply!.lang, true) : await tts(reply!.text, reply!.lang);
      const url = URL.createObjectURL(blob);
      playback.current = play(url);
      setState("playing");
      await playback.current.done;
      URL.revokeObjectURL(url);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not play audio");
    } finally {
      setState("idle");
    }
  }

  return (
    <IconButton label={state === "playing" ? "Stop" : "Listen"} onClick={toggle} disabled={state === "loading"}>
      {state === "loading" ? <Loader2 className="animate-spin" /> : state === "playing" ? <Square /> : <Volume2 />}
    </IconButton>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <IconButton
      label={copied ? "Copied" : "Copy"}
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        } catch {
          toast.error("Could not copy");
        }
      }}
    >
      {copied ? <Check /> : <Copy />}
    </IconButton>
  );
}

function RichCards({ reply, createdAt }: { reply: BotReply; createdAt?: number }) {
  const { mandi, weather, vision } = reply.details;
  return (
    <>
      {reply.intent === "crop_image" && vision && <DiagnosisCard vision={vision} createdAt={createdAt} />}
      {reply.intent === "market_price" && mandi && mandi.records.length > 0 && (
        <PriceCard mandi={mandi} commodity={mandi.records[0].commodity} />
      )}
      {reply.intent === "weather" && weather && <WeatherCard weather={weather} lang={reply.lang} />}
    </>
  );
}

export function MessageView({
  message,
  onDetails,
  onUseLocation,
}: {
  message: Message;
  onDetails: (r: BotReply) => void;
  onUseLocation: () => void;
}) {
  if (message.role === "user") {
    return (
      <BlurFade duration={0.25} className="flex flex-col items-end gap-2">
        {message.image && (
          <Lens zoomFactor={2.2} lensSize={130}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={message.image} alt="Your crop photo" className="max-h-56 max-w-[260px] rounded-2xl border object-cover" />
          </Lens>
        )}
        {message.text && (
          <div className="max-w-[85%] rounded-3xl rounded-br-md bg-muted px-4 py-2.5 text-[15px] leading-relaxed">
            {message.voice && <Mic className="mr-1.5 mb-0.5 inline size-3.5 text-primary" aria-label="Spoken" />}
            {message.text}
          </div>
        )}
      </BlurFade>
    );
  }

  const reply = message.reply;
  const entities = reply ? Object.entries(reply.entities).filter(([, v]) => v) : [];

  return (
    <BlurFade duration={0.3} className="flex gap-3">
      <Avatar className="mt-0.5">
        <AvatarFallback>🌾</AvatarFallback>
      </Avatar>
      <div className="flex min-w-0 flex-1 flex-col gap-3">
        <p
          className={cn(
            "whitespace-pre-wrap text-[15px] leading-relaxed",
            message.error && "text-destructive",
          )}
        >
          {message.text}
        </p>
        {reply?.details.needs_location && (
          <Button variant="outline" className="w-fit gap-2 rounded-full" onClick={onUseLocation}>
            <LocateFixed className="text-primary" /> Use my current location
          </Button>
        )}
        {reply && <RichCards reply={reply} createdAt={message.ts} />}
        {entities.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {entities.map(([k, v]) => (
              <Badge key={k} variant="secondary" className="font-normal">
                {ENTITY_EMOJI[k]} {v}
              </Badge>
            ))}
          </div>
        )}
        {reply && (
          <div className="-ml-1.5 flex items-center gap-0.5 text-muted-foreground">
            <ListenButton message={message} />
            <CopyButton text={message.text} />
            <IconButton label="How I understood this" onClick={() => onDetails(reply)}>
              <Brain />
            </IconButton>
          </div>
        )}
      </div>
    </BlurFade>
  );
}
