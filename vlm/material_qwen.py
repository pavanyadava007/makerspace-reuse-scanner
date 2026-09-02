"""Local Qwen2.5-VL-3B-Instruct for material/condition when a GPU (≥6 GB) is present. Falls back to CLIP otherwise."""
from __future__ import annotations

import json
import re

import torch
from PIL import Image
from prompts import QWEN_PROMPT


class QwenMaterial:
    def __init__(self, model_id="Qwen/Qwen2.5-VL-3B-Instruct"):
        from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration
        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(model_id, torch_dtype=torch.bfloat16, device_map="auto")
        self.proc = AutoProcessor.from_pretrained(model_id)

    @torch.no_grad()
    def __call__(self, img: Image.Image) -> dict:
        msgs = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": QWEN_PROMPT}]}]
        text = self.proc.apply_chat_template(msgs, add_generation_prompt=True)
        inputs = self.proc(text=[text], images=[img], return_tensors="pt").to(self.model.device)
        out = self.model.generate(**inputs, max_new_tokens=80, do_sample=False)
        s = self.proc.batch_decode(out[:, inputs.input_ids.shape[1]:], skip_special_tokens=True)[0]
        m = re.search(r"\{.*\}", s, re.DOTALL)
        d = json.loads(m.group()) if m else {"material": "unknown", "condition": "unknown", "reusable": None, "note": s[:60]}
        d["backend"] = "qwen2.5-vl-3b"; return d


def get_backend():
    if torch.cuda.is_available() and torch.cuda.get_device_properties(0).total_memory > 6e9:
        return QwenMaterial()
    from material_clip import ClipMaterial
    return ClipMaterial()
