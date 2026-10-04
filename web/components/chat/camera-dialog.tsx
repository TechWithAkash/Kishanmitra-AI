"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Camera, Check, RefreshCw, RotateCcw, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

type Facing = "environment" | "user";

function explain(e: unknown): string {
  if (e instanceof DOMException) {
    if (e.name === "NotAllowedError") return "Camera permission is blocked. Allow it in your browser's address bar, or upload a photo instead.";
    if (e.name === "NotFoundError") return "No camera found on this device. Please upload a photo instead.";
    if (e.name === "NotReadableError") return "The camera is being used by another app. Close it and try again.";
  }
  return "Could not open the camera. Please upload a photo instead.";
}

function CameraSession({ onCapture, onClose }: { onCapture: (b: Blob) => void; onClose: () => void }) {
  const video = useRef<HTMLVideoElement>(null);
  const [facing, setFacing] = useState<Facing>("environment");
  const [error, setError] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [shot, setShot] = useState<{ blob: Blob; url: string } | null>(null);

  useEffect(() => {
    let stream: MediaStream | null = null;
    let cancelled = false;
    (async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: facing }, width: { ideal: 1920 }, height: { ideal: 1080 } },
          audio: false,
        });
        if (cancelled) return stream.getTracks().forEach((t) => t.stop());
        if (video.current) {
          video.current.srcObject = stream;
          await video.current.play().catch(() => {});
        }
      } catch (e) {
        if (!cancelled) setError(explain(e));
      }
    })();
    return () => {
      cancelled = true;
      stream?.getTracks().forEach((t) => t.stop());
      setReady(false);
    };
  }, [facing]);

  useEffect(() => {
    return () => {
      if (shot) URL.revokeObjectURL(shot.url);
    };
  }, [shot]);

  const snap = useCallback(() => {
    const v = video.current;
    if (!v || !v.videoWidth) return;
    const canvas = document.createElement("canvas");
    canvas.width = v.videoWidth;
    canvas.height = v.videoHeight;
    canvas.getContext("2d")!.drawImage(v, 0, 0);
    canvas.toBlob(
      (blob) => blob && setShot({ blob, url: URL.createObjectURL(blob) }),
      "image/jpeg",
      0.92,
    );
  }, []);

  return (
    <div className="relative flex h-full flex-col bg-black">
      <div className="relative min-h-0 flex-1 overflow-hidden">
        {error ? (
          <div className="flex h-full items-center justify-center p-8 text-center text-sm text-white/80">{error}</div>
        ) : (
          <>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            {shot && <img src={shot.url} alt="Captured crop photo" className="absolute inset-0 size-full object-cover" />}
            <video
              ref={video}
              playsInline
              muted
              onPlaying={() => setReady(true)}
              className={cn("size-full object-cover", facing === "user" && "-scale-x-100", shot && "invisible")}
            />
            {/* framing guide */}
            {!shot && (
              <div className="pointer-events-none absolute inset-6 flex flex-col items-center justify-end">
                <div className="absolute inset-0 rounded-2xl border-2 border-dashed border-white/40" />
                <p className="relative mb-3 rounded-full bg-black/55 px-3 py-1 text-xs text-white">
                  Fill the frame with one affected leaf, in daylight
                </p>
              </div>
            )}
          </>
        )}
      </div>

      <div className="flex items-center justify-center gap-6 bg-black/90 px-6 py-4">
        {shot ? (
          <>
            <Button variant="secondary" onClick={() => setShot(null)}>
              <RotateCcw /> Retake
            </Button>
            <Button onClick={() => onCapture(shot.blob)}>
              <Check /> Use photo
            </Button>
          </>
        ) : (
          <>
            <Button variant="ghost" size="icon-lg" className="text-white hover:bg-white/15 hover:text-white" onClick={onClose} aria-label="Close camera">
              <X />
            </Button>
            <button
              type="button"
              onClick={snap}
              disabled={!ready || !!error}
              aria-label="Take photo"
              className="grid size-16 place-items-center rounded-full border-4 border-white outline-none transition-transform focus-visible:ring-4 focus-visible:ring-white/50 enabled:active:scale-90 disabled:opacity-40"
            >
              <span className="size-12 rounded-full bg-white" />
            </button>
            <Button
              variant="ghost"
              size="icon-lg"
              className="text-white hover:bg-white/15 hover:text-white"
              onClick={() => setFacing((f) => (f === "environment" ? "user" : "environment"))}
              aria-label="Switch camera"
            >
              <RefreshCw />
            </Button>
          </>
        )}
      </div>
    </div>
  );
}

export function CameraDialog({
  open,
  onOpenChange,
  onCapture,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCapture: (blob: Blob) => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        showCloseButton={false}
        className="h-[min(720px,92dvh)] gap-0 overflow-hidden rounded-2xl p-0 sm:max-w-lg"
      >
        <DialogTitle className="sr-only">
          <Camera /> Take a photo of your crop
        </DialogTitle>
        <DialogDescription className="sr-only">Point the camera at the affected leaf and press the shutter button.</DialogDescription>
        <CameraSession
          onClose={() => onOpenChange(false)}
          onCapture={(b) => {
            onCapture(b);
            onOpenChange(false);
          }}
        />
      </DialogContent>
    </Dialog>
  );
}
