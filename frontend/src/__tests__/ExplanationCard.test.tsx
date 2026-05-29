import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ExplanationCard from "../components/ExplanationCard";
import { MOCK_RECOMMENDATION } from "../api/client";

function wrapper({ children }: { children: React.ReactNode }) {
  return <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>;
}

test("renders template text", () => {
  render(
    <ExplanationCard
      explanation={MOCK_RECOMMENDATION.explanation}
      templateText="Texto de exemplo para o teste."
    />,
    { wrapper },
  );
  expect(screen.getByText("Texto de exemplo para o teste.")).toBeInTheDocument();
});

test("renders Explicar mais button", () => {
  render(
    <ExplanationCard
      explanation={MOCK_RECOMMENDATION.explanation}
      templateText="Texto."
    />,
    { wrapper },
  );
  expect(screen.getByRole("button", { name: /explicar mais/i })).toBeInTheDocument();
});
