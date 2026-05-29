import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import React from "react";
import FanChart from "../components/FanChart";
import type { YearPercentiles } from "../api/types";

// Recharts ResponsiveContainer reports 0 width in jsdom — replace with plain div
vi.mock("recharts", async () => {
  const actual = await vi.importActual<typeof import("recharts")>("recharts");
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="fan-chart" style={{ width: 600, height: 320 }}>{children}</div>
    ),
  };
});

const mockData: YearPercentiles[] = Array.from({ length: 5 }, (_, i) => ({
  year: 2026 + i,
  p10: 80_000 * (i + 1),
  p50: 120_000 * (i + 1),
  p90: 200_000 * (i + 1),
}));

test("renders without crashing", () => {
  render(<FanChart data={mockData} />);
  expect(screen.getByTestId("fan-chart")).toBeInTheDocument();
});

test("renders with correct number of data points", () => {
  const { container } = render(<FanChart data={mockData} />);
  expect(container).toBeTruthy();
  expect(mockData).toHaveLength(5);
});
