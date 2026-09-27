"""
tools/voice/train_koneko_decoder.py — train the missing SPEECH organ.

The encoder (tokens -> 128-d vector) is trained (generator_weights_5rhythm.pt). The DECODER
(vector -> words) was never saved. This trains a TokenDecoder to read back the FROZEN trained
encoder and SAVES it.

Same weights and ecology the bridge loads (repl_qwen.py). That is not the same vector the
live mouth emits: default Qwen-perception replaces generate() with normalize(W @ qwen), and
corpus tokens absent from the saved ecology sit on virgin embedding rows. The holdout print
is therefore split into clean (every token already in the ecology) vs dirty.

recall@k / lift-over-random is the speakability gate — whether the substrate can be spoken
from at all. Near-random lift means the encoder has to grow before the organ is worth wiring.
"""
import sys
sys.path.insert(0, ".")
import numpy as np
import torch
from agents.generator import Generator
from agents.decoder import TokenDecoder
from training.corpus import load_corpus, TRAIN_PATH, HOLDOUT_PATH, corpus_version
from training.decoder_training import _vocab_from, train_decoder, evaluate

W   = "data/checkpoints/generator_weights_5rhythm.pt"
E   = "data/checkpoints/generator_ecology_5rhythm.json"
OUT = "data/checkpoints/decoder_5rhythm.pt"
OUT_ECO = "data/checkpoints/decoder_5rhythm_ecology.pt"
METRICS = "docs/findings/2026-09-22-decode-organ-metrics.json"
DIM, HIDDEN, EPOCHS, TOPK = 128, 256, 20, 8

def _encode_logged(gen, records, label):
    """Same frozen generate() path as training.decoder_training._encode, with a heartbeat.

    generate() registers any token the ecology does not already hold and parks it
    on an unused (still-init) embedding row. Snapshot ecology membership BEFORE
    calling this if the clean/orphan split is going to mean anything.
    """
    import time
    token_lists = [r.get("tokens", []) for r in records]
    vecs = []
    n = len(token_lists)
    t0 = time.perf_counter()
    for i, tl in enumerate(token_lists, 1):
        vecs.append(gen.generate(tl))
        if i % 1000 == 0 or i == n:
            print(f"  encode {label} {i}/{n}  {time.perf_counter() - t0:.1f}s", flush=True)
    X = torch.tensor(np.array(vecs), dtype=torch.float32, device=gen.device)
    return X, token_lists


def _in_ecology(token, ecology, pipeline):
    return pipeline.process(token).token in ecology


def _clean_mask(token_lists, ecology, pipeline):
    """True when every token already had a trained row before this process encoded."""
    return [all(_in_ecology(t, ecology, pipeline) for t in toks) for toks in token_lists]


def _take(X, token_lists, mask):
    idx = [i for i, keep in enumerate(mask) if keep]
    if not idx:
        return None, None
    return X[idx], [token_lists[i] for i in idx]


def _token_hits(dec, X, token_lists, ecology, pipeline, top_k=8):
    """Micro recall: fraction of true tokens landing in top-k, split by ecology membership."""
    dec.eval()
    with torch.no_grad():
        logits = dec(X)
    k = min(top_k, dec.vocab_size)
    top = logits.topk(k, dim=-1).indices.tolist()
    inn = out = inn_hit = out_hit = 0
    for pred_idx, toks in zip(top, token_lists):
        pred = set(pred_idx)
        for t in toks:
            j = dec.index.get(t)
            if j is None:
                continue
            hit = j in pred
            if _in_ecology(t, ecology, pipeline):
                inn += 1
                inn_hit += int(hit)
            else:
                out += 1
                out_hit += int(hit)
    def rate(h, n):
        return round(h / n, 4) if n else None
    return {
        "in_ecology_n": inn,
        "in_ecology_recall@k": rate(inn_hit, inn),
        "orphan_n": out,
        "orphan_recall@k": rate(out_hit, out),
    }


def _samples(dec, X, token_lists, n, tag):
    rows = []
    for r in range(min(n, len(token_lists))):
        guesses = dec.decode(X[r].detach().cpu().numpy(), top_k=6)
        shown = [(t, round(p, 3)) for t, p in guesses]
        print(f"   {tag} {token_lists[r]} -> {shown}", flush=True)
        rows.append({"true": list(token_lists[r]), "top6": shown})
    return rows


