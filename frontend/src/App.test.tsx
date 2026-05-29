import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'

function wrapper({ children }: { children: React.ReactNode }) {
  return <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>
}

test('renders disclaimer', () => {
  render(<App />, { wrapper })
  expect(screen.getByText(/simulador educacional/i)).toBeInTheDocument()
})
