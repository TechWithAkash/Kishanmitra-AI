let current: HTMLAudioElement | null = null;

export type Playback = {
  /** Resolves when playback ends (or fails). */
  done: Promise<void>;
  stop: () => void;
  /** Resolves true once sound is actually playing, false if the browser blocked or could not play it. */
  started: Promise<boolean>;
};

/** Play audio from a URL / data URI. Only one clip plays at a time. Failures are reported, never swallowed. */
export function play(src: string): Playback {
  current?.pause();
  const audio = new Audio(src);
  current = audio;

  let finish!: () => void;
  const done = new Promise<void>((resolve) => (finish = resolve));
  let begin!: (ok: boolean) => void;
  const started = new Promise<boolean>((resolve) => (begin = resolve));

  const end = () => {
    if (current === audio) current = null;
    begin(false); // no-op if it had already started
    finish();
  };
  audio.onplaying = () => begin(true);
  audio.onended = end;
  audio.onerror = () => {
    console.warn("Voice reply could not be decoded/played:", audio.error?.message ?? "unknown error");
    end();
  };
  audio.play().catch((err: unknown) => {
    // Typically NotAllowedError: the browser blocks sound that did not follow a tap.
    console.warn("Voice reply was blocked:", err instanceof Error ? `${err.name}: ${err.message}` : err);
    end();
  });

  return {
    done,
    started,
    stop: () => {
      audio.pause();
      end();
    },
  };
}

export function stopAudio() {
  current?.pause();
  current = null;
  if (typeof speechSynthesis !== "undefined") speechSynthesis.cancel();
}
