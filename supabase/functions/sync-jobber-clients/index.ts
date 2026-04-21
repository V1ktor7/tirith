import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.1";

const corsHeaders: Record<string, string> = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers":
    "authorization, x-client-info, apikey, content-type, x-sync-secret",
};

Deno.serve(async (req: Request): Promise<Response> => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    const syncSecret = Deno.env.get("SYNC_SECRET");
    const hdr = req.headers.get("x-sync-secret") ?? "";

    if (!syncSecret || hdr !== syncSecret) {
      return new Response(JSON.stringify({ error: "Unauthorized" }), {
        status: 401,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
    const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
    const supabase = createClient(supabaseUrl, serviceKey);

    const body = await req.json();
    const clients = Array.isArray(body.clients) ? body.clients : [];

    let upserted = 0;
    const errors: string[] = [];

    for (const c of clients) {
      const id = c?.id;
      if (!id || typeof id !== "string") continue;

      const srcUp = c.updatedAt ?? c.updated_at ?? null;

      const { error } = await supabase.from("jobber_clients").upsert(
        {
          jobber_client_id: id,
          snapshot: c as Record<string, unknown>,
          updated_at: new Date().toISOString(),
          source_last_updated: typeof srcUp === "string" ? srcUp : null,
        },
        { onConflict: "jobber_client_id" },
      );

      if (error) errors.push(`${id}: ${error.message}`);
      else upserted++;
    }

    return new Response(
      JSON.stringify({
        ok: errors.length === 0,
        upserted,
        received: clients.length,
        errors: errors.length ? errors : undefined,
      }),
      {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      },
    );
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return new Response(JSON.stringify({ error: msg }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
