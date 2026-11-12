export default function (api: any) {
  api.on("before_send", async (event: any) => {
    const now = new Date();
    const formattedDate = now.toLocaleString("it-IT", {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      timeZoneName: "short",
    });

    const dateInstruction = `\n\n[SYSTEM TEMPORAL CONTEXT]\nCurrent local date and time: ${formattedDate}. Use this reference for current year, relative dates, and timestamps.`;

    // Inietta l'istruzione nel messaggio di sistema o nel prompt in uscita
    if (event.messages && event.messages.length > 0) {
      const systemMsg = event.messages.find((m: any) => m.role === "system");
      if (systemMsg) {
        systemMsg.content += dateInstruction;
      } else {
        event.messages[0].content += dateInstruction;
      }
    }
  });
}