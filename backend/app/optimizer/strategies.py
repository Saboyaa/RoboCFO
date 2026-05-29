"""T9: Built-in strategy catalogue and custom strategy builder."""
from __future__ import annotations

from contracts import AssetClass, Strategy

BUILTIN_STRATEGIES: tuple[Strategy, ...] = (
    Strategy(
        id="debt_first",
        name="Quitar dívidas de alto custo primeiro",
        description="Direciona o fluxo de caixa disponível para amortizar as dívidas com maior taxa de juros antes de investir.",
    ),
    Strategy(
        id="invest_fixed",
        name="Investir primeiro (renda fixa)",
        description="Aplica todo o excedente mensal em renda fixa (Tesouro, CDB) antes de amortizar dívidas além do mínimo.",
    ),
    Strategy(
        id="invest_variable",
        name="Investir primeiro (renda variável)",
        description="Aplica todo o excedente mensal em renda variável (ações, ETFs) antes de amortizar dívidas além do mínimo.",
    ),
    Strategy(
        id="balanced",
        name="Equilibrado: metade dívida, metade investimento",
        description="Divide o excedente igualmente entre amortização de dívida e investimento diversificado.",
    ),
    Strategy(
        id="tax_efficient_redemption",
        name="Resgatar na ordem mais eficiente fiscalmente",
        description="Resgata investimentos na sequência que minimiza o imposto total, priorizando ativos isentos e os de prazo mais longo.",
    ),
)


def build_custom_strategy(
    debt_fraction: float,
    invest_asset_class: AssetClass,
) -> Strategy:
    """Return a Strategy with id='custom' reflecting the user-specified allocation."""
    invest_pct = round((1.0 - debt_fraction) * 100)
    debt_pct = round(debt_fraction * 100)
    return Strategy(
        id="custom",
        name=f"Personalizado: {debt_pct}% dívida / {invest_pct}% {invest_asset_class.value}",
        description=(
            f"Estratégia personalizada: {debt_pct}% do excedente para amortização de dívidas "
            f"e {invest_pct}% investido em {invest_asset_class.value}."
        ),
    )
