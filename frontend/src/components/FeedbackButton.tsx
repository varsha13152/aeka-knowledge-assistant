'use client';

/**
 * Feedback trigger button for the nav bar.
 * Opens the FeedbackModal when clicked.
 */

import { useState } from 'react';
import { FeedbackModal } from './FeedbackModal';

export function FeedbackButton() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className="text-sm hover:text-brand-600"
        aria-label="Send feedback"
        title="Send feedback"
      >
        💬 Feedback
      </button>
      {isOpen && <FeedbackModal onClose={() => setIsOpen(false)} />}
    </>
  );
}
