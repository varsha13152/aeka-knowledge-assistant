'use client';

/**
 * Thumbs up/down feedback buttons for AI responses.
 * Allows users to rate individual messages.
 */

import { memo, useState } from 'react';
import { api } from '@/lib/api';

interface FeedbackButtonsProps {
  messageId: string;
}

export const FeedbackButtons = memo(function FeedbackButtons({ messageId }: FeedbackButtonsProps) {
  const [rating, setRating] = useState<'thumbs_up' | 'thumbs_down' | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleFeedback = async (newRating: 'thumbs_up' | 'thumbs_down') => {
    if (isSubmitting) return;

    // Optimistic update
    const previousRating = rating;
    setRating(newRating);
    setIsSubmitting(true);

    try {
      await api.submitFeedback(messageId, newRating);
    } catch {
      // Rollback on error
      setRating(previousRating);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="mt-1.5 flex items-center gap-1">
      <button
        onClick={() => handleFeedback('thumbs_up')}
        disabled={isSubmitting}
        className={`rounded p-1 text-xs transition-colors ${
          rating === 'thumbs_up'
            ? 'bg-green-100 text-green-600'
            : 'text-gray-400 hover:text-green-500 hover:bg-green-50'
        }`}
        aria-label="Thumbs up — good answer"
        title="Good answer"
      >
        👍
      </button>
      <button
        onClick={() => handleFeedback('thumbs_down')}
        disabled={isSubmitting}
        className={`rounded p-1 text-xs transition-colors ${
          rating === 'thumbs_down'
            ? 'bg-red-100 text-red-600'
            : 'text-gray-400 hover:text-red-500 hover:bg-red-50'
        }`}
        aria-label="Thumbs down — bad answer"
        title="Bad answer"
      >
        👎
      </button>
    </div>
  );
});