def main():
    import json
    from pathlib import Path

    torch.manual_seed(42)
    train = load_corpus(TRAIN_PATH); holdout = load_corpus(HOLDOUT_PATH)
    vocab = _vocab_from(train)
    print(f"corpus v{corpus_version()}  train={len(train)} holdout={len(holdout)} vocab={len(vocab)}", flush=True)

    gen = Generator(vocab_size=8192, dim=DIM, depth=4, heads=4)
    gen.load_checkpoint(W, E)
    gen.eval()
    # Membership BEFORE generate() assigns virgin rows to tokens the checkpoint never held.
    ecology = set(gen.registry.symbols)
    print(
        f"loaded FROZEN trained 5-rhythm encoder (device={gen.device}) "
        f"ecology_symbols={len(ecology)} emb={tuple(gen.embedding.weight.shape)}",
        flush=True,
    )

    dec = TokenDecoder(vocab, dim=DIM, hidden=HIDDEN)
    print("encoding train/holdout through the frozen encoder ...", flush=True)
    Xtr, ttr = _encode_logged(gen, train, "train")
    Xho, tho = _encode_logged(gen, holdout, "holdout")
    print("training decoder against the trained encoder ...", flush=True)
    train_decoder(gen, dec, Xtr, ttr, epochs=EPOCHS)

    tr = evaluate(dec, Xtr, ttr, top_k=TOPK)
    ho = evaluate(dec, Xho, tho, top_k=TOPK)
    print("TRAIN  :", tr, flush=True)
    print("HOLDOUT:", ho, flush=True)

    pipe = gen.registry.pipeline
    mask_tr = _clean_mask(ttr, ecology, pipe)
    mask_ho = _clean_mask(tho, ecology, pipe)
    Xtr_c, ttr_c = _take(Xtr, ttr, mask_tr)
    Xho_c, tho_c = _take(Xho, tho, mask_ho)
    Xtr_d, ttr_d = _take(Xtr, ttr, [not m for m in mask_tr])
    Xho_d, tho_d = _take(Xho, tho, [not m for m in mask_ho])
    print(
        f"ecology split  train clean={len(ttr_c)}/{len(ttr)}  "
        f"holdout clean={len(tho_c)}/{len(tho)}  "
        f"(clean = every token already in the loaded ecology)",
        flush=True,
    )

    ho_clean = evaluate(dec, Xho_c, tho_c, top_k=TOPK)
    ho_dirty = evaluate(dec, Xho_d, tho_d, top_k=TOPK)
    tr_clean = evaluate(dec, Xtr_c, ttr_c, top_k=TOPK)
    hits = _token_hits(dec, Xho, tho, ecology, pipe, top_k=TOPK)
    print("HOLDOUT clean (trained rows only):", ho_clean, flush=True)
    print("HOLDOUT dirty (any virgin row):   ", ho_dirty, flush=True)
    print("TRAIN   clean:                    ", tr_clean, flush=True)
    print("TOKEN HITS holdout:               ", hits, flush=True)

    torch.save({"state_dict": dec.state_dict(), "vocab": vocab, "dim": DIM, "hidden": HIDDEN,
                "ecology_only": False}, OUT)
    print("SAVED decoder ->", OUT, flush=True)

    # Same head, trained only on sequences the checkpoint can actually represent.
    # Asks the ceiling of the frozen encoder without also fitting virgin rows.
    print("training ecology-only decoder (clean sequences) ...", flush=True)
    torch.manual_seed(42)
    dec_eco = TokenDecoder(vocab, dim=DIM, hidden=HIDDEN)
    train_decoder(gen, dec_eco, Xtr_c, ttr_c, epochs=EPOCHS)
    eco_tr = evaluate(dec_eco, Xtr_c, ttr_c, top_k=TOPK)
    eco_ho = evaluate(dec_eco, Xho_c, tho_c, top_k=TOPK)
    eco_hits = _token_hits(dec_eco, Xho_c, tho_c, ecology, pipe, top_k=TOPK)
    print("ECOLOGY-ONLY TRAIN  :", eco_tr, flush=True)
    print("ECOLOGY-ONLY HOLDOUT:", eco_ho, flush=True)
    print("ECOLOGY-ONLY TOKEN HITS:", eco_hits, flush=True)
    torch.save({"state_dict": dec_eco.state_dict(), "vocab": vocab, "dim": DIM, "hidden": HIDDEN,
                "ecology_only": True}, OUT_ECO)
    print("SAVED ecology-only decoder ->", OUT_ECO, flush=True)

    print("SAMPLES stub decoder (holdout true tokens -> decoded top-6):", flush=True)
    print("  -- first holdout rows, unfiltered --", flush=True)
    samples_head = _samples(dec, Xho, tho, 6, "head")
    print("  -- clean holdout (trained rows) --", flush=True)
    samples_clean = _samples(dec, Xho_c, tho_c, 8, "clean")
    print("  -- dirty holdout (virgin row in the bag) --", flush=True)
    samples_dirty = _samples(dec, Xho_d, tho_d, 4, "dirty")
    print("SAMPLES ecology-only decoder on clean holdout:", flush=True)
    samples_eco = _samples(dec_eco, Xho_c, tho_c, 8, "eco")

    metrics = {
        "corpus": corpus_version(),
        "train_n": len(train),
        "holdout_n": len(holdout),
        "vocab": len(vocab),
        "ecology_symbols": len(ecology),
        "train_clean_n": len(ttr_c),
        "holdout_clean_n": len(tho_c),
        "top_k": TOPK,
        "epochs": EPOCHS,
        "hidden": HIDDEN,
        "dim": DIM,
        "encoder": W,
        "stub_train": tr,
        "stub_holdout": ho,
        "stub_holdout_clean": ho_clean,
        "stub_holdout_dirty": ho_dirty,
        "stub_train_clean": tr_clean,
        "stub_token_hits_holdout": hits,
        "ecology_only_train": eco_tr,
        "ecology_only_holdout": eco_ho,
        "ecology_only_token_hits": eco_hits,
        "samples_head": samples_head,
        "samples_clean": samples_clean,
        "samples_dirty": samples_dirty,
        "samples_ecology_only": samples_eco,
    }
    Path(METRICS).parent.mkdir(parents=True, exist_ok=True)
    Path(METRICS).write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print("WROTE", METRICS, flush=True)
    print("TRAIN_DONE", flush=True)

if __name__ == "__main__":
    main()
