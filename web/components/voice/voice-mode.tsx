"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Mic, MicOff, Volume2, VolumeX, X } from "lucide-react";
import { AnimatePresence, motion, useMotionValue } from "motion/react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { BlurFade } from "@/components/ui/blur-fade";
import { BorderBeam } from "@/components/ui/border-beam";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Particles } from "@/components/ui/particles";
import { ShimmerButton } from "@/components/ui/shimmer-button";
import { TextAnimate } from "@/components/ui/text-animate";
import { useLatest } from "@/hooks/use-latest";
import { useRecorder } from "@/hooks/use-recorder";
import { type Playback } from "@/lib/audio";
import { speakReply, type SpokenVia } from "@/lib/speak-reply";
import { languageName } from "@/lib/languages";
import { cn } from "@/lib/utils";
import { LevelBars } from "./level-bars";
import { PHASE_STYLE, VoiceOrb, type VoicePhase } from "./voice-orb";

export type VoiceTurn = {
  transcript: string;
  text: string;
  /** Short version meant for speaking (falls back to `text`). */
  spoken: string | null;
  audioB64: string | null;
  lang: string;
};

const PHASE_TEXT: Record<VoicePhase, string> = {
  listening: "Listening…",
  thinking: "Thinking…",
  speaking: "Speaking…",
  paused: "Paused",
};

const PHASE_HINT: Record<VoicePhase, string> = {
  listening: "Speak now. I'll answer when you pause.",
  thinking: "Looking that up for you",
  speaking: "Tap the orb to skip",
  paused: "Tap the orb to talk again",
};

const TRY_SAYING = ["Onion price in Nashik", "Will it rain in Pune tomorrow?", "टमाटर के पत्ते पीले हो रहे हैं"];

const IDLE_ROUNDS_BEFORE_PAUSE = 2;

/**
 * Hands-free voice conversation (like ChatGPT voice):
 * listen → (silence detected) → think → speak the answer → listen again.
 * Mounted only while the dialog is open, so every session starts fresh.
 */
