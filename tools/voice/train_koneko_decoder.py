"""
tools/voice/train_koneko_decoder.py — train the missing SPEECH organ.

The encoder (tokens -> 128-d vector) is trained (generator_weights_5rhythm.pt). The DECODER
(vector -> words) was never saved. This trains a TokenDecoder to read back the FROZEN trained
encoder and SAVES it, so the bridge can render Koneko's actual representation into language.
Trained against the exact encoder the bridge loads, so decodes match runtime vectors.

The holdout eval also measures how losslessly the encoder's 'thoughts' can be read back
(recall@k / lift-over-random) — i.e. whether the substrate CAN be spoken from at all.
"""
import sys
sys.path.insert(0, ".")
import torch
from agents.generator import Generator
from agents.decoder import TokenDecoder
from training.corpus import load_corpus, TRAIN_PATH, HOLDOUT_PATH, corpus_version
from training.decoder_training import _vocab_from, _encode, train_decoder, evaluate

W   = "data/checkpoints/generator_weights_5rhythm.pt"
E   = "data/checkpoints/generator_ecology_5rhythm.json"
OUT = "data/checkpoints/decoder_5rhythm.pt"
DIM, HIDDEN, EPOCHS, TOPK = 128, 256, 20, 8

def main():
    torch.manual_seed(42)
    train = load_corpus(TRAIN_PATH); holdout = load_corpus(HOLDOUT_PATH)
    vocab = _vocab_from(train)
    print(f"corpus v{corpus_version()}  train={len(train)} holdout={len(holdout)} vocab={len(vocab)}", flush=True)

    gen = Generator(vocab_size=8192, dim=DIM, depth=4, heads=4)
    gen.load_checkpoint(W, E)
    gen.eval()
    print(f"loaded FROZEN trained 5-rhythm encoder (device={gen.device})", flush=True)

    dec = TokenDecoder(vocab, dim=DIM, hidden=HIDDEN)
    Xtr, ttr = _encode(gen, train)
    Xho, tho = _encode(gen, holdout)
    print("training decoder against the trained encoder ...", flush=True)
    train_decoder(gen, dec, Xtr, ttr, epochs=EPOCHS)

    tr = evaluate(dec, Xtr, ttr, top_k=TOPK)
    ho = evaluate(dec, Xho, tho, top_k=TOPK)
    print("TRAIN  :", tr, flush=True)
    print("HOLDOUT:", ho, flush=True)

    torch.save({"state_dict": dec.state_dict(), "vocab": vocab, "dim": DIM, "hidden": HIDDEN}, OUT)
    print("SAVED decoder ->", OUT, flush=True)

    print("SAMPLES (holdout true tokens -> decoded top-6):", flush=True)
    for r in range(min(6, len(tho))):
        g = dec.decode(Xho[r].cpu().numpy(), top_k=6)
        print("   ", tho[r][:8], "->", [t for t, _ in g], flush=True)

if __name__ == "__main__":
    main()
