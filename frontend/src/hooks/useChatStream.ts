import { useCallback, useMemo, useRef, useState } from "react";
import type { ChatMessage, RefundInterrupt, StreamPayload } from "../types";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

function createMessageId() {
  return `${Date.now()}-${crypto.randomUUID()}`;
}

function parseSseBuffer(buffer: string) {
  const events = buffer.split("\n\n");
  const remainder = events.pop() ?? "";

  return {
    payloads: events
      .map((event) =>
        event
          .split("\n")
          .filter((line) => line.startsWith("data:"))
          .map((line) => line.slice(5).trimStart())
          .join("\n"),
      )
      .filter(Boolean),
    remainder,
  };
}

async function readSseResponse(
  response: Response,
  onPayload: (payload: string) => void,
) {
  if (!response.body) {
    throw new Error("The chat response did not include a readable stream.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();

    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const parsed = parseSseBuffer(buffer);
    buffer = parsed.remainder;

    for (const payload of parsed.payloads) {
      onPayload(payload);
    }
  }
}

export function useChatStream() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: createMessageId(),
      role: "assistant",
      content:
        "Hi, I am AbhiMart support. Ask about products, policies, orders, or start a refund review.",
    },
  ]);
  const [sessionId] = useState(() => `web-${crypto.randomUUID()}`);
  const [pendingInterrupt, setPendingInterrupt] =
    useState<RefundInterrupt | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const assistantMessageIdRef = useRef<string | null>(null);

  const appendAssistantText = useCallback((text: string) => {
    setMessages((current) =>
      current.map((message) =>
        message.id === assistantMessageIdRef.current
          ? { ...message, content: `${message.content}${text}` }
          : message,
      ),
    );
  }, []);

  const startAssistantMessage = useCallback(() => {
    const assistantMessageId = createMessageId();
    assistantMessageIdRef.current = assistantMessageId;
    setMessages((current) => [
      ...current,
      { id: assistantMessageId, role: "assistant", content: "" },
    ]);
  }, []);

  const handleRawPayload = useCallback(
    (rawPayload: string) => {
      if (rawPayload === "[DONE]") {
        return;
      }

      let payload: StreamPayload;
      try {
        payload = JSON.parse(rawPayload) as StreamPayload;
      } catch {
        appendAssistantText(rawPayload);
        return;
      }

      if ("type" in payload && payload.type === "interrupt") {
        setPendingInterrupt(payload.interrupt);
        return;
      }

      if ("text" in payload) {
        appendAssistantText(payload.text);
      }
    },
    [appendAssistantText],
  );

  const sendMessage = useCallback(
    async (content: string) => {
      const trimmed = content.trim();
      if (!trimmed || isStreaming) {
        return;
      }

      setError(null);
      setPendingInterrupt(null);
      setMessages((current) => [
        ...current,
        { id: createMessageId(), role: "user", content: trimmed },
      ]);
      startAssistantMessage();
      setIsStreaming(true);

      try {
        const response = await fetch(`${API_BASE_URL}/v1/chat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            message: trimmed,
            session_id: sessionId,
          }),
        });

        if (!response.ok) {
          throw new Error(
            `Chat request failed with status ${response.status}.`,
          );
        }

        await readSseResponse(response, handleRawPayload);
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Chat request failed.";
        setError(message);
        appendAssistantText(
          "I could not reach the AbhiMart backend. Make sure the FastAPI server is running.",
        );
      } finally {
        assistantMessageIdRef.current = null;
        setIsStreaming(false);
      }
    },
    [
      appendAssistantText,
      handleRawPayload,
      isStreaming,
      sessionId,
      startAssistantMessage,
    ],
  );

  const resumeRefund = useCallback(
    async (approved: boolean, reviewerNote: string) => {
      if (isStreaming) {
        return;
      }

      setError(null);
      startAssistantMessage();
      setIsStreaming(true);

      try {
        const response = await fetch(`${API_BASE_URL}/v1/chat/resume`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            session_id: sessionId,
            approved,
            reviewer_note: reviewerNote,
          }),
        });

        if (!response.ok) {
          throw new Error(
            `Resume request failed with status ${response.status}.`,
          );
        }

        setPendingInterrupt(null);
        await readSseResponse(response, handleRawPayload);
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Resume request failed.";
        setError(message);
        appendAssistantText(
          "I could not resume the refund review. Please check the backend logs.",
        );
      } finally {
        assistantMessageIdRef.current = null;
        setIsStreaming(false);
      }
    },
    [
      appendAssistantText,
      handleRawPayload,
      isStreaming,
      sessionId,
      startAssistantMessage,
    ],
  );

  const samplePrompts = useMemo(
    () => [
      "What warranty do laptops come with?",
      "Is the Sony WH-1000XM5 in stock?",
      "My email is rohit@example.com. Please start a refund for my MacBook order.",
    ],
    [],
  );

  return {
    error,
    isStreaming,
    messages,
    pendingInterrupt,
    resumeRefund,
    samplePrompts,
    sendMessage,
    sessionId,
  };
}
