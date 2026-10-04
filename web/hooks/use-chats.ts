"use client";

import { useCallback, useEffect, useState } from "react";
import type { Chat, Message } from "@/lib/types";

const KEY = "kisanmitra.chats.v1";
const MAX_CHATS = 50;

const newId = () => Math.random().toString(36).slice(2, 10);

export function makeMessage(m: Omit<Message, "id">): Message {
  return { id: newId(), ts: Date.now(), ...m };
}

function load(): Chat[] {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as Chat[]) : [];
  } catch {
    return [];
  }
}

function save(chats: Chat[]) {
  try {
    // Audio is large and cheap to regenerate, so it is never persisted.
    const slim = chats.slice(0, MAX_CHATS).map((c) => ({
      ...c,
      messages: c.messages.map((m) => ({ ...m, audioB64: undefined })),
    }));
    localStorage.setItem(KEY, JSON.stringify(slim));
  } catch {
    // storage full / blocked: the app still works, history just isn't kept
  }
}

/** Chat history kept in localStorage. `activeId === null` means "a new, empty chat". */
export function useChats() {
  const [chats, setChats] = useState<Chat[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    // Hydrate from localStorage after mount (it does not exist during server rendering).
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setChats(load());
    setReady(true);
  }, []);

  useEffect(() => {
    if (ready) save(chats);
  }, [chats, ready]);

  const active = chats.find((c) => c.id === activeId) ?? null;

  /** Append a message; creates the chat first if none is active. Returns the chat id. */
  const addMessage = useCallback((chatId: string | null, message: Message): string => {
    const id = chatId ?? newId();
    setChats((prev) => {
      const existing = prev.find((c) => c.id === id);
      if (existing) {
        return prev.map((c) => (c.id === id ? { ...c, messages: [...c.messages, message] } : c));
      }
      const title = message.text.slice(0, 40) || (message.image ? "Crop photo" : "New chat");
      return [{ id, title, createdAt: Date.now(), messages: [message] }, ...prev];
    });
    setActiveId(id);
    return id;
  }, []);

  const deleteChat = useCallback((id: string) => {
    setChats((prev) => prev.filter((c) => c.id !== id));
    setActiveId((cur) => (cur === id ? null : cur));
  }, []);

  const newChat = useCallback(() => setActiveId(null), []);

  return { chats, active, activeId, ready, addMessage, deleteChat, newChat, selectChat: setActiveId };
}
