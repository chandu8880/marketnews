import { useState } from "react";
import { translateText } from "../api";

export default function SelectionToolbar({ selection, onClear }) {
  const [translating, setTranslating] = useState(false);
  const [translation, setTranslation] = useState(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState(null);

  if (!selection) return null;

  const { text, rect } = selection;
  const top = rect.top + window.scrollY - 8;
  const left = rect.left + window.scrollX + rect.width / 2;

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    } catch {
      setError("Copy failed");
    }
  }

  async function handleTranslate() {
    setTranslating(true);
    setError(null);
    try {
      const res = await translateText(text, "te");
      setTranslation(res.translated);
    } catch {
      setError("Translation failed. Try again.");
    } finally {
      setTranslating(false);
    }
  }

  function handleClose() {
    setTranslation(null);
    setError(null);
    onClear();
  }

  return (
    <div className="selection-toolbar" style={{ top, left }}>
      {!translation && !error && (
        <div className="selection-toolbar-buttons">
          <button onClick={handleCopy} className="sel-btn">
            {copied ? "Copied" : "Copy"}
          </button>
          <button onClick={handleTranslate} className="sel-btn sel-btn-primary" disabled={translating}>
            {translating ? "Translating…" : "Translate to Telugu"}
          </button>
          <button onClick={handleClose} className="sel-btn sel-btn-close" aria-label="Close">
            ×
          </button>
        </div>
      )}
      {(translation || error) && (
        <div className="selection-translation">
          <div className="selection-translation-original">{text}</div>
          {translation && <div className="selection-translation-telugu">{translation}</div>}
          {error && <div className="selection-translation-error">{error}</div>}
          <div className="selection-toolbar-buttons">
            {translation && (
              <button
                className="sel-btn"
                onClick={async () => {
                  await navigator.clipboard.writeText(translation);
                  setCopied(true);
                  setTimeout(() => setCopied(false), 1200);
                }}
              >
                {copied ? "Copied" : "Copy Telugu"}
              </button>
            )}
            <button onClick={handleClose} className="sel-btn sel-btn-close" aria-label="Close">
              ×
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
