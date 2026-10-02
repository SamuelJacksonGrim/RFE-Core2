"""Pass-1 BASE encoder vocabulary policy (language + reasoning, no world knowledge). Decided with Samuel 2026-10-02.

Why: the live 709-word vocab was hand-authored around the five rhythms, and its glue set is spatial only
(of, between, with, across, into, toward, within, along...). Nothing logical: no because/if/not/but. Those words
appear 0 times in the 8,527 training rows, though Samuel uses them thousands of times (not 6.3/1k words, but 5.0/1k,
if 4.2/1k, because 2.9/1k). A reasoning base needs them.

GLUE  = function words. Kept in every row as scaffolding, exempt from the content-frequency cap (per the authoring
        rule: never strip glue, level content only). v2 adds logic, negation, condition, contrast, comparison, time.
CONTENT seeds = reasoning/conversation words that should enter the content vocab and be leveled like any other.
EXCLUDE = what pass-1 never admits: proper nouns (places, people, family personas, games/media, brands),
          platform/tech names, numbers, URLs, code identifiers. Those come back through search, RM and LoRA (Layer 2).
Contractions are expanded first so negation is one token: don't -> do not, can't -> can not, isn't -> is not."""
import re

GLUE_V1_SPATIAL = {"of", "between", "with", "across", "the", "against", "and", "in", "to", "from", "into", "toward",
                   "a", "within", "along", "is", "an", "on", "at", "by", "for", "as", "be", "it"}
GLUE_V2_LOGIC = {
    # cause / consequence
    "because", "so", "therefore", "thus", "hence", "since",
    # condition
    "if", "unless", "whether", "then", "otherwise",
    # contrast / concession
    "but", "yet", "although", "though", "however", "instead", "despite", "while",
    # negation
    "not", "no", "never", "nor", "nothing", "none", "neither",
    # alternatives / addition
    "or", "either", "also", "too",
    # comparison
    "than", "as", "like", "more", "less", "same", "different",
    # time / sequence
    "when", "before", "after", "until", "still", "already", "again",
    # questions
    "why", "how", "what", "who", "which", "where",
    # modality
    "can", "could", "would", "should", "must", "might", "may", "will",
    # copula / auxiliaries needed to state things
    "are", "was", "were", "been", "do", "does", "did", "have", "has", "had",
    # reference
    "this", "that", "these", "those", "there", "here", "all", "some", "any", "each", "every", "only",
    # pronouns (who is speaking to whom: needed to talk to someone)
    "i", "me", "my", "mine", "myself", "you", "your", "yours", "yourself", "we", "us", "our", "ours", "ourselves",
    "he", "him", "his", "himself", "she", "her", "hers", "herself", "they", "them", "their", "theirs", "themselves",
    "its", "itself", "am",
    # small connectives the first pass missed
    "about", "through", "out", "up", "down", "over", "under", "just", "even", "very", "now", "without", "around",
}
GLUE = GLUE_V1_SPATIAL | GLUE_V2_LOGIC

CONTENT_SEEDS = {
    "know", "believe", "think", "understand", "mean", "true", "false", "maybe", "reason", "question", "answer",
    "agree", "disagree", "feel", "doubt", "prove", "evidence", "assume", "expect", "explain", "decide", "choose",
    "wrong", "right", "possible", "impossible", "certain", "uncertain", "cause", "effect", "result", "because",
    "ask", "tell", "listen", "say", "learn", "remember", "forget", "sorry", "thank", "help", "trust", "honest",
}
CONTENT_SEEDS -= GLUE

CONTRACTIONS = {"can't": "can not", "won't": "will not", "n't": " not", "'re": " are", "'ve": " have",
                "'ll": " will", "'d": " would", "'m": " am", "it's": "it is", "that's": "that is",
                "what's": "what is", "there's": "there is", "let's": "let us"}

