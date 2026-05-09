export interface Env {
  APP_NAME: string;
  APP_VERSION: string;
  COURSE_NAME: string;
  ENVIRONMENT: string;
  API_TOKEN?: string;
  ADMIN_EMAIL?: string;
  SETTINGS?: KVNamespace;
}

const fallbackStore = new Map<string, string>();

function json(data: unknown, init: ResponseInit = {}): Response {
  const headers = new Headers(init.headers);
  headers.set("content-type", "application/json; charset=utf-8");
  return new Response(JSON.stringify(data, null, 2), {
    ...init,
    headers,
  });
}

async function kvGet(env: Env, key: string): Promise<string | null> {
  if (env.SETTINGS) {
    return env.SETTINGS.get(key);
  }
  return fallbackStore.get(key) ?? null;
}

async function kvPut(env: Env, key: string, value: string): Promise<void> {
  if (env.SETTINGS) {
    await env.SETTINGS.put(key, value);
    return;
  }
  fallbackStore.set(key, value);
}

function safeSecretSummary(env: Env) {
  return {
    apiTokenConfigured: Boolean(env.API_TOKEN),
    apiTokenLength: env.API_TOKEN?.length ?? 0,
    adminEmailConfigured: Boolean(env.ADMIN_EMAIL),
    adminEmailDomain: env.ADMIN_EMAIL?.split("@")[1] ?? null,
  };
}

function edgeMetadata(request: Request) {
  const cf = request.cf;
  return {
    colo: cf?.colo ?? null,
    country: cf?.country ?? null,
    city: cf?.city ?? null,
    region: cf?.region ?? null,
    asn: cf?.asn ?? null,
    asOrganization: cf?.asOrganization ?? null,
    httpProtocol: cf?.httpProtocol ?? null,
    tlsVersion: cf?.tlsVersion ?? null,
    tlsCipher: cf?.tlsCipher ?? null,
    continent: cf?.continent ?? null,
    timezone: cf?.timezone ?? null,
    clientTcpRtt: cf?.clientTcpRtt ?? null,
    latitude: cf?.latitude ?? null,
    longitude: cf?.longitude ?? null,
  };
}

async function handleCounter(env: Env): Promise<Response> {
  const raw = await kvGet(env, "visits");
  const visits = Number(raw ?? "0") + 1;
  await kvPut(env, "visits", String(visits));

  return json({
    key: "visits",
    visits,
    storage: env.SETTINGS ? "workers-kv" : "in-memory-fallback",
  });
}

async function handleKv(request: Request, env: Env, key: string): Promise<Response> {
  if (!key) {
    return json({ error: "key is required" }, { status: 400 });
  }

  if (request.method === "GET") {
    const value = await kvGet(env, key);
    if (value === null) {
      return json({ error: `key '${key}' not found` }, { status: 404 });
    }

    return json({
      key,
      value,
      storage: env.SETTINGS ? "workers-kv" : "in-memory-fallback",
    });
  }

  if (request.method === "POST" || request.method === "PUT") {
    let payload: { value?: string } | null = null;

    try {
      payload = (await request.json()) as { value?: string };
    } catch {
      return json({ error: "request body must be valid JSON" }, { status: 400 });
    }

    if (typeof payload?.value !== "string" || payload.value.length === 0) {
      return json({ error: "body must include a non-empty string field named 'value'" }, { status: 400 });
    }

    await kvPut(env, key, payload.value);

    return json({
      key,
      value: payload.value,
      storage: env.SETTINGS ? "workers-kv" : "in-memory-fallback",
      message: "value stored",
    });
  }

  return json({ error: "method not allowed" }, { status: 405 });
}

const worker: ExportedHandler<Env> = {
  async fetch(request, env) {
    const url = new URL(request.url);
    const pathname = url.pathname;

    console.log(
      JSON.stringify({
        path: pathname,
        method: request.method,
        colo: request.cf?.colo ?? null,
        country: request.cf?.country ?? null,
      }),
    );

    if (pathname === "/") {
      return json({
        app: env.APP_NAME,
        version: env.APP_VERSION,
        course: env.COURSE_NAME,
        environment: env.ENVIRONMENT,
        message: "Hello from Cloudflare Workers at the global edge",
        timestamp: new Date().toISOString(),
        routes: [
          "/",
          "/health",
          "/edge",
          "/config",
          "/secrets",
          "/counter",
          "/kv/<key>",
        ],
      });
    }

    if (pathname === "/health") {
      return json({
        status: "ok",
        service: env.APP_NAME,
        version: env.APP_VERSION,
        timestamp: new Date().toISOString(),
      });
    }

    if (pathname === "/edge") {
      return json({
        edge: edgeMetadata(request),
        request: {
          method: request.method,
          url: request.url,
          userAgent: request.headers.get("user-agent"),
          cfRay: request.headers.get("cf-ray"),
        },
      });
    }

    if (pathname === "/config") {
      return json({
        appName: env.APP_NAME,
        version: env.APP_VERSION,
        courseName: env.COURSE_NAME,
        environment: env.ENVIRONMENT,
        secretsShouldNotBeStoredHere: true,
      });
    }

    if (pathname === "/secrets") {
      return json({
        message: "Secrets are available through env, but the API only returns a safe summary.",
        secrets: safeSecretSummary(env),
      });
    }

    if (pathname === "/counter") {
      return handleCounter(env);
    }

    if (pathname.startsWith("/kv/")) {
      const key = pathname.replace(/^\/kv\//, "").trim();
      return handleKv(request, env, key);
    }

    return json(
      {
        error: "not found",
        path: pathname,
      },
      { status: 404 },
    );
  },
};

export default worker;
