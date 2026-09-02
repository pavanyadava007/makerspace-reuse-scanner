// Dedicated inference worker (browser demo build): holds the onnxruntime-web session so the page thread never blocks.
// Messages: {type:"init", wasmPaths, model} → {type:"ready", threads}; {type:"run", x} → {type:"result", data, dims, ms}.
import * as ort from "onnxruntime-web";

let session: ort.InferenceSession | null = null;
self.onmessage = async (e: MessageEvent) => {
  const m = e.data;
  try {
    if (m.type === "init") {
      ort.env.wasm.wasmPaths = m.wasmPaths;
      session = await ort.InferenceSession.create(m.model as ArrayBuffer, { executionProviders: ["wasm"], graphOptimizationLevel: "all" });
      self.postMessage({ type: "ready", threads: ort.env.wasm.numThreads ?? 1, input: session.inputNames[0] });
    } else if (m.type === "run" && session) {
      const t = performance.now();
      const res = await session.run({ [session.inputNames[0]]: new ort.Tensor("float32", m.x as Float32Array, [1, 3, m.size, m.size]) });
      const o = res[session.outputNames[0]]; const data = o.data as Float32Array;
      (self as unknown as Worker).postMessage({ type: "result", data, dims: o.dims, ms: performance.now() - t }, [data.buffer]);
    }
  } catch (err) { self.postMessage({ type: "error", message: (err as Error).message }); }
};