function VoiceSession({
  langPref,
  onTurn,
  onClose,
}: {
  langPref: string;
  onTurn: (blob: Blob) => Promise<VoiceTurn | null>;
  onClose: () => void;
}) {
  const level = useMotionValue(0);
  const [phase, setPhase] = useState<VoicePhase>("listening");
  const [caption, setCaption] = useState<{ user: string; bot: string; lang: string } | null>(null);
  const [voiceVia, setVoiceVia] = useState<SpokenVia | null>(null); // how the last answer was spoken
  const lastTurn = useRef<VoiceTurn | null>(null);

  const recorder = useRecorder({ onLevel: (v) => level.set(v) });
  const cancelRecording = recorder.cancel; // stable identity
  const recorderRef = useLatest(recorder);
  const onTurnRef = useLatest(onTurn);

  const active = useRef(false);
  const paused = useRef(false);
  const looping = useRef(false);
  const resume = useRef<(() => void) | null>(null);
  const playback = useRef<Playback | null>(null);

  const loop = useCallback(async () => {
    if (looping.current) return;
    looping.current = true;
    let silentRounds = 0;
    try {
      while (active.current) {
        if (paused.current) {
          setPhase("paused");
          await new Promise<void>((r) => (resume.current = r));
          silentRounds = 0;
          continue;
        }

        setPhase("listening");
        const { blob } = await recorderRef.current.start();
        if (!active.current) break;
        if (paused.current) continue;

        if (!blob) {
          // Nobody spoke. After a couple of quiet rounds, wait for a tap instead of listening forever.
          if (++silentRounds >= IDLE_ROUNDS_BEFORE_PAUSE) paused.current = true;
          continue;
        }
        silentRounds = 0;

        setPhase("thinking");
        const turn = await onTurnRef.current(blob);
        if (!active.current) break;
        if (!turn) continue;

        setCaption({ user: turn.transcript, bot: turn.text, lang: turn.lang });
        lastTurn.current = turn;
        setPhase("speaking");
        const { via, playback: spoken } = await speakReply({
          audioB64: turn.audioB64,
          text: turn.spoken ?? turn.text,
          lang: turn.lang,
        });
        setVoiceVia(via);
        if (spoken) {
          playback.current = spoken;
          await spoken.done;
          playback.current = null;
        }
      }
    } catch (e) {
      if (active.current) {
        toast.error(
          e instanceof DOMException && e.name === "NotAllowedError"
            ? "Microphone permission is blocked. Allow it in your browser's address bar."
            : "Voice mode stopped: could not use the microphone.",
        );
        onClose();
      }
    } finally {
      looping.current = false;
    }
  }, [onClose, recorderRef, onTurnRef]);

  useEffect(() => {
    active.current = true;
    paused.current = false;
    const start = setTimeout(() => void loop(), 0); // deferred, so React StrictMode's double-mount starts one loop
    return () => {
      clearTimeout(start);
      active.current = false;
      cancelRecording();
      playback.current?.stop();
      resume.current?.();
    };
  }, [loop, cancelRecording]);

  function resumeListening() {
    paused.current = false;
    resume.current?.();
  }

  function onOrbClick() {
    if (phase === "listening") recorder.stop(); // "I'm done talking": send now
    else if (phase === "speaking") playback.current?.stop(); // skip the answer
    else if (phase === "paused") resumeListening();
  }

  /** Tapping the speaker counts as a user gesture, so browsers allow the sound. */
  async function replay() {
    const turn = lastTurn.current;
    if (!turn) return;
    playback.current?.stop();
    const { via, playback: spoken } = await speakReply({ audioB64: turn.audioB64, text: turn.spoken ?? turn.text, lang: turn.lang });
    setVoiceVia(via);
    if (!spoken) {
      toast.error("This device has no voice for this language. Please read the answer on the screen.");
      return;
    }
    playback.current = spoken;
    await spoken.done;
    if (playback.current === spoken) playback.current = null;
  }

  function toggleMute() {
    if (paused.current) return resumeListening();
    paused.current = true;
    recorder.cancel();
    playback.current?.stop();
  }

  const style = PHASE_STYLE[phase];

  return (
    <div className="relative flex h-full flex-col overflow-hidden">
      <Particles className="absolute inset-0" quantity={55} ease={90} size={0.5} color={style.hex} refresh />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-50 transition-[background] duration-700"
        style={{ background: `radial-gradient(60% 38% at 50% 36%, ${style.hex}33 0%, transparent 70%)` }}
      />

      <header className="relative z-10 flex items-center justify-between p-4">
        <Badge variant="secondary">{langPref === "auto" ? "Any language" : languageName(langPref)}</Badge>
        <div className="flex items-center gap-2 text-sm font-medium" role="status" aria-live="polite">
          <span className="relative flex size-2.5">
            <span className={cn("absolute inline-flex size-full animate-ping rounded-full opacity-60", phase === "paused" ? "hidden" : "bg-current", style.text)} />
            <span className={cn("relative inline-flex size-2.5 rounded-full bg-current transition-colors", style.text)} />
          </span>
          {PHASE_TEXT[phase]}
        </div>
        <Button variant="ghost" size="icon-sm" onClick={onClose} aria-label="Close voice mode">
          <X />
        </Button>
      </header>

      <div className="relative z-10 flex flex-1 flex-col items-center justify-center gap-1">
        <BlurFade delay={0.05} duration={0.5}>
          <VoiceOrb phase={phase} level={level} onClick={onOrbClick} label={`${PHASE_TEXT[phase]} ${PHASE_HINT[phase]}`} />
        </BlurFade>
        <div className={cn("transition-colors duration-500", style.text)}>
          <LevelBars phase={phase} level={level} />
        </div>
        <AnimatePresence mode="wait">
          <motion.p
            key={phase}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.2 }}
            className="mt-3 text-sm text-muted-foreground"
          >
            {PHASE_HINT[phase]}
          </motion.p>
        </AnimatePresence>
      </div>

      <div className="relative z-10 flex min-h-32 flex-col items-center justify-start gap-2 px-6 text-center">
        {caption ? (
          <>
            <p className="max-w-full truncate text-sm text-muted-foreground">🎤 {caption.user}</p>
            <div lang={caption.lang}>
              <TextAnimate
                key={caption.bot}
                animation="blurInUp"
                by="word"
                once
                duration={0.9}
                className="line-clamp-4 text-[15px] leading-relaxed"
              >
                {caption.bot.length > 240 ? `${caption.bot.slice(0, 240)}…` : caption.bot}
              </TextAnimate>
            </div>
            {voiceVia === "none" && (
              <p className="flex items-center gap-1.5 text-xs text-amber-600 dark:text-amber-400" role="alert">
                <VolumeX className="size-3.5 shrink-0" />
                Sound could not be played automatically. Tap the speaker to hear the answer.
              </p>
            )}
            {voiceVia === "browser" && (
              <p className="text-xs text-muted-foreground">Spoken with your device&apos;s voice.</p>
            )}
          </>
        ) : (
          <BlurFade delay={0.25} className="flex flex-col items-center gap-2">
            <p className="text-sm text-muted-foreground">Try saying</p>
            <div className="flex flex-wrap justify-center gap-2">
              {TRY_SAYING.map((t) => (
                <Badge key={t} variant="outline" className="font-normal">
                  “{t}”
                </Badge>
              ))}
            </div>
          </BlurFade>
        )}
      </div>

      <footer className="relative z-10 flex items-center justify-center gap-4 p-5">
        {phase === "paused" ? (
          <ShimmerButton onClick={resumeListening} background={style.hex} className="h-12 gap-2 px-6 text-sm font-medium text-white">
            <Mic className="size-4" /> Tap to talk
          </ShimmerButton>
        ) : (
          <Button variant="secondary" size="icon-lg" className="size-12 rounded-full" onClick={toggleMute} aria-label="Mute microphone">
            <MicOff />
          </Button>
        )}
        {caption && (
          <Button variant="secondary" size="icon-lg" className="size-12 rounded-full" onClick={() => void replay()} aria-label="Hear the answer again">
            <Volume2 />
          </Button>
        )}
        <Button variant="destructive" className="h-12 rounded-full px-5" onClick={onClose} aria-label="End voice mode">
          <X /> End
        </Button>
      </footer>

      <BorderBeam size={260} duration={7} borderWidth={2} colorFrom={style.beam[0]} colorTo={style.beam[1]} />
    </div>
  );
}

export function VoiceMode({
  open,
  onClose,
  langPref,
  onTurn,
}: {
  open: boolean;
  onClose: () => void;
  langPref: string;
  /** Sends one recording to the backend and returns what to say, or null if nothing was understood. */
  onTurn: (blob: Blob) => Promise<VoiceTurn | null>;
}) {
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent
        showCloseButton={false}
        className="h-[min(700px,92dvh)] gap-0 overflow-hidden rounded-3xl p-0 shadow-2xl duration-300 sm:max-w-md"
      >
        <DialogTitle className="sr-only">Voice conversation</DialogTitle>
        <DialogDescription className="sr-only">
          Speak your farming question. KisanMitra answers out loud and listens again.
        </DialogDescription>
        <VoiceSession langPref={langPref} onTurn={onTurn} onClose={onClose} />
      </DialogContent>
    </Dialog>
  );
}