# Abbreviations people type -> the full word, applied before encoding (training AND live input), so "img" and "image"
# are one concept with pooled examples. Only unambiguous ones; ambiguous (temp, rec, res, sm, pd...) are dropped instead.
ABBREVIATIONS = {
    "img": "image", "imgs": "images", "pic": "picture", "pics": "pictures", "txt": "text", "msg": "message",
    "msgs": "messages", "db": "database", "dbs": "databases", "len": "length", "prev": "previous", "desc": "description",
    "avg": "average", "num": "number", "nums": "numbers", "obj": "object", "objs": "objects", "dir": "directory",
    "dirs": "directories", "req": "request", "reqs": "requests", "seq": "sequence", "val": "value", "vals": "values",
    "docs": "documents", "doc": "document", "info": "information", "config": "configuration", "auth": "authentication",
    "dev": "developer", "devs": "developers", "env": "environment", "eval": "evaluation", "deg": "degrees",
    "dist": "distance", "conn": "connection", "pct": "percent", "exp": "experience", "fn": "function",
    "sys": "system", "nav": "navigation", "ctrl": "control", "crit": "critical", "inst": "instance", "diff": "difference",
    "approx": "approximately", "specs": "specifications", "spec": "specification", "ref": "reference",
    "refs": "references", "param": "parameter", "params": "parameters", "pls": "please", "plz": "please", "thx": "thanks", "ty": "thank you", "bc": "because",
    "cuz": "because", "tho": "though", "thru": "through", "w/": "with", "w/o": "without",
    "b4": "before", "u": "you", "ur": "your", "rn": "right now", "idk": "i do not know",
    "imo": "in my opinion", "imho": "in my opinion", "tbh": "to be honest", "ngl": "not going to lie",
    "afaik": "as far as i know", "iirc": "if i remember correctly", "btw": "by the way", "fyi": "for your information",
    "nvm": "never mind", "omw": "on my way", "wanna": "want to", "gonna": "going to", "ganna": "going to",
    "gotta": "got to", "kinda": "kind of", "sorta": "sort of", "dunno": "do not know", "lemme": "let me",
    "gimme": "give me", "ya": "you", "yall": "you all", "ok": "okay",
    # added after Samuel's review (2026-10-02): unambiguous technical abbreviations
    "px": "pixels", "mb": "megabytes", "gb": "gigabytes", "kb": "kilobytes", "xl": "extra large", "std": "standard",
    "ui": "user interface", "org": "organization", "kwh": "kilowatt hours", "eq": "equation", "bg": "background",
    "nn": "neural network", "tok": "token", "toks": "tokens", "eff": "efficiency", "gt": "greater than",
    "io": "input output", "lr": "learning rate", "pid": "process", "cls": "class",
}
# Tone markers: no facts, but they carry inflection and thought-in-progress ("hmm, I do not know about that",
# "lol, that is ridiculous", "uhh... maybe?"). KEPT as words (Samuel, 2026-10-02).
TONE_MARKERS = {"lol", "lmao", "haha", "hahaha", "hehe", "hmm", "hmmm", "mmm", "uh", "uhh", "um", "umm", "ugh", "oof",
                "yay", "aww", "meh", "welp", "bruh", "whoa", "wow", "huh", "eh", "ah", "oh", "ooh", "yikes", "phew"}
_ABBR = re.compile(r"(?<![\w/])(" + "|".join(re.escape(k) for k in sorted(ABBREVIATIONS, key=len, reverse=True)) + r")(?![\w/])", re.I)

def split_hyphens(text: str) -> str:
    """long-term -> long term, fine-tuning -> fine tuning. Each part is learned as its own word (more examples),
    and CSS-style tokens (text-center) fall apart into pieces the vocab already handles or drops."""
    return re.sub(r"(?<=[A-Za-z])-(?=[A-Za-z])", " ", text)

def expand_abbreviations(text: str) -> str:
    return _ABBR.sub(lambda m: ABBREVIATIONS[m.group(1).lower()], text)

def expand_contractions(text: str) -> str:
    t = text.replace("’", "'")
    for k in ("can't", "won't", "it's", "that's", "what's", "there's", "let's"):
        t = re.sub(rf"\b{k}\b", CONTRACTIONS[k], t, flags=re.I)
    for k in ("n't", "'re", "'ve", "'ll", "'d", "'m"):
        t = re.sub(rf"(\w){k}\b", rf"\1{CONTRACTIONS[k]}", t, flags=re.I)
    return t

if __name__ == "__main__":
    print(len(GLUE), "glue words (", len(GLUE_V2_LOGIC - GLUE_V1_SPATIAL), "new logic/function )")
    print(len(CONTENT_SEEDS), "content seeds")
    print(expand_contractions("I don't think it's true, and we can't prove it isn't."))
