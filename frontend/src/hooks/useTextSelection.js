import { useEffect, useState } from "react";

/**
 * Tracks the current text selection inside `containerRef` and exposes its
 * text + on-screen position, so a floating Copy/Translate toolbar can be
 * positioned next to whatever the user just highlighted (mouse or touch).
 */
export function useTextSelection(containerRef) {
  const [selection, setSelection] = useState(null); // { text, rect }

  useEffect(() => {
    function handleSelectionChange() {
      const sel = window.getSelection();
      if (!sel || sel.isCollapsed || sel.rangeCount === 0) {
        setSelection(null);
        return;
      }
      const text = sel.toString().trim();
      if (!text) {
        setSelection(null);
        return;
      }
      const container = containerRef.current;
      if (container && !container.contains(sel.anchorNode)) {
        setSelection(null);
        return;
      }
      const rect = sel.getRangeAt(0).getBoundingClientRect();
      if (rect.width === 0 && rect.height === 0) {
        setSelection(null);
        return;
      }
      setSelection({ text, rect });
    }

    document.addEventListener("selectionchange", handleSelectionChange);
    return () => document.removeEventListener("selectionchange", handleSelectionChange);
  }, [containerRef]);

  const clear = () => {
    window.getSelection()?.removeAllRanges();
    setSelection(null);
  };

  return { selection, clear };
}
