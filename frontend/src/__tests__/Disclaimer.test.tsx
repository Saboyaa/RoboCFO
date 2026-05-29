import { render, screen } from "@testing-library/react";
import Disclaimer from "../components/Disclaimer";

test("renders disclaimer text", () => {
  render(<Disclaimer />);
  expect(screen.getByText(/simulador educacional/i)).toBeInTheDocument();
  expect(screen.getByText(/assessoria financeira/i)).toBeInTheDocument();
});
