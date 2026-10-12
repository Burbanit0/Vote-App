import React, { useEffect, useState } from 'react';

/** A polite live region that speaks `text` once it has held for `delay` ms, so a screen
 * reader hears where a drag settles, not every frame on the way (PLAN_BEYOND_CI W3.6). */
const LiveAnnouncement: React.FC<{ text: string; testId: string; delay?: number }> = ({
  text,
  testId,
  delay = 800,
}) => {
  const [spoken, setSpoken] = useState('');
  useEffect(() => {
    const id = setTimeout(() => setSpoken(text), delay);
    return () => clearTimeout(id);
  }, [text, delay]);
  return (
    <span role="status" aria-live="polite" className="sr-only" data-testid={testId}>
      {spoken}
    </span>
  );
};

export default LiveAnnouncement;
