import { renderHook, act, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import {
  useOptimize,
  useSimulate,
  useExplain,
  MOCK_RECOMMENDATION,
  MOCK_SIMULATION_RESULT,
} from "../api/client";

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("useOptimize", () => {
  it("returns mock Recommendation", async () => {
    const { result } = renderHook(() => useOptimize(), { wrapper });
    await act(async () => {
      await result.current.mutateAsync({ years: 30 });
    });
    expect(result.current.data?.ranked.length).toBeGreaterThan(0);
    expect(result.current.data?.explanation.winner_id).toBeDefined();
    expect(result.current.data).toEqual(MOCK_RECOMMENDATION);
  });
});

describe("useSimulate", () => {
  it("returns mock SimulationResult", async () => {
    const { result } = renderHook(() => useSimulate(), { wrapper });
    await act(async () => {
      await result.current.mutateAsync({ years: 30 });
    });
    expect(result.current.data?.by_year.length).toBeGreaterThan(0);
    expect(result.current.data).toEqual(MOCK_SIMULATION_RESULT);
  });
});

describe("useExplain", () => {
  it("returns explanation text on success", async () => {
    const { result } = renderHook(() => useExplain(), { wrapper });
    const explanation = MOCK_RECOMMENDATION.explanation;
    await act(async () => {
      await result.current.mutateAsync({ explanation, use_llm: true });
    });
    expect(result.current.data?.text).toBeTruthy();
  });

  it("shows isPending while mutating", async () => {
    const { result } = renderHook(() => useExplain(), { wrapper });
    expect(result.current.isPending).toBe(false);
    const explanation = MOCK_RECOMMENDATION.explanation;
    act(() => {
      void result.current.mutate({ explanation, use_llm: true });
    });
    await waitFor(() => expect(result.current.isPending).toBe(false));
  });
});
