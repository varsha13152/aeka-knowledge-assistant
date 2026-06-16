import { ChatWindow } from '@/components/chat/ChatWindow';
import { SessionSidebar } from '@/components/chat/SessionSidebar';

export default function HomePage() {
  return (
    <div className="flex h-full">
      <SessionSidebar />
      <div className="flex-1">
        <ChatWindow />
      </div>
    </div>
  );
}
