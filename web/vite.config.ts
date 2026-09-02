import { copyFileSync, readdirSync } from "node:fs";
import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";

// browser mode copies the onnxruntime-web WASM runtime next to index.html (ort.env.wasm.wasmPaths points there)
const copyOrtWasm = (): Plugin => {
  let outDir = "dist";
  return {
    name: "copy-ort-wasm", apply: "build",
    configResolved(c) { outDir = c.build.outDir; },
    closeBundle() { const src = "node_modules/onnxruntime-web/dist"; for (const f of readdirSync(src)) if (/^ort-wasm-simd-threaded\.(wasm|mjs)$/.test(f)) copyFileSync(`${src}/${f}`, `${outDir}/${f}`); },
  };
};
export default defineConfig(({ mode }) => ({
  plugins: mode === "browser" ? [react(), copyOrtWasm()] : [react()],
  base: mode === "browser" ? "./" : "/",
  server: { proxy: { "/api": "http://localhost:8000", "/ws": { target: "ws://localhost:8000", ws: true } } },
}));
