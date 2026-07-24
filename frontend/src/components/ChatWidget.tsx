import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import type { useChatStream } from "../hooks/useChatStream";
import type { ChatMessage, RefundInterrupt } from "../types";

type ChatController = ReturnType<typeof useChatStream>;

function MessageBubble({ message }: { message: ChatMessage }) {
  return (
    <article className={`message message-${message.role}`}>
      <div className="message-label">
        {message.role === "user" ? "You" : "AbhiMart Agent"}
      </div>
      <p>{message.content || "…"}</p>
    </article>
  );
}

function RefundApprovalCard({
  interrupt,
  isStreaming,
  onDecision,
}: {
  interrupt: RefundInterrupt;
  isStreaming: boolean;
  onDecision: (approved: boolean, note: string) => void;
}) {
  const [note, setNote] = useState("Reviewed in local demo");

  return (
    <section className="approval-card" aria-label="Refund approval required">
      <div>
        <p className="section-label">Human review required</p>
        <h2>Refund approval</h2>
        <p className="approval-copy">
          The agent paused before processing this refund. Approve or reject to
          resume the same LangGraph thread.
        </p>
      </div>

      <dl className="approval-details">
        <div>
          <dt>Request</dt>
          <dd>{interrupt.refund_request_id}</dd>
        </div>
        <div>
          <dt>Order</dt>
          <dd>#{interrupt.order_id_preview ?? "unknown"}</dd>
        </div>
        <div>
          <dt>Status</dt>
          <dd>{interrupt.refund_status}</dd>
        </div>
        <div>
          <dt>Amount</dt>
          <dd>${interrupt.total_amount ?? "0.00"}</dd>
        </div>
      </dl>

      {interrupt.items?.length ? (
        <div className="approval-items">
          {interrupt.items.map((item) => (
            <div key={`${item.product_name}-${item.qty}`} className="item-row">
              <span>{item.product_name}</span>
              <span>
                Qty {item.qty ?? 1} — ${item.price ?? "0.00"}
              </span>
            </div>
          ))}
        </div>
      ) : null}

      <label className="note-field">
        Reviewer note
        <textarea
          value={note}
          onChange={(event) => setNote(event.target.value)}
          rows={3}
        />
      </label>

      <div className="approval-actions">
        <button
          type="button"
          className="secondary-action"
          disabled={isStreaming}
          onClick={() => onDecision(false, note)}
        >
          Reject
        </button>
        <button
          type="button"
          className="primary-action"
          disabled={isStreaming}
          onClick={() => onDecision(true, note)}
        >
          Approve
        </button>
      </div>
    </section>
  );
}

export function ChatWidget({
  chat,
  open,
  onOpen,
  onClose,
}: {
  chat: ChatController;
  open: boolean;
  onOpen: () => void;
  onClose: () => void;
}) {
  const {
    error,
    isStreaming,
    messages,
    pendingInterrupt,
    resumeRefund,
    sendMessage,
  } = chat;
  const [draft, setDraft] = useState("");
  const transcriptRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    transcriptRef.current?.scrollTo({
      top: transcriptRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, pendingInterrupt, open]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void sendMessage(draft);
    setDraft("");
  }

  return (
    <div className="chat-widget">
      {open ? (
        <section className="chat-window" aria-label="AbhiMart support chat">
          <header className="widget-header">
            <div>
              <p className="section-label">AI support</p>
              <h2>AbhiMart Agent</h2>
            </div>
            <div className="widget-header-right">
              <span className={`stream-pill ${isStreaming ? "active" : ""}`}>
                {isStreaming ? "Streaming" : "Ready"}
              </span>
              <button
                type="button"
                className="widget-close"
                aria-label="Close chat"
                onClick={onClose}
              >
                ×
              </button>
            </div>
          </header>

          <div className="transcript" ref={transcriptRef}>
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            {pendingInterrupt ? (
              <RefundApprovalCard
                interrupt={pendingInterrupt}
                isStreaming={isStreaming}
                onDecision={resumeRefund}
              />
            ) : null}
          </div>

          {error ? <p className="error-banner">{error}</p> : null}

          <form className="composer" onSubmit={handleSubmit}>
            <div className="composer-row">
              <textarea
                id="message"
                value={draft}
                placeholder="Ask about products, orders, or refunds…"
                disabled={isStreaming}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    event.currentTarget.form?.requestSubmit();
                  }
                }}
                rows={2}
              />
              <button type="submit" disabled={isStreaming || !draft.trim()}>
                Send
              </button>
            </div>
          </form>
        </section>
      ) : null}

      <button
        type="button"
        className="chat-fab"
        aria-label={open ? "Close support chat" : "Open support chat"}
        onClick={open ? onClose : onOpen}
      >
        {open ? "×" : "💬"}
      </button>
    </div>
  );
}
