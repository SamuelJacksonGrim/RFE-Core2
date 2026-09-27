"""Word lists for the long-sequence corpus.

The four-rhythm regions are the vetted growth from tools/voice/gen_vocab.py
on experiment/witness-corpus (commit fb600b9). They are copied here so this
branch does not check that branch's corpus out over the live jsonl. Reflect
was out of scope for that generator; the reflect regions below are the
matching addition for this experiment. A token already in the live vocabulary
is dropped at generation time, not edited here.
"""
from __future__ import annotations

# Closed-class glue. Scaffolding, not a basin.
GLUE = (
    "a", "across", "against", "along", "and", "beneath", "between", "beyond",
    "from", "in", "into", "is", "of", "the", "through", "to", "toward",
    "with", "within",
)

REGIONS: dict[str, dict[str, list[str]]] = {
    "explore": {
        "venture": [
            "foray", "sortie", "expedition", "itinerary", "detour", "excursion",
            "traversal", "wayfaring", "jaunt", "trek", "odyssey", "beeline", "gambit",
        ],
        "grades": [
            "uncharted", "unplumbed", "unnamed", "unasked", "untried", "trackless",
            "remote", "outlying", "horizon", "vicinity", "yonder", "afar", "hinterland",
        ],
        "bearing": [
            "azimuth", "leeway", "heading", "waypoint", "meridian", "orienteer",
            "landmark", "sextant", "quadrant", "locus", "sightline", "tangent", "compass",
        ],
        "tentative": [
            "conjecture", "surmise", "postulate", "inkling", "hunch", "supposition",
            "hypothesis", "speculation", "query", "prospect", "reconnoiter", "canvass", "delve",
        ],
    },
    "dream": {
        "making": [
            "improvise", "extemporize", "fabulate", "confabulate", "extrapolate",
            "interpolate", "contrive", "germinate", "engender", "transfigure",
            "transmute", "reimagine", "overlay",
        ],
        "image": [
            "reverie", "daydream", "fantasia", "mirage", "apparition", "afterimage",
            "simulacrum", "figment", "tableau", "vignette", "panorama", "cameo", "illusion",
        ],
        "place": [
            "inscape", "mindscape", "dreamland", "otherworld", "dreamtime", "elsewhere",
            "nowhere", "faerie", "cloudland", "idyll", "dreamworld", "oasis", "fabled",
        ],
        "joining": [
            "interleave", "juxtapose", "entwine", "braid", "montage", "collage",
            "palimpsest", "hybridize", "alloy", "tessellate", "interlace", "inlay", "mingle",
        ],
    },
    "stabilize": {
        "support": [
            "undergird", "buttress", "ballast", "mooring", "keystone", "linchpin",
            "footing", "plinth", "stanchion", "girder", "trestle", "underlay", "strut",
        ],
        "equilibrium": [
            "equilibrium", "equipoise", "congruity", "proportion", "symmetry", "poise",
            "evenness", "aplomb", "composure", "equanimity", "steadiness", "constancy",
            "imperturbability",
        ],
        "tenure": [
            "tenure", "custody", "stewardship", "safekeeping", "perpetuity", "perennial",
            "longevity", "subsistence", "upkeep", "husbandry", "guardianship", "safeguard",
            "stalwart",
        ],
        "recovery": [
            "reestablish", "resettle", "reknit", "cohere", "buffer", "dampen",
            "righting", "regain", "restore", "repair", "mend", "redress", "rehabilitate",
        ],
    },
    "rupture": {
        "apart": [
            "disintegrate", "crumble", "unravel", "unspool", "deliquesce", "pulverize",
            "comminute", "decrepitate", "implode", "buckle", "splinter", "sunder", "rive",
        ],
        "after": [
            "wreckage", "debris", "rubble", "detritus", "aftermath", "ruination",
            "desolation", "remnant", "wrack", "carnage", "shambles", "slag", "cinder",
        ],
        "force": [
            "wrench", "concuss", "torsion", "tensile", "overload", "shockwave",
            "cavitation", "avulse", "deflagrate", "detonate", "whiplash", "topple", "capsize",
        ],
        "spoil": [
            "corrode", "erode", "abrade", "oxidize", "putrefy", "fester", "necrose",
            "gangrene", "rust", "embrittle", "leach", "excoriate", "molder",
        ],
    },
    # Finer analytic distinctions. Not the witness spine, and not a synonym
    # mill over analyze/inspect/verify (those stay in the live reflect lexicon).
    "reflect": {
        "grain": [
            "dissect", "parse", "itemize", "enumerate", "particularize", "specify",
            "differentiate", "discriminate", "subdivide", "anatomize", "decompose",
            "factorize", "granular",
        ],
        "warrant": [
            "corroborate", "substantiate", "underwrite", "crosscheck", "vet", "cite",
            "provenance", "ledger", "dossier", "footnote", "notarize", "authenticate",
            "certify",
        ],
        "retrospect": [
            "reassess", "reexamine", "reconsider", "retrospect", "hindsight", "debrief",
            "stocktake", "recap", "synopsis", "precis", "postmortem", "afterword",
            "stocktaking",
        ],
        "linkage": [
            "covary", "correlate", "contrast", "compare", "commensurate", "interrelate",
            "discrepancy", "consonant", "discrepant", "covariate", "proportionality",
            "covariance", "collation",
        ],
    },
}
