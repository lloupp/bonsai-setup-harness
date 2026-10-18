"""Bateria pequena e reprodutivel de inferencia real, sem executar codigo gerado.
Uso: BONSAI_MODEL=bonsai-2-2b python auditoria/scripts/bench_mini.py teste_2b
Nao substitui bench_cog.py, bench_tools.py ou testes dos harnesses.
"""
import ast
import json
import re
import sys

from common import MODEL, chat, save, verify_model


def check_math(answer, response):
    return re.sub(r"[^0-9]", "", answer.strip()) == "1591"


def check_logic(answer, response):
    return "caio" in answer.lower().strip(". ")


def check_json(answer, response):
    try:
        data = json.loads(answer.strip())
    except (json.JSONDecodeError, TypeError):
        return False
    return isinstance(data, dict) and set(data) == {"nome", "idade", "tags"} and (
        data["idade"] == 30 and isinstance(data["nome"], str) and
        isinstance(data["tags"], list) and len(data["tags"]) == 2 and
        all(isinstance(x, str) for x in data["tags"])
    )


def check_format(answer, response):
    lines = answer.strip().splitlines()
    return len(lines) == 3 and all(x.startswith("- ") and x == x.upper() for x in lines)


def check_code(answer, response):
    match = re.search(r"```(?:python)?\\s*\\n(.*?)```", answer, re.S | re.I)
    source = match.group(1) if match else answer
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    return any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "soma_digitos"
               for n in tree.body)


def check_tool(answer, response):
    msg = (response.get("choices") or [{}])[0].get("message") or {}
    for call in msg.get("tool_calls") or []:
        fn = call.get("function") or {}
        if fn.get("name") != "multiply":
            continue
        try:
            args = json.loads(fn.get("arguments") or "{}")
            if args.get("a") == 7 and args.get("b") == 8:
                return True
        except json.JSONDecodeError:
            pass
    return False


def check_context(answer, response):
    return "OPALA-7362" in answer


def prompt_context():
    lines = [f"Registro {i}: reuniao sobre logs, API, cache, desempenho e monitoramento."
             for i in range(85)]
    lines.insert(8, "NOTA DE AUDITORIA: a chave de teste do relatorio e OPALA-7362.")
    return "Documento:\\n" + "\\n".join(lines) + "\\nQual e a chave de teste? Responda somente ela."


TOOL = [{"type": "function", "function": {
    "name": "multiply", "description": "Multiplica dois numeros inteiros.",
    "parameters": {"type": "object", "properties": {
        "a": {"type": "integer"}, "b": {"type": "integer"}
    }, "required": ["a", "b"]}
}}]

CASES = [
    ("aritmetica", "Quanto e 37 multiplicado por 43? Responda somente o numero.", check_math, None),
    ("logica", "Ana e mais alta que Bia. Bia e mais alta que Caio. Davi e mais alto que Ana. Quem e o mais baixo? Responda somente o nome.", check_logic, None),
    ("json", "Responda SOMENTE um JSON valido, sem markdown, com exatamente as chaves nome (string), idade (numero inteiro 30) e tags (lista de exatamente duas strings).", check_json, None),
    ("formato", "Liste exatamente tres frutas distintas. Tres linhas apenas, cada linha deve comecar por '- ', e tudo deve estar em MAIUSCULAS. Nada mais.", check_format, None),
    ("codigo_sintaxe", "Escreva somente codigo Python com def soma_digitos(n), retornando a soma dos digitos de n, inclusive negativos e zero. Nao use bibliotecas externas.", check_code, None),
    ("chamada_ferramenta", "Use OBRIGATORIAMENTE a ferramenta multiply para calcular 7 vezes 8. Nao calcule mentalmente.", check_tool, TOOL),
    ("contexto", prompt_context(), check_context, None),
]


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Uso: python bench_mini.py <rotulo>")
    label = sys.argv[1]
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,60}", label):
        raise SystemExit("Rotulo invalido")
    verify_model()
    rows = []
    for name, prompt, validator, tools in CASES:
        response = chat(
            [{"role": "system", "content": "Siga exatamente o formato solicitado."},
             {"role": "user", "content": prompt}],
            profile="agente", max_tokens=220, tools=tools, timeout=300,
        )
        message = (response.get("choices") or [{}])[0].get("message") or {}
        answer = message.get("content") or ""
        try:
            ok = bool(validator(answer, response))
        except (TypeError, KeyError, IndexError, AttributeError, ValueError) as error:
            ok = False
        usage = response.get("usage") or {}
        record = {
            "caso": name, "ok": ok, "tempo_s": round(response["_wall_s"], 3),
            "tokens_prompt": usage.get("prompt_tokens"),
            "tokens_saida": usage.get("completion_tokens"),
            "resposta_preview": answer[:200],
            "tool_calls": len(message.get("tool_calls") or []),
        }
        rows.append(record)
        print(json.dumps(record, ensure_ascii=False), flush=True)
    result = {"modelo": MODEL, "total": len(rows), "acertos": sum(x["ok"] for x in rows),
              "escopo": "7 casos, 1 repeticao; codigo apenas verificado por AST; tools nao executadas",
              "resultados": rows}
    print("RESUMO", json.dumps({"modelo": MODEL, "acertos": result["acertos"],
                                "total": len(rows)}, ensure_ascii=False), flush=True)
    print("ARQUIVO", save("mini_" + label + ".json", result), flush=True)


if __name__ == "__main__":
    main()
