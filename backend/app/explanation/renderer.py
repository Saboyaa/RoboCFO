"""Explanation renderer — T12.

Fast path (use_llm=False): Jinja2 template rendering in Portuguese.
LLM path (use_llm=True): DeepSeek via openai SDK; the model is instructed
  never to recompute numbers — it may only narrate what is in the Explanation struct.
"""
from __future__ import annotations

import os
from pathlib import Path

from contracts import Explanation, KeyDriver
from jinja2 import Environment, FileSystemLoader, select_autoescape

# ---------------------------------------------------------------------------
# Portuguese label map for all 8 KeyDriver values (fixed taxonomy)
# ---------------------------------------------------------------------------

KEY_DRIVER_LABELS: dict[str, str] = {
    KeyDriver.IRPF_REDUCER_BENEFIT.value: (
        "Redutor IRPF (Lei 15.270/2025) — o redutor reduz materialmente o imposto"
    ),
    KeyDriver.TAX_EFFICIENCY.value: (
        "Eficiência fiscal — o imposto vitalício total difere entre as estratégias"
    ),
    KeyDriver.DEBT_COST_REDUCTION.value: (
        "Dívida de alto custo — quitar dívidas caras melhora o retorno líquido"
    ),
    KeyDriver.SEQUENCE_OF_RETURNS_RISK.value: (
        "Sequência de retornos — a dispersão dos caminhos determina a probabilidade de sucesso"
    ),
    KeyDriver.VARIABLE_INCOME_EXEMPTION.value: (
        "Isenção de renda variável — utilização da isenção mensal de R$20.000 no swing trade"
    ),
    KeyDriver.FIXED_INCOME_HOLDING_PERIOD.value: (
        "Prazo de renda fixa — a tabela regressiva muda a alíquota conforme o tempo de aplicação"
    ),
    KeyDriver.IRPFM_THRESHOLD.value: (
        "IRPFM — a estratégia cruza ou evita o piso anual de R$600.000"
    ),
    KeyDriver.ASSET_ALLOCATION.value: (
        "Alocação de ativos — composição de risco/retorno entre as classes de ativos"
    ),
}

# ---------------------------------------------------------------------------
# Jinja2 environment
# ---------------------------------------------------------------------------

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape([]),  # plain text output, no HTML escaping
    keep_trailing_newline=True,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render_explanation(explanation: Explanation, use_llm: bool = False) -> str:
    """Render an Explanation to a Portuguese narrative string.

    Parameters
    ----------
    explanation:
        Structured data from the optimizer.  This function ONLY renders; it
        never computes or infers numeric values.
    use_llm:
        If False (default), use the deterministic Jinja2 template.
        If True, call DeepSeek via the openai SDK.  Raises EnvironmentError
        if LLM_PROVIDER is "none" or DEEPSEEK_API_KEY is missing.
    """
    if use_llm:
        return _render_with_llm(explanation)
    return _render_with_template(explanation)


# ---------------------------------------------------------------------------
# Template path
# ---------------------------------------------------------------------------


def _render_with_template(explanation: Explanation) -> str:
    template = _jinja_env.get_template("recommendation.j2")
    return template.render(
        objective=explanation.objective.value,
        winner_id=explanation.winner_id,
        winner_metric=explanation.winner_metric,
        runner_up_id=explanation.runner_up_id,
        delta_vs_runner_up=explanation.delta_vs_runner_up,
        key_drivers=list(explanation.key_drivers),
        key_driver_labels=KEY_DRIVER_LABELS,
    )


# ---------------------------------------------------------------------------
# LLM path
# ---------------------------------------------------------------------------


def _render_with_llm(explanation: Explanation) -> str:
    """Call DeepSeek to produce a richer Portuguese narrative.

    The prompt explicitly forbids the model from computing or inferring any
    values — it must use ONLY the numbers supplied in the structured data.
    """
    llm_provider = os.environ.get("LLM_PROVIDER", "none")
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")

    if llm_provider == "none":
        raise OSError(
            "LLM path is disabled: LLM_PROVIDER is set to 'none'. "
            "Set LLM_PROVIDER=deepseek and provide DEEPSEEK_API_KEY to enable it."
        )
    if not api_key:
        raise OSError(
            "DEEPSEEK_API_KEY is not set. "
            "Provide the API key to use the LLM explanation path."
        )

    # Build the template-rendered text as context for the LLM
    template_text = _render_with_template(explanation)

    # Key drivers as a list of Portuguese labels
    drivers_text = "\n".join(
        f"  - {KEY_DRIVER_LABELS[d.value]}" for d in explanation.key_drivers
    )

    system_prompt = (
        "Você é um assistente financeiro educacional brasileiro. "
        "Sua tarefa é transformar dados estruturados em narrativa em português claro e acessível. "
        "Use ONLY the numbers provided. Do NOT compute or infer any values. "
        "Nunca recalcule valores; apenas narre os dados fornecidos."
    )

    user_prompt = (
        f"Com base nos seguintes dados estruturados, escreva uma explicação narrativa "
        f"em português para o usuário. NÃO compute nem infira nenhum valor — "
        f"use APENAS os números fornecidos abaixo.\n\n"
        f"=== Dados Estruturados ===\n{template_text}\n\n"
        f"=== Fatores Principais ===\n{drivers_text}\n\n"
        f"Escreva um parágrafo explicativo conciso (3-5 frases) em português, "
        f"sem repetir todos os números, mas mencionando os fatores mais relevantes."
    )

    from openai import OpenAI  # lazy import — only needed on LLM path

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com/v1",
    )
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=512,
        temperature=0.3,
    )
    content = response.choices[0].message.content
    return content if content is not None else ""


__all__ = ["render_explanation", "KEY_DRIVER_LABELS"]
