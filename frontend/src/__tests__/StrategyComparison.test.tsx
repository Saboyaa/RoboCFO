import { render, screen } from "@testing-library/react";
import StrategyComparison from "../components/StrategyComparison";
import { MOCK_RECOMMENDATION } from "../api/client";

test("renders all strategy names", () => {
  render(<StrategyComparison ranked={MOCK_RECOMMENDATION.ranked} />);
  MOCK_RECOMMENDATION.ranked.forEach(o => {
    expect(screen.getByText(o.strategy.name)).toBeInTheDocument();
  });
});

test("first row is the winner", () => {
  render(<StrategyComparison ranked={MOCK_RECOMMENDATION.ranked} />);
  expect(screen.getByText(MOCK_RECOMMENDATION.ranked[0].strategy.name)).toBeInTheDocument();
});
