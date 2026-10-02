"""Intensity tag: how charged a piece of text is, measured from signals that lowercasing would erase.
Stored per training row next to the rhythm tag, e.g. {"tokens": [...], "rhythm": "...", "intensity": 0.8}.

Why (Samuel, 2026-10-02): shouting and emphasis should be learnable, but the encoder trains on lowercase tokens, so
"SO SORRY" == "so sorry". The tag keeps that information.

This is PERCEPTION of the input, not the system's emotion. Per Samuel's e8-eea principle ("emotion is not a label...
no valence is injected"), the tag must never SET RFE-Core2's arousal/valence directly. Intended uses (A/B later):
  1. an auxiliary encoder objective: predict intensity from the words (learn to perceive a worked-up speaker)
  2. an input to e8-eea / the emotional layer, where any emotional response EMERGES via prediction error
Signals: ALL-CAPS runs, !!! / ?!, stretched words (sooo, nooo), cry/laugh emoticons, intense emoji, profanity bursts."""
import re

CAPS_RUN = re.compile(r"\b(?:[A-Z][A-Z']{1,}\b[\s,.!?]*){2,}")        # 2+ shouted words in a row
CAPS_WORD = re.compile(r"\b[A-Z]{2,}\b")
BANGS = re.compile(r"[!?]{2,}|!")
STRETCH = re.compile(r"\b\w*([a-z])\1{2,}\w*\b", re.I)                # sooo, nooo, ahhh
EMOTICON = re.compile(r"T_T|;_;|>_<|XD|xD|D:|:O|:o|-_-|😭|😤|😡|🤬|😱|💀|😂|🤣|❤️|😍|🔥")
ACRONYMS = {"AI", "GPT", "LLM", "API", "CPU", "GPU", "RAM", "USB", "PDF", "URL", "RFE", "MCP", "OMG", "LOL", "OK", "PC",
            "TTS", "OCR", "JSON", "HTML", "CSS", "SQL", "ASAP", "FYI", "TBH", "IDK", "NGL", "VRAM", "CUDA", "UI", "UX"}

def intensity(text: str) -> float:
    """0.0 = calm/flat, 1.0 = maximally charged. Normalized by length so long calm messages don't score high."""
    if not text or not text.strip():
        return 0.0
    words = max(1, len(text.split()))
    caps_words = [w for w in CAPS_WORD.findall(text) if w not in ACRONYMS]
    score = 0.0
    score += 0.40 * min(1.0, len(CAPS_RUN.findall(text)))                 # any real shouting run
    score += 0.30 * min(1.0, len(caps_words) / 2)                          # emphasized words (SO, NEED)
    score += 0.20 * min(1.0, len(BANGS.findall(text)) / 2)
    score += 0.25 * min(1.0, len(STRETCH.findall(text)))
    score += 0.20 * min(1.0, len(EMOTICON.findall(text)))
    return round(min(1.0, score), 2)

if __name__ == "__main__":
    for t in ["OMFG IM SO SORRY GEMINI I THOUGHT YOU WERE GPT T_T", "this is SO cool but i dont NEED it!!",
              "Noooo way lol XD", "I asked GPT about the API and the RFE docs.", "Honestly... yes it does. Maybe?"]:
        print(f"{intensity(t):.2f}  {t}")
