'use client';

/**
 * HITL Review Queue — admin panel for reviewing flagged AI responses.
 *
 * Features:
 * - Real-time queue updates via WebSocket
 * - Approve/reject/edit actions
 * - Confidence scores and hallucination flags
 */

import { useCallback, useEffect, useState } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws/review';

interface ReviewItem {
  id: string;
  query: string;
  generated_answer: string;
  confidence_score: number;
  reason: string;
  status: string;
  created_at: string;
}

export default function ReviewQueuePage() {
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [selectedItem, setSelectedItem] = useState<ReviewItem | null>(null);
  const [editedAnswer, setEditedAnswer] = useState('');

  // Real-time updates
  const { connectionState } = useWebSocket({
    url: WS_URL,
    onMessage: (data) => {
      if (data.type === 'new_review_item') {
        setItems((prev) => [data.item, ...prev]);
      } else if (data.type === 'item_updated') {
        setItems((prev) =>
          prev.map((item) => (item.id === data.item.id ? data.item : item))
        );
      }
    },
  });

  const fetchItems = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/review/queue`);
      if (res.ok) {
        const data = await res.json();
        setItems(data.items || []);
      }
    } catch (err) {
      console.error('Failed to fetch review items:', err);
    }
  }, []);

  useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  const handleAction = async (id: string, action: 'approved' | 'rejected' | 'edited') => {
    try {
      await fetch(`${API_URL}/api/v1/review/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          status: action,
          edited_answer: action === 'edited' ? editedAnswer : undefined,
        }),
      });
      await fetchItems();
      setSelectedItem(null);
    } catch (err) {
      console.error('Action failed:', err);
    }
  };

  return (
    <div className="flex h-full">
      {/* Queue list */}
      <div className="w-1/2 border-r overflow-y-auto">
        <div className="p-4 border-b bg-white sticky top-0">
          <div className="flex items-center justify-between">
            <h1 className="text-lg font-bold text-gray-800">Review Queue</h1>
            <div className="flex items-center gap-2">
              <span
                className={`h-2 w-2 rounded-full ${
                  connectionState === 'connected' ? 'bg-green-500' : 'bg-red-500'
                }`}
              />
              <span className="text-xs text-gray-500">
                {connectionState === 'connected' ? 'Live' : 'Disconnected'}
              </span>
            </div>
          </div>
          <p className="text-sm text-gray-500 mt-1">
            {items.filter((i) => i.status === 'pending').length} items pending review
          </p>
        </div>

        <div className="divide-y">
          {items.map((item) => (
            <button
              key={item.id}
              onClick={() => {
                setSelectedItem(item);
                setEditedAnswer(item.generated_answer);
              }}
              className={`w-full p-4 text-left hover:bg-gray-50 ${
                selectedItem?.id === item.id ? 'bg-blue-50' : ''
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span
                  className={`text-xs font-medium rounded-full px-2 py-0.5 ${
                    item.status === 'pending'
                      ? 'bg-yellow-100 text-yellow-700'
                      : item.status === 'approved'
                      ? 'bg-green-100 text-green-700'
                      : 'bg-red-100 text-red-700'
                  }`}
                >
                  {item.status}
                </span>
                <span className="text-xs text-gray-400">
                  Confidence: {(item.confidence_score * 100).toFixed(0)}%
                </span>
              </div>
              <p className="text-sm font-medium text-gray-800 line-clamp-1">
                {item.query}
              </p>
              <p className="text-xs text-gray-500 mt-1">{item.reason}</p>
            </button>
          ))}

          {items.length === 0 && (
            <div className="p-12 text-center text-gray-400">
              No items in review queue
            </div>
          )}
        </div>
      </div>

      {/* Review detail */}
      <div className="w-1/2 overflow-y-auto p-6">
        {selectedItem ? (
          <div className="space-y-4">
            <div>
              <h2 className="text-sm font-semibold text-gray-600 mb-1">User Query</h2>
              <p className="bg-gray-50 rounded-lg p-3 text-sm">{selectedItem.query}</p>
            </div>

            <div>
              <h2 className="text-sm font-semibold text-gray-600 mb-1">
                Generated Answer (Confidence: {(selectedItem.confidence_score * 100).toFixed(0)}%)
              </h2>
              <div className="rounded-lg border p-3">
                <textarea
                  value={editedAnswer}
                  onChange={(e) => setEditedAnswer(e.target.value)}
                  className="w-full min-h-[200px] text-sm resize-none focus:outline-none"
                />
              </div>
            </div>

            <div>
              <h2 className="text-sm font-semibold text-gray-600 mb-1">Flag Reason</h2>
              <p className="text-sm text-orange-600 bg-orange-50 rounded-lg p-3">
                {selectedItem.reason}
              </p>
            </div>

            {/* Actions */}
            <div className="flex gap-3 pt-4 border-t">
              <button
                onClick={() => handleAction(selectedItem.id, 'approved')}
                className="flex-1 rounded-lg bg-green-600 py-2 text-sm font-medium text-white hover:bg-green-700"
              >
                ✓ Approve
              </button>
              <button
                onClick={() => handleAction(selectedItem.id, 'edited')}
                className="flex-1 rounded-lg bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                ✎ Approve with Edits
              </button>
              <button
                onClick={() => handleAction(selectedItem.id, 'rejected')}
                className="flex-1 rounded-lg bg-red-600 py-2 text-sm font-medium text-white hover:bg-red-700"
              >
                ✗ Reject
              </button>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-400">
            Select an item from the queue to review
          </div>
        )}
      </div>
    </div>
  );
}
