let current: HTMLAudioElement | null = null;

export type Playback = { done: Promise<void>; stop: () => void };

/** Play audio from a URL / data URI. Only one clip plays at a time. */
export function play(src: string): Playback {
  current?.pause();
  const audio = new Audio(src);
  current = audio;

  let finish!: () => void;
  const done = new Promise<void>((resolve) => (finish = resolve));
  const end = () => {
    if (current === audio) current = null;
    finish();
  };
  audio.onended = end;
  audio.onerror = end;
  audio.play().catch(end); // autoplay blocked or decode error: just move on

  return {
    done,
    stop: () => {
      audio.pause();
      end();
    },
  };
}

export function stopAudio() {
  current?.pause();
  current = null;
}
