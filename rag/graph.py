"""Tiny material↔process knowledge graph for GraphRAG expansion. neighbours('PLA plastic') → related terms to retrieve."""
import networkx as nx

G = nx.Graph()
EDGES = [
    ("PLA plastic", "filament recycler"), ("PLA plastic", "Restmüll"), ("PLA plastic", "industrial composting"),
    ("PETG plastic", "filament recycler"), ("PETG plastic", "Gelber Sack"), ("ABS plastic", "fume extraction"),
    ("acrylic", "laser cutting"), ("acrylic", "Wertstoffhof"), ("plywood", "laser cutting"), ("plywood", "Altholz A II"),
    ("MDF", "Altholz A II"), ("MDF", "dust extraction"), ("solid wood", "Altholz A I"),
    ("steel", "Metallschrott"), ("aluminium", "Metallschrott"), ("aluminium", "Nutprofil"), ("copper", "Metallschrott"),
    ("copper", "cable"), ("fiberglass PCB", "Elektroschrott"), ("fiberglass PCB", "desoldering"),
    ("lithium battery", "BattG"), ("lithium battery", "fire risk"), ("cardboard", "Papiertonne"), ("glass", "Glascontainer"),
]
G.add_edges_from(EDGES)

def neighbours(term: str, depth: int = 1) -> list[str]:
    if term not in G: return []
    return [n for n in nx.single_source_shortest_path_length(G, term, cutoff=depth) if n != term]

if __name__ == "__main__":
    import sys
    print(neighbours(sys.argv[1] if len(sys.argv) > 1 else "PLA plastic"))
