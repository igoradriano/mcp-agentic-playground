from mcp.server.fastmcp import FastMCP
import os

# -----------------------------------------------------------------------------
# Inicialização do servidor MCP
# -----------------------------------------------------------------------------
# FastMCP é uma forma simplificada de criar um servidor MCP.
# Ele expõe automaticamente:
# - Tools  (ações executáveis)
# - Resources (dados consultáveis)
# - Prompts (templates reutilizáveis)
# "AssistenteFinanceiro" é o nome lógico do servidor, usado para identificação pelo cliente MCP.
mcp = FastMCP("AssistenteFinanceiro")


# -----------------------------------------------------------------------------
# TOOL: Função executável pelo LLM
# -----------------------------------------------------------------------------

@mcp.tool()
def adiciona(a: int, b: int) -> int:
    """ Ferramenta para soma de dois números inteiros """
    return a + b

# -----------------------------------------------------------------------------
# RESOURCE: Dado persistente ou consultável
# -----------------------------------------------------------------------------

# Conceito:Resources representam dados "de leitura. Podem ser arquivos, bancos, APIs ou memória. 
# São acessados via URI (neste caso: memory://despesas_mensais)

@mcp.resource("memory://despesas_mensais")
def despesas_mensais() -> str:
    """ Lisa de despesas mensais registradas """
    try:
        SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))  # Diretório onde este arquivo Python está localizado
        FILE_PATH = os.path.join(SCRIPT_DIR, "contas_a_pagar.txt") # Caminho absoluto do arquivo de despesas
        with open(FILE_PATH, "r", encoding="utf-8") as f: # Leitura do conteúdo do arquivo
            return f.read()

    except FileNotFoundError:
        return "Nenhuma despesa registrada." # Caso o arquivo não exista, retorna uma resposta controlada

# -----------------------------------------------------------------------------
# PROMPT: Template reutilizável para o LLM
# -----------------------------------------------------------------------------

@mcp.prompt()
def formatar_dado_cadastral(cpf: str) -> str:
    """Prompt para formatar dados cadastrais"""
    return f"Formate o CPF informado no padrão xxx.xxx.xxx-xx: {cpf}"