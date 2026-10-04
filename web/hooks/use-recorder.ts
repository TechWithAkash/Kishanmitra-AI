"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useLatest } from "./use-latest";

export type RecorderResult = {
  /** null when no speech was detected (silence / noise only). */
  blob: Blob | null;
  heardSpeech: boolean;
};

type Options = {
  /** Stop automatically after this much silence once the person has spoken. */
  silenceMs?: number;
  /** Give up if nothing is said within this time. */
  noSpeechMs?: number;
  /** Hard cap on one recording. */
  maxMs?: number;
  /** Called every animation frame with the mic volume (0..1) — drives the orb. */
  onLevel?: (level: number) => void;
};

const MIME_TYPES = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"];

function pickMimeType(): string | undefined {
  if (typeof MediaRecorder === "undefined") return undefined;
  return MIME_TYPES.find((t) => MediaRecorder.isTypeSupported(t));
}

/**
 * Microphone recorder with automatic end-of-speech detection.
 * The silence threshold adapts to the background noise measured in the first
 * moments of recording, so it also works outdoors / in noisy rooms.
 */
export function useRecorder({ silenceMs = 1300, noSpeechMs = 10000, maxMs = 30000, onLevel }: Options = {}) {
  const [recording, setRecording] = useState(false);
  const onLevelRef = useLatest(onLevel);

  const session = useRef<{ stop: (discard: boolean) => void } | null>(null);

  const stop = useCallback(() => session.current?.stop(false), []);
  const cancel = useCallback(() => session.current?.stop(true), []);

  /** Starts recording; resolves when recording ends (auto-stop, stop(), or cancel()). */
  const start = useCallback(async (): Promise<RecorderResult> => {
    if (session.current) session.current.stop(true);

    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    });
    const mimeType = pickMimeType();
    const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
    const chunks: Blob[] = [];
    recorder.ondataavailable = (e) => e.data.size > 0 && chunks.push(e.data);

    const ctx = new AudioContext();
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 1024;
    ctx.createMediaStreamSource(stream).connect(analyser);
    const buf = new Float32Array(analyser.fftSize);

    return new Promise<RecorderResult>((resolve) => {
      const startedAt = performance.now();
      let raf = 0;
      let discarded = false;
      let finished = false;
      let heardSpeech = false;
      let speechSince = 0;
      let lastLoud = 0;
      let noise = 0;
      let noiseFrames = 0;
      let smooth = 0;

      const finish = (discard: boolean) => {
        if (finished) return;
        finished = true;
        discarded = discard;
        cancelAnimationFrame(raf);
        if (recorder.state !== "inactive") recorder.stop();
        else cleanup();
      };

      const cleanup = () => {
        stream.getTracks().forEach((t) => t.stop());
        ctx.close().catch(() => {});
        onLevelRef.current?.(0);
        session.current = null;
        setRecording(false);
        const blob = !discarded && heardSpeech && chunks.length
          ? new Blob(chunks, { type: recorder.mimeType || mimeType || "audio/webm" })
          : null;
        resolve({ blob, heardSpeech: heardSpeech && !discarded });
      };

      recorder.onstop = cleanup;

      const tick = () => {
        analyser.getFloatTimeDomainData(buf);
        let sum = 0;
        for (let i = 0; i < buf.length; i++) sum += buf[i] * buf[i];
        const rms = Math.sqrt(sum / buf.length);
        const now = performance.now();
        const elapsed = now - startedAt;

        // Calibrate the noise floor during the first 400 ms.
        if (elapsed < 400) {
          noise += rms;
          noiseFrames++;
        }
        const floor = noiseFrames ? noise / noiseFrames : 0;
        const threshold = Math.max(0.015, floor * 2.5);

        smooth = smooth * 0.7 + rms * 0.3;
        onLevelRef.current?.(Math.min(1, smooth * 8));

        if (elapsed >= 400) {
          if (rms > threshold) {
            lastLoud = now;
            if (!speechSince) speechSince = now;
            if (now - speechSince > 150) heardSpeech = true; // ignore clicks/pops
          } else if (now - lastLoud > 120) {
            speechSince = 0;
          }
          if (heardSpeech && now - lastLoud > silenceMs) return finish(false);
          if (!heardSpeech && elapsed > noSpeechMs) return finish(false);
        }
        if (elapsed > maxMs) return finish(false);
        raf = requestAnimationFrame(tick);
      };

      session.current = { stop: finish };
      recorder.start(250);
      setRecording(true);
      raf = requestAnimationFrame(tick);
    });
  }, [silenceMs, noSpeechMs, maxMs, onLevelRef]);

  useEffect(() => () => session.current?.stop(true), []);

  return { recording, start, stop, cancel };
}
