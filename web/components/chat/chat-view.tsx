"use client";

import { useEffect, useRef } from "react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { AnimatedShinyText } from "@/components/ui/animated-shiny-text";
import type { BotReply, Message } from "@/lib/types";
import { EmptyState } from "./empty-state";
import { MessageView } from "./message";

export function ChatView({
  messages,
  pending,
  onPick,
  onScan,
  onTalk,
  onDetails,
  onUseLocation,
}: {
  messages: Message[];
  pending: boolean;
  onPick: (text: string) => void;
  onScan: () => void;
  onTalk: () => void;
  onDetails: (reply: BotReply) => void;
  onUseLocation: () => void;
}) {
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, pending]);

  if (messages.length === 0 && !pending) return <EmptyState onPick={onPick} onScan={onScan} onTalk={onTalk} />;

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-6">
      {messages.map((m) => (
        <MessageView key={m.id} message={m} onDetails={onDetails} onUseLocation={onUseLocation} />
      ))}
      {pending && (
        <div className="flex items-center gap-3" role="status" aria-live="polite">
          <Avatar>
            <AvatarFallback>🌾</AvatarFallback>
          </Avatar>
          <AnimatedShinyText className="text-sm">Thinking…</AnimatedShinyText>
        </div>
      )}
      <div ref={bottom} />
    </div>
  );
}
