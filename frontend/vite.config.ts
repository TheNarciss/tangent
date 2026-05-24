import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    allowedHosts: ["riskybusinesses.uk", "www.riskybusinesses.uk", ".riskybusinesses.uk"],
    host: "0.0.0.0",
    port: 5173,
    // Polling mode — nécessaire dans Docker sur Mac/Windows pour que les changements
    // de fichiers depuis l'host déclenchent bien le HMR dans le container.
    // L'env var CHOKIDAR_USEPOLLING (set par docker-compose) active aussi ce mode,
    // mais on le force ici aussi pour être robuste.
    watch: {
      usePolling: true,
      interval: 300,
    },
    // Permet à Vite d'accepter le client HMR sur n'importe quelle origine — utile
    // quand on accède au front via localhost:5173 alors qu'il tourne dans Docker.
    hmr: {
      clientPort: 5173,
    },
  },
});