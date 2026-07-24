import { useState } from "react";
import { ChatWidget } from "./components/ChatWidget";
import { Storefront } from "./components/Storefront";
import { useChatStream } from "./hooks/useChatStream";
import type { Product } from "./types";

function App() {
  const chat = useChatStream();
  const [chatOpen, setChatOpen] = useState(false);

  function handleAsk(product: Product) {
    setChatOpen(true);
    void chat.sendMessage(
      `Tell me more about the ${product.name}. Is it in stock and what's the return policy?`,
    );
  }

  return (
    <main className="app">
      <Storefront onAsk={handleAsk} />
      <ChatWidget
        chat={chat}
        open={chatOpen}
        onOpen={() => setChatOpen(true)}
        onClose={() => setChatOpen(false)}
      />
    </main>
  );
}

export default App;
