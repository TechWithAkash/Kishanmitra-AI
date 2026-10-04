"use client";

import { useEffect, useRef, useState } from "react";
import { ImagePlus } from "lucide-react";
import { toast } from "sonner";
import { AppSidebar } from "@/components/app-sidebar";
import { CameraDialog } from "@/components/chat/camera-dialog";
import { ChatView } from "@/components/chat/chat-view";
import { Composer } from "@/components/chat/composer";
import { NlpDetailsSheet } from "@/components/chat/nlp-details-sheet";
import { TopBar } from "@/components/top-bar";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { VoiceMode, type VoiceTurn } from "@/components/voice/voice-mode";
import { useAttachment } from "@/hooks/use-attachment";
import { usePlace } from "@/hooks/use-place";
import { makeMessage, useChats } from "@/hooks/use-chats";
import { useLatest } from "@/hooks/use-latest";
import { useLocalState } from "@/hooks/use-local-state";
import * as api from "@/lib/api";
import type { BotReply, ChatContext, Place } from "@/lib/types";

const GEO_PROMPTED_KEY = "kisanmitra.geo-prompted";

export default function Home() {
  const { chats, active, activeId, addMessage, deleteChat, newChat, selectChat } = useChats();
  const [langPref, setLangPref] = useLocalState("kisanmitra.lang", "auto");
  const { place, setPlace, detect, locating } = usePlace();
  const [pending, setPending] = useState(false);
  const [details, setDetails] = useState<BotReply | null>(null);
  const [voiceOpen, setVoiceOpen] = useState(false);
  const [cameraOpen, setCameraOpen] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [photoCrop, setPhotoCrop] = useState("any");
  const { attachment, busy: attaching, attach, clear: clearAttachment } = useAttachment();

  const uploadInput = useRef<HTMLInputElement>(null);
  const cameraInput = useRef<HTMLInputElement>(null);

  // Handlers run inside long-lived async loops (voice mode), so read the latest values via refs.
  const activeIdRef = useLatest(activeId);
  const settings = useLatest({ langPref, place });
  const activeChat = useLatest(active);
  const attachmentRef = useLatest(attachment);
  const photoCropRef = useLatest(photoCrop);

  // First visit: offer to use the current location (the browser itself asks for permission after the tap).
  useEffect(() => {
    try {
      if (localStorage.getItem(GEO_PROMPTED_KEY) || localStorage.getItem("kisanmitra.place")) return;
      localStorage.setItem(GEO_PROMPTED_KEY, "1");
    } catch {
      return;
    }
    toast("Get weather and prices for your village", {
      description: "Share your location so answers are for where you farm.",
      action: { label: "Use my location", onClick: () => void detect() },
      duration: 15000,
    });
  }, [detect]);

  /** What the last answer was about, so a short follow-up like "aur Pune me?" is understood. */
  function followUpContext(): ChatContext | null {
    const last = [...(activeChat.current?.messages ?? [])].reverse().find((m) => m.reply);
    const r = last?.reply;
    return r && (r.intent === "weather" || r.intent === "market_price")
      ? { intent: r.intent, crop: r.entities.crop }
      : null;
  }

  function takePhoto() {
    // Live camera needs a secure context (https or localhost); otherwise fall back to the phone's camera app.
    const devices = navigator.mediaDevices as MediaDevices | undefined; // undefined on insecure (http, non-localhost) pages
    if (devices?.getUserMedia) setCameraOpen(true);
    else cameraInput.current?.click();
  }

  function onFilePicked(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = ""; // allow picking the same file again
    if (file) void attach(file);
  }

  async function send(text: string, opts: { place?: Place; repeat?: boolean } = {}) {
    const t = text.trim();
    const image = opts.repeat ? null : attachmentRef.current;
    if ((!t && !image) || pending) return;

    // `repeat`: re-asking a question after the location was set. The question is already in the chat.
    const chatId = opts.repeat
      ? (activeIdRef.current as string)
      : addMessage(activeIdRef.current, makeMessage({ role: "user", text: t, image: image?.thumb }));
    activeIdRef.current = chatId;
    const crop = photoCropRef.current;
    clearAttachment();
    setPhotoCrop("any");
    setPending(true);
    try {
      const { langPref: lang, place: saved } = settings.current;
      const where = opts.place ?? saved;
      const reply = image
        ? await api.diagnose(image.blob, lang, where?.name ?? null, t || undefined, crop)
        : await api.chat(t, lang, where, followUpContext());
      addMessage(chatId, makeMessage({ role: "assistant", text: reply.text, reply }));
    } catch (e) {
      addMessage(
        chatId,
        makeMessage({ role: "assistant", text: e instanceof Error ? e.message : "Something went wrong.", error: true }),
      );
    } finally {
      setPending(false);
    }
  }

  /** "Use my current location" under a "which town?" answer: locate, then answer the same question. */
  async function locateAndRetry() {
    const found = await detect();
    if (!found) return;
    const lastQuestion = [...(activeChat.current?.messages ?? [])].reverse().find((m) => m.role === "user" && m.text);
    if (lastQuestion) await send(lastQuestion.text, { place: found, repeat: true });
  }

  async function voiceTurn(blob: Blob): Promise<VoiceTurn | null> {
    try {
      const res = await api.voice(blob, settings.current.langPref, settings.current.place, followUpContext());
      if ("reply" in res) {
        // backend heard no words
        toast.info("I couldn't make out any words. Please try again.");
        return null;
      }
      const { transcript, audio_b64, ...reply } = res;
      const chatId = addMessage(activeIdRef.current, makeMessage({ role: "user", text: transcript, voice: true }));
      activeIdRef.current = chatId;
      addMessage(chatId, makeMessage({ role: "assistant", text: reply.text, reply, audioB64: audio_b64 }));
      return { transcript, text: reply.text, audioB64: audio_b64, lang: reply.lang };
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Voice request failed");
      return null;
    }
  }

  return (
    <SidebarProvider>
      <AppSidebar chats={chats} activeId={activeId} onSelect={selectChat} onNew={newChat} onDelete={deleteChat} />
      <SidebarInset
        className="relative h-dvh overflow-hidden"
        onDragOver={(e) => {
          if (e.dataTransfer.types.includes("Files")) {
            e.preventDefault();
            setDragging(true);
          }
        }}
        onDragLeave={(e) => e.currentTarget === e.target && setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          const file = Array.from(e.dataTransfer.files).find((f) => f.type.startsWith("image/"));
          if (file) void attach(file);
          else if (e.dataTransfer.files.length) toast.info("Please drop an image file.");
        }}
      >
        <TopBar
          langPref={langPref}
          onLangChange={setLangPref}
          place={place}
          onPlaceChange={setPlace}
          onDetect={detect}
          locating={locating}
        />
        <main className="min-h-0 flex-1 overflow-y-auto">
          <ChatView
            messages={active?.messages ?? []}
            pending={pending}
            onPick={send}
            onScan={takePhoto}
            onTalk={() => setVoiceOpen(true)}
            onDetails={setDetails}
            onUseLocation={() => void locateAndRetry()}
          />
        </main>
        <Composer
          onSend={send}
          onOpenVoice={() => setVoiceOpen(true)}
          onTakePhoto={takePhoto}
          onUploadPhoto={() => uploadInput.current?.click()}
          onAttachFile={(f) => void attach(f)}
          attachment={attachment}
          attaching={attaching}
          onRemoveAttachment={clearAttachment}
          crop={photoCrop}
          onCropChange={setPhotoCrop}
          disabled={pending}
        />

        {dragging && (
          <div className="pointer-events-none absolute inset-0 z-40 grid place-items-center bg-background/80 backdrop-blur-sm">
            <div className="flex flex-col items-center gap-2 rounded-2xl border-2 border-dashed border-primary px-10 py-8 text-primary">
              <ImagePlus className="size-8" />
              <p className="font-medium">Drop your crop photo here</p>
            </div>
          </div>
        )}
      </SidebarInset>

      {/* hidden pickers: gallery, and the phone's own camera app as a fallback */}
      <input ref={uploadInput} type="file" accept="image/*" className="hidden" onChange={onFilePicked} data-testid="upload-input" />
      <input ref={cameraInput} type="file" accept="image/*" capture="environment" className="hidden" onChange={onFilePicked} />

      <CameraDialog open={cameraOpen} onOpenChange={setCameraOpen} onCapture={(b) => void attach(b)} />
      <NlpDetailsSheet reply={details} onClose={() => setDetails(null)} />
      <VoiceMode open={voiceOpen} onClose={() => setVoiceOpen(false)} langPref={langPref} onTurn={voiceTurn} />
    </SidebarProvider>
  );
}
