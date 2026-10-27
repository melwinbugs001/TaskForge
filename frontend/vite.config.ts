import { get as httpGet } from "node:http";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

function isBackendAvailable(port: number): Promise<boolean> {
  return new Promise((resolve) => {
    const request = httpGet(
      {
        hostname: "127.0.0.1",
        port,
        path: "/api/v1/health",
        timeout: 500,
      },
      (response) => {
        response.resume();
        resolve(response.statusCode === 200);
      },
    );

    request.on("timeout", () => request.destroy());
    request.on("error", () => resolve(false));
  });
}

export default defineConfig(async ({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const ports = [8000, 8001, 8002];
  let apiTarget = "http://127.0.0.1:8000";

  if (command === "serve" && !env.VITE_API_URL) {
    const availablePorts = await Promise.all(
      ports.map(async (port) => (await isBackendAvailable(port) ? port : null)),
    );
    const backendPort = availablePorts.find((port) => port !== null);

    if (backendPort !== undefined) {
      apiTarget = `http://127.0.0.1:${backendPort}`;
      console.info(`TaskForge API detected on port ${backendPort}.`);
    } else {
      console.warn(
        "No TaskForge API was detected on ports 8000, 8001, or 8002. " +
          "Vite will proxy to port 8000; restart Vite after starting the backend.",
      );
    }
  }

  return {
    plugins: [react()],
    server: {
      host: "127.0.0.1",
      proxy: {
        "/api": {
          target: apiTarget,
          changeOrigin: true,
        },
      },
    },
  };
});
