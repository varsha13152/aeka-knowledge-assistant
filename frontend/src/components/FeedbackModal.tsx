'use client';

/**
 * General feedback modal — allows users to submit bugs, feature requests, or UX feedback.
 */

import { useCallback, useEffect, useState } from 'react';
import { api } from '@/lib/api';

interface FeedbackModalProps {
  onClose: () => void;
}

const CATEGORIES = [
  { value: 'bug', label: '🐛 Bug Report' },
  { value: 'feature', label: '✨ Feature Request' },
  { value: 'ux', label: '💡 UX Improvement' },
  { value: 'other', label: '💬 Other' },
] as const;

export function FeedbackModal({ onClose }: FeedbackModalProps) {
  const [category, setCategory] = useState<string>('bug');
  const [message, setMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  // Close on Escape
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [onClose]);

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim() || isSubmitting) return;

    setIsSubmitting(true);
    try {
      await api.submitGeneralFeedback(category, message.trim());
      setSubmitted(true);
    } catch (err) {
      alert('Failed to submit feedback. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  }, [category, message, isSubmitting]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label="Submit feedback"
    >
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-2xl">
        {submitted ? (
          <div className="text-center py-8">
            <span className="text-4xl">🎉</span>
            <h3 className="mt-3 text-lg font-semibold text-gray-800">Thank you!</h3>
            <p className="mt-1 text-sm text-gray-500">Your feedback helps us improve AEKA.</p>
            <button
              onClick={onClose}
              className="mt-4 rounded-lg bg-brand-600 px-4 py-2 text-sm text-white hover:bg-brand-700"
            >
              Close
            </button>
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-800">Send Feedback</h3>
              <button
                onClick={onClose}
                className="rounded p-1 text-gray-400 hover:text-gray-600"
                aria-label="Close"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Category
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {CATEGORIES.map((cat) => (
                    <button
                      key={cat.value}
                      type="button"
                      onClick={() => setCategory(cat.value)}
                      className={`rounded-lg border px-3 py-2 text-sm text-left transition-colors ${
                        category === cat.value
                          ? 'border-brand-500 bg-brand-50 text-brand-700'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      {cat.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label htmlFor="feedback-message" className="block text-sm font-medium text-gray-700 mb-1">
                  Your feedback
                </label>
                <textarea
                  id="feedback-message"
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Tell us what's on your mind..."
                  rows={4}
                  maxLength={5000}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 resize-none"
                  required
                />
                <p className="mt-1 text-xs text-gray-400">{message.length}/5000</p>
              </div>

              <button
                type="submit"
                disabled={!message.trim() || isSubmitting}
                className="w-full rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
              >
                {isSubmitting ? 'Submitting...' : 'Submit Feedback'}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
