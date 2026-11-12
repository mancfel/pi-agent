# Next.js App Router Conventions

These conventions apply specifically when building or reviewing applications using the **Next.js App Router** (`app/` directory). They extend `react.md`.

## Server Components by Default

- **All components in `app/` are React Server Components (RSC) by default.** Keep them as RSC whenever possible — zero client-side JavaScript bundle overhead, faster initial page loads, direct secure access to backend services.
- Only introduce `"use client"` at the top of a file when interactivity is explicitly required:
  - React state (`useState`, `useReducer`)
  - Lifecycle effects (`useEffect`)
  - DOM event listeners (`onClick`, `onChange`, `onSubmit`)
  - Browser-only APIs (`window`, `localStorage`, `navigator`)

## Minimize Client Component Scope ("Push Client to Leaves")

- **Do NOT mark an entire route or page as `"use client"`** just because one button or input needs interactivity.
- Keep pages/layouts as Server Components and encapsulate only the interactive element in a focused Client Component:

```tsx
// app/dashboard/page.tsx (Server Component)
import { SummaryCards } from "@/components/SummaryCards";
import { DateFilterDropdown } from "@/components/DateFilterDropdown"; // "use client"
import { fetchDashboardData } from "@/services/dashboard";

export default async function DashboardPage() {
  const data = await fetchDashboardData();
  return <main className="p-6"><DateFilterDropdown /><SummaryCards data={data} /></main>;
}
```

## Data Fetching: RSC Flight Protocol (Never JSON + parse)

### The Rule: Fetch Directly in Server Components

Always fetch data inside `page.tsx` or `layout.tsx` using backend services or database clients. **Never** use `useEffect` with client-side `fetch()` + `response.json()`.

```tsx
// ✅ CLEAN PATTERN — Server Component, native types preserved
interface PageProps { searchParams: Promise<{ anno?: string }>; }

export default async function TaxDeclarationPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const initialData = await fetchTaxDeclarationData(Number(params.anno));
  return <TaxTable initialYear={Number(params.anno)} initialData={initialData} />;
}
```

### Why Client-Side JSON Fetch Is Prohibited

| Problem | Detail |
|---------|--------|
| **No native Date/Rich Types** | JSON has no `Date`, `Map`, `Set`, or `BigInt` — all dates arrive as strings, causing silent runtime errors like `.getFullYear()` throwing on a string. |
| **Type casts are erased at compile time** | `(json as DomainType)` is only a compile-time assertion; it does nothing at runtime. |
| **Waterfall requests & layout shift** | JS bundle must download → component mount → effect triggers → HTTP roundtrip → loading spinners. |
| **Boilerplate overhead** | Requires `AbortController`, `useState` for loading/error/data, manual DTO mapping. |

### How RSC Preserves Native Types

Next.js uses the **RSC Flight Protocol** (not JSON) to serialize data across the server-client boundary:
- **Native `Date` instances**, `BigInt`, and `ArrayBuffer` are natively encoded and rehydrated on the client — zero parsing needed.
- When `initialData` reaches a Client Component, all date properties are already real `Date` objects.

### Interactive Filters via URL Search Params

When user input should trigger new data (e.g., selecting a year from a dropdown):

1. **Update the URL**: Push or replace the query parameter (`router.push(`?anno=${newYear}`)`).
2. Next.js automatically re-runs the Server Component `page.tsx` with new `searchParams`, fetches fresh data, and passes typed props to the Client Component — no client-side `fetch()`.

### Fallback Exception: When Client-Side Fetch Is Unavoidable

For infinite scrolling, debounced search suggestions, or third-party client APIs where RSC fetching is not feasible:

- **Never use naive type casts** (`json as DomainType`).
- Always validate and transform using a **Zod schema** or explicit deserializer function.

## Route Handlers & API Endpoints

- Place API route handlers in `app/api/**/route.ts`.
- Always validate incoming request payloads (query params, body, headers) with **Zod** before processing.
- Return structured, typed JSON responses with appropriate HTTP status codes.
- Never expose internal database errors or stack traces to API consumers.
