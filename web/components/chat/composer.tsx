"use client";

import { useRef, useState } from "react";
import { ArrowUp, Camera, ImagePlus, Loader2, Mic, Plus, X } from "lucide-react";
import { IconButton } from "@/components/icon-button";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { PHOTO_CROPS } from "@/lib/crops";
import type { PreparedImage } from "@/lib/image";

export function Composer({
  onSend,
  onOpenVoice,
  onTakePhoto,
  onUploadPhoto,
  onAttachFile,
  attachment,
  attaching,
  onRemoveAttachment,
  crop,
  onCropChange,
  disabled,
}: {
  onSend: (text: string) => void;
  onOpenVoice: () => void;
  onTakePhoto: () => void;
  onUploadPhoto: () => void;
  onAttachFile: (file: File) => void;
  attachment: PreparedImage | null;
  attaching: boolean;
  onRemoveAttachment: () => void;
  crop: string;
  onCropChange: (crop: string) => void;
  disabled: boolean;
}) {
  const [text, setText] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);
  const canSend = (text.trim().length > 0 || attachment !== null) && !disabled;

  const grow = () => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  };

  const submit = () => {
    if (!canSend) return;
    onSend(text);
    setText("");
    requestAnimationFrame(grow);
  };

  return (
    <div className="mx-auto w-full max-w-3xl px-4 pb-4">
      <div className="rounded-3xl border bg-card p-2 shadow-sm focus-within:ring-3 focus-within:ring-ring/30">
        {(attachment || attaching) && (
          <div className="flex items-end gap-3 px-2 pt-1 pb-2">
            <div className="relative inline-block">
              {attachment ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={attachment.previewUrl} alt="Your crop photo" className="size-20 rounded-xl border object-cover" />
              ) : (
                <div className="grid size-20 place-items-center rounded-xl border bg-muted">
                  <Loader2 className="animate-spin text-muted-foreground" />
                </div>
              )}
              {attachment && (
                <Button
                  size="icon-xs"
                  variant="secondary"
                  className="absolute -top-2 -right-2 rounded-full shadow"
                  onClick={onRemoveAttachment}
                  aria-label="Remove photo"
                >
                  <X />
                </Button>
              )}
            </div>
            {attachment && (
              <div className="flex flex-col gap-1">
                <span className="text-xs text-muted-foreground">Which crop is this? (helps accuracy)</span>
                <Select value={crop} onValueChange={(v) => v && onCropChange(v)}>
                  <SelectTrigger size="sm" aria-label="Crop in the photo" className="w-44">
                    <SelectValue>{(v: string) => PHOTO_CROPS.find((c) => c.value === v)?.label ?? v}</SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    {PHOTO_CROPS.map((c) => (
                      <SelectItem key={c.value} value={c.value}>
                        {c.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
          </div>
        )}

        <div className="flex items-end gap-1">
          <DropdownMenu>
            <DropdownMenuTrigger
              render={<Button variant="ghost" size="icon" className="rounded-full" aria-label="Add a photo of your crop" />}
            >
              <Plus />
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" side="top">
              <DropdownMenuItem onClick={onTakePhoto}>
                <Camera /> Take a photo
              </DropdownMenuItem>
              <DropdownMenuItem onClick={onUploadPhoto}>
                <ImagePlus /> Upload a photo
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          <Textarea
            ref={ref}
            value={text}
            rows={1}
            onChange={(e) => {
              setText(e.target.value);
              grow();
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault();
                submit();
              }
            }}
            onPaste={(e) => {
              const file = Array.from(e.clipboardData.files).find((f) => f.type.startsWith("image/"));
              if (file) {
                e.preventDefault();
                onAttachFile(file);
              }
            }}
            placeholder={attachment ? "Add a note about the photo (optional)…" : "Ask anything… / कुछ भी पूछें…"}
            aria-label="Your question"
            className="max-h-[200px] min-h-9 resize-none border-0 bg-transparent px-2 py-2 shadow-none focus-visible:ring-0 dark:bg-transparent"
          />

          <IconButton label="Talk to KisanMitra" onClick={onOpenVoice} className="rounded-full text-primary">
            <Mic />
          </IconButton>
          <Button
            size="icon"
            className="rounded-full"
            onClick={submit}
            disabled={!canSend}
            aria-label="Send"
          >
            <ArrowUp />
          </Button>
        </div>
      </div>
      <p className="mt-2 text-center text-xs text-muted-foreground">
        KisanMitra can make mistakes. For serious crop problems call the Kisan Call Centre: 1800-180-1551
      </p>
    </div>
  );
}
