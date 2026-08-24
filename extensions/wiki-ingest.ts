import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  // Subscribe to events
  let enabled: boolean;

  // 1. Traccia quando la skill viene invocata da input
  pi.on('input', async (event, ctx) => {
    if (event.text.startsWith('/skill:wiki-ingest')) {
      enabled = true;
    }
  });
  
  pi.on("agent_settled", async (event, ctx) => {
	  if(enabled)
		pi.sendUserMessage("/skill:wiki-ingest continue with next file");
  });
  
  pi.on('agent_cancelled', async (event, ctx) => {
	  enabled = false;
  });
}