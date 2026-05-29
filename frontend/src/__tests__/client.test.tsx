import { renderHook } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { useOptimize, useExplain, MOCK_RECOMMENDATION } from "../api/client";

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("useOptimize", () => {
  it("hook initialises in idle state", () => {
    const { result } = renderHook(() => useOptimize(), { wrapper });
    expect(result.current.isPending).toBe(false);
    expect(result.current.isError).toBe(false);
    expect(result.current.data).toBeUndefined();
  });
});

describe("useExplain", () => {
  it("hook initialises in idle state", () => {
    const { result } = renderHook(() => useExplain(), { wrapper });
    expect(result.current.isPending).toBe(false);
    expect(result.current.isError).toBe(false);
  });

  it("MOCK_RECOMMENDATION has required shape", () => {
    expect(MOCK_RECOMMENDATION.ranked.length).toBeGreaterThan(0);
    expect(MOCK_RECOMMENDATION.explanation.winner_id).toBeDefined();
    expect(MOCK_RECOMMENDATION.explanation.key_drivers.length).toBeGreaterThan(0);
  });
});
