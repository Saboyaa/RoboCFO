import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import Home from "../pages/Home";

function wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

test("renders disclaimer on home page", () => {
  render(<Home />, { wrapper });
  expect(screen.getByText(/simulador educacional/i)).toBeInTheDocument();
});

test("renders simulation form", () => {
  render(<Home />, { wrapper });
  expect(screen.getByRole("button", { name: /simular/i })).toBeInTheDocument();
  expect(screen.getByLabelText(/anos de simulação/i)).toBeInTheDocument();
});
