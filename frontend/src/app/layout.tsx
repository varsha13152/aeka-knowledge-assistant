import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'AEKA — AI Knowledge Assistant',
  description: 'Enterprise knowledge assistant with multi-agent RAG',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full bg-gray-50 text-gray-900 antialiased">
        <div className="flex h-full flex-col">
          <header className="border-b bg-white px-6 py-3">
            <nav className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xl font-bold text-brand-700">AEKA</span>
                <span className="text-sm text-gray-500">Knowledge Assistant</span>
              </div>
              <div className="flex items-center gap-4">
                <a href="/" className="text-sm hover:text-brand-600">Chat</a>
                <a href="/documents" className="text-sm hover:text-brand-600">Documents</a>
                <a href="/admin/review" className="text-sm hover:text-brand-600">Review Queue</a>
                <a href="/dashboard" className="text-sm hover:text-brand-600">Dashboard</a>
              </div>
            </nav>
          </header>
          <main className="flex-1 overflow-hidden">{children}</main>
        </div>
      </body>
    </html>
  );
}
