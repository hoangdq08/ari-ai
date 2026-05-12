import { ChatScreen } from "@/modules/chat/presentation/screens/ChatScreen";

import { ChatStoreProvider } from "@/modules/chat/presentation/stores/useChatStore";

export default function ChatPage() {
  return (
    <ChatStoreProvider>
      <ChatScreen />
    </ChatStoreProvider>
  );
}
