import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { useChatStream } from "./hooks/useChatStream";
import type { ChatMessage, RefundInterrupt } from "./types";

function MessageBubble({ message }: { message: ChatMessage }) {
  return (
    <article className={`message message-${message.role}`}>
      <div className="message-label">
        {message.role === "user" ? "You" : "AbhiMart Agent"}
      </div>
      <p>{message.content || "..."}</p>
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
          The agent paused before processing this refund. Review the order
          context, then approve or reject to resume the same LangGraph thread.
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
                Qty {item.qty ?? 1} - ${item.price ?? "0.00"}
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

function App() {
  const {
    error,
    isStreaming,
    messages,
    pendingInterrupt,
    resumeRefund,
    samplePrompts,
    sendMessage,
    sessionId,
  } = useChatStream();
  const [draft, setDraft] = useState("");
  const transcriptRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    transcriptRef.current?.scrollTo({
      top: transcriptRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, pendingInterrupt]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void sendMessage(draft);
    setDraft("");
  }

  return (
    <main className="app-shell">
      <aside className="side-panel">
        <div>
          <p className="section-label">AbhiMart Stage 6</p>
          <h1>AI support console</h1>
          <p className="intro-copy">
            React frontend for the existing FastAPI SSE chat and refund approval
            contract.
          </p>
        </div>

        <div className="status-stack">
          <div className="status-card">
            <span>Backend</span>
            <strong>http://127.0.0.1:8000</strong>
          </div>
          <div className="status-card">
            <span>Session</span>
            <strong>{sessionId}</strong>
          </div>
        </div>

        <div className="prompt-stack">
          <p className="section-label">Try these</p>
          {samplePrompts.map((prompt) => (
            <button
              key={prompt}
              type="button"
              className="prompt-button"
              disabled={isStreaming}
              onClick={() => void sendMessage(prompt)}
            >
              {prompt}
            </button>
          ))}
        </div>
      </aside>

      <section className="chat-panel" aria-label="Chat workspace">
        <header className="chat-header">
          <div>
            <p className="section-label">Live stream</p>
            <h2>Customer conversation</h2>
          </div>
          <span className={`stream-pill ${isStreaming ? "active" : ""}`}>
            {isStreaming ? "Streaming" : "Ready"}
          </span>
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
          <label htmlFor="message">Message</label>
          <div className="composer-row">
            <textarea
              id="message"
              value={draft}
              placeholder="Ask about warranty, product stock, orders, or refunds..."
              disabled={isStreaming}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  event.currentTarget.form?.requestSubmit();
                }
              }}
              rows={3}
            />
            <button type="submit" disabled={isStreaming || !draft.trim()}>
              Send
            </button>
          </div>
        </form>
      </section>
    </main>
  );
}

export default App;
