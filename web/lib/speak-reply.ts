import { play, type Playback } from "./audio";
import { speakWithBrowser } from "./browser-voice";

export type SpokenVia = "server" | "browser" | "none";

/**
 * Say a reply out loud, trying in order:
 *   1. the server's natural voice (audio sent with the reply),
 *   2. the device's built-in voice for that language,
 * and report which one worked ("none" means no sound could be made, so the UI must say so).
 */
export async function speakReply(opts: {
  audioB64?: string | null;
  text: string;
  lang: string;
}): Promise<{ via: SpokenVia; playback: Playback | null }> {
  if (opts.audioB64) {
    const server = play(`data:audio/mpeg;base64,${opts.audioB64}`);
    if (await server.started) return { via: "server", playback: server };
  }
  const local = speakWithBrowser(opts.text, opts.lang);
  if (await local.started) return { via: "browser", playback: local };
  return { via: "none", playback: null };
}
