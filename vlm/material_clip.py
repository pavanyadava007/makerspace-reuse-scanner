"""Zero-shot material + condition via open_clip (ViT-B/32). CPU-friendly, ~40 ms per crop on x86."""
from __future__ import annotations

import open_clip
import torch
from PIL import Image
from prompts import CLIP_TEMPLATES, CONDITIONS, MATERIALS


class ClipMaterial:
    def __init__(self, name="ViT-B-32", pretrained="laion2b_s34b_b79k", device=None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model, _, self.pre = open_clip.create_model_and_transforms(name, pretrained=pretrained, device=self.device)
        self.tok = open_clip.get_tokenizer(name)
        self.mat_emb = self._text(MATERIALS); self.cond_emb = self._text([f"an object that is {c}" for c in CONDITIONS])

    @torch.no_grad()
    def _text(self, labels):
        embs = []
        for lab in labels:
            t = self.tok([tpl.format(lab) for tpl in CLIP_TEMPLATES]).to(self.device)
            e = self.model.encode_text(t); e = e / e.norm(dim=-1, keepdim=True); embs.append(e.mean(0))
        e = torch.stack(embs); return e / e.norm(dim=-1, keepdim=True)

    @torch.no_grad()
    def __call__(self, img: Image.Image) -> dict:
        x = self.pre(img).unsqueeze(0).to(self.device)
        v = self.model.encode_image(x); v = v / v.norm(dim=-1, keepdim=True)
        pm = (100 * v @ self.mat_emb.T).softmax(-1)[0]; pc = (100 * v @ self.cond_emb.T).softmax(-1)[0]
        return {"material": MATERIALS[pm.argmax()], "material_conf": float(pm.max()),
                "condition": CONDITIONS[pc.argmax()], "condition_conf": float(pc.max()), "backend": "clip-vitb32"}
