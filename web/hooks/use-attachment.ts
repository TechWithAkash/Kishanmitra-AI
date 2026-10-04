"use client";

import { useCallback, useState } from "react";
import { toast } from "sonner";
import { prepareImage, type PreparedImage } from "@/lib/image";

/** The crop photo waiting to be sent with the next message. */
export function useAttachment() {
  const [attachment, setAttachment] = useState<PreparedImage | null>(null);
  const [busy, setBusy] = useState(false);

  const clear = useCallback(() => {
    setAttachment((prev) => {
      if (prev) URL.revokeObjectURL(prev.previewUrl);
      return null;
    });
  }, []);

  const attach = useCallback(async (file: Blob) => {
    setBusy(true);
    try {
      const prepared = await prepareImage(file);
      setAttachment((prev) => {
        if (prev) URL.revokeObjectURL(prev.previewUrl);
        return prepared;
      });
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not use that image");
    } finally {
      setBusy(false);
    }
  }, []);

  return { attachment, busy, attach, clear };
}
