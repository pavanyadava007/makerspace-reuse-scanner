MATERIALS = ["steel", "aluminium", "copper", "PLA plastic", "PETG plastic", "ABS plastic", "acrylic",
             "plywood", "solid wood", "MDF", "cardboard", "glass", "fiberglass PCB", "rubber", "lithium battery"]
CONDITIONS = ["like new", "lightly used", "worn", "damaged", "scrap"]
CLIP_TEMPLATES = ["a photo of an object made of {}", "a close-up of {} in a workshop"]
QWEN_PROMPT = (
    "You are inspecting an object from a makerspace. Return ONLY JSON: "
    '{"material": one of %s, "condition": one of %s, "reusable": true|false, "note": "<12 words"}'
) % (MATERIALS, CONDITIONS)
