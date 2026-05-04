import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

export default defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    files: ["components/asap-demo.tsx"],
    rules: {
      // DefaultChatTransport reads refs only inside async prepareSendMessagesRequest (HTTP), not during render.
      "react-hooks/refs": "off",
    },
  },
  globalIgnores([".next/**", "out/**", "build/**", "next-env.d.ts"]),
]);
